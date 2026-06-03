from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str

    user_query: str
    normalized_query: str

    intent: str

    neo4j_results: list[dict]
    postgres_results: list[dict]

    route: list[str]
    context: str
    sources: list[dict]

    answer: str
    confidence: float
    verification_comment: str

    retry_count: int
    need_retry: bool

    error: str | None
    trace: list[dict[str, Any]]