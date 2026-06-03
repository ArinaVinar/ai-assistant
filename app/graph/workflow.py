from langgraph.graph import StateGraph, END

from app.config import settings
from app.graph.state import AgentState
from app.graph.nodes import (
    normalize_query_node,
    route_intent_node,
    neo4j_search_node,
    postgres_search_node,
    out_of_domain_node,
    context_merge_node,
    context_check_node,
    answer_generation_node,
    answer_verification_node,
    retry_prepare_node,
    final_response_node,
)


def choose_search_branch(state: AgentState) -> str:
    intent = state.get("intent", "geo_knowledge")

    if intent == "navigation":
        return "neo4j_search"

    if intent == "geo_knowledge":
        return "postgres_search"

    if intent == "mixed":
        return "neo4j_search"

    return "out_of_domain"


def after_neo4j_branch(state: AgentState) -> str:
    intent = state.get("intent", "unknown")

    if intent == "mixed":
        return "postgres_search"

    return "context_merge"


def after_context_check(state: AgentState) -> str:
    need_retry = state.get("need_retry", False)
    retry_count = state.get("retry_count", 0)

    if need_retry and retry_count < settings.max_retries:
        return "retry_prepare"

    return "answer_generation"


def after_verification(state: AgentState) -> str:
    need_retry = state.get("need_retry", False)
    retry_count = state.get("retry_count", 0)

    if need_retry and retry_count < settings.max_retries:
        return "retry_prepare"

    return "final_response"


def build_workflow():
    graph = StateGraph(AgentState)

    graph.add_node("normalize_query", normalize_query_node)
    graph.add_node("route_intent", route_intent_node)

    graph.add_node("neo4j_search", neo4j_search_node)
    graph.add_node("postgres_search", postgres_search_node)
    graph.add_node("out_of_domain", out_of_domain_node)

    graph.add_node("context_merge", context_merge_node)
    graph.add_node("context_check", context_check_node)

    graph.add_node("answer_generation", answer_generation_node)
    graph.add_node("answer_verification", answer_verification_node)

    graph.add_node("retry_prepare", retry_prepare_node)
    graph.add_node("final_response", final_response_node)

    graph.set_entry_point("normalize_query")

    graph.add_edge("normalize_query", "route_intent")

    graph.add_conditional_edges(
        "route_intent",
        choose_search_branch,
        {
            "neo4j_search": "neo4j_search",
            "postgres_search": "postgres_search",
            "out_of_domain": "out_of_domain",
        },
    )

    graph.add_conditional_edges(
        "neo4j_search",
        after_neo4j_branch,
        {
            "postgres_search": "postgres_search",
            "context_merge": "context_merge",
        },
    )

    graph.add_edge("postgres_search", "context_merge")
    graph.add_edge("out_of_domain", "final_response")

    graph.add_edge("context_merge", "context_check")

    graph.add_conditional_edges(
        "context_check",
        after_context_check,
        {
            "retry_prepare": "retry_prepare",
            "answer_generation": "answer_generation",
        },
    )

    graph.add_edge("retry_prepare", "route_intent")

    graph.add_edge("answer_generation", "answer_verification")

    graph.add_conditional_edges(
        "answer_verification",
        after_verification,
        {
            "retry_prepare": "retry_prepare",
            "final_response": "final_response",
        },
    )

    graph.add_edge("final_response", END)

    return graph.compile()


navigator_workflow = build_workflow()