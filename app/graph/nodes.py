from app.config import settings
from app.graph.state import AgentState
from app.services.neo4j_service import neo4j_service
from app.services.postgresql_service import postgres_service
from app.services.ollama_service import ollama_service


def add_trace(state: AgentState, node: str, data: dict) -> AgentState:
    trace = state.get("trace", [])
    trace.append(
        {
            "node": node,
            "data": data,
        }
    )
    state["trace"] = trace
    return state


def normalize_query_node(state: AgentState) -> AgentState:
    query = state["user_query"].strip()
    normalized_query = " ".join(query.split())

    state["normalized_query"] = normalized_query
    state["retry_count"] = state.get("retry_count", 0)
    state["need_retry"] = False

    return add_trace(
        state,
        "normalize_query",
        {
            "normalized_query": normalized_query,
        },
    )


def route_intent_node(state: AgentState) -> AgentState:
    query = state["normalized_query"]

    prompt = f"""
Ты классификатор запросов для AI-ассистента программного комплекса «Навигатор».

Типы запросов:
1. navigation — пользователь спрашивает, где находится вкладка, раздел, функция, как перейти в нужное место интерфейса.
2. geo_knowledge — пользователь спрашивает геологический термин, определение, процесс или справочную информацию по геологии.
3. mixed — пользователю одновременно нужен маршрут в «Навигаторе» и пояснение геологического термина.
4. out_of_domain — вопрос не относится к «Навигатору» и геологическим знаниям.

Верни только JSON:
{{
  "intent": "navigation | geo_knowledge | mixed | out_of_domain",
  "reason": "короткая причина"
}}

Запрос пользователя:
{query}
"""

    result = ollama_service.generate_json(prompt, temperature=0.0)

    intent = result.get("intent", "geo_knowledge")

    if intent not in {"navigation", "geo_knowledge", "mixed", "out_of_domain"}:
        intent = "geo_knowledge"

    state["intent"] = intent

    return add_trace(
        state,
        "route_intent",
        {
            "intent": intent,
            "llm_result": result,
        },
    )


def neo4j_search_node(state: AgentState) -> AgentState:
    query = state["normalized_query"]

    results = neo4j_service.search_elements_semantic(query)

    state["neo4j_results"] = results

    route = []
    if results:
        route = results[0].get("route", [])

    state["route"] = route

    return add_trace(
        state,
        "neo4j_search",
        {
            "count": len(results),
            "route": route,
            "top_titles": [item.get("title") for item in results[:3]],
        },
    )


def postgres_search_node(state: AgentState) -> AgentState:
    query = state["normalized_query"]

    results = postgres_service.search_geology_blocks(query)

    state["postgres_results"] = results

    return add_trace(
        state,
        "postgres_search",
        {
            "count": len(results),
            "top_titles": [item.get("title") for item in results[:3]],
        },
    )


def out_of_domain_node(state: AgentState) -> AgentState:
    state["answer"] = (
        "Я могу помогать с работой в программном комплексе «Навигатор» "
        "и отвечать на вопросы по геологическим знаниям из подключенной базы. "
        "Этот запрос не относится к доступной предметной области."
    )
    state["confidence"] = 1.0
    state["sources"] = []
    state["route"] = []
    state["need_retry"] = False

    return add_trace(
        state,
        "out_of_domain",
        {
            "answer": state["answer"],
        },
    )


def context_merge_node(state: AgentState) -> AgentState:
    neo4j_results = state.get("neo4j_results", [])
    postgres_results = state.get("postgres_results", [])

    context_parts = []
    sources = []

    if neo4j_results:
        context_parts.append("ДАННЫЕ ИЗ NEO4J ПО СТРУКТУРЕ ПК «НАВИГАТОР»:")
        for item in neo4j_results:
            route = " → ".join(item.get("route", []))
            context_parts.append(
                f"""
Источник: Neo4j
ID узла: {item.get("source_id")}
Название: {item.get("title")}
Описание: {item.get("content") or ""}
Маршрут: {route}
Score: {item.get("score")}
""".strip()
            )
            sources.append(item)

    if postgres_results:
        context_parts.append("ДАННЫЕ ИЗ POSTGRESQL ПО ГЕОЛОГИЧЕСКИМ ЗНАНИЯМ:")
        for item in postgres_results:
            context_parts.append(
                f"""
Источник: PostgreSQL
ID блока: {item.get("source_id")}
Название: {item.get("title")}
Описание: {item.get("content") or ""}
Score: {item.get("score")}
""".strip()
            )
            sources.append(item)

    state["context"] = "\n\n".join(context_parts).strip()
    state["sources"] = sources

    return add_trace(
        state,
        "context_merge",
        {
            "sources_count": len(sources),
            "context_length": len(state["context"]),
        },
    )


def context_check_node(state: AgentState) -> AgentState:
    context = state.get("context", "")
    sources = state.get("sources", [])

    if not context or not sources:
        state["need_retry"] = True
        state["verification_comment"] = "Контекст не найден."
    else:
        state["need_retry"] = False
        state["verification_comment"] = "Контекст найден."

    return add_trace(
        state,
        "context_check",
        {
            "need_retry": state["need_retry"],
            "comment": state["verification_comment"],
        },
    )


def answer_generation_node(state: AgentState) -> AgentState:
    query = state["normalized_query"]
    intent = state.get("intent", "unknown")
    context = state.get("context", "")
    route = state.get("route", [])

    prompt = f"""
Ты AI-ассистент программного комплекса «Навигатор».

Отвечай только на основе предоставленного контекста.

Правила:
1. Не выдумывай сведения, которых нет в контексте.
2. Если вопрос про навигацию, дай понятный маршрут по интерфейсу.
3. Если вопрос про геологию, объясни термин или процесс простым техническим языком.
4. Если вопрос смешанный, сначала дай маршрут, затем пояснение.
5. В конце укажи источник данных: Neo4j, PostgreSQL или оба источника.
6. Не возвращай JSON. Верни обычный текст ответа.

Тип запроса:
{intent}

Запрос пользователя:
{query}

Маршрут, если найден:
{" → ".join(route) if route else "маршрут не найден"}

Контекст:
{context}

Сформируй ответ пользователю.
"""

    answer = ollama_service.generate(prompt, temperature=0.2)

    state["answer"] = answer

    return add_trace(
        state,
        "answer_generation",
        {
            "answer_length": len(answer),
        },
    )


def answer_verification_node(state: AgentState) -> AgentState:
    query = state["normalized_query"]
    context = state.get("context", "")
    answer = state.get("answer", "")

    prompt = f"""
Ты проверяющий агент AI-ассистента.

Оцени качество ответа относительно вопроса пользователя и найденного контекста.

Критерии:
1. Ответ должен отвечать на вопрос пользователя.
2. Ответ должен опираться на найденный контекст.
3. В ответе не должно быть неподтвержденных фактов.
4. Если вопрос про навигацию, маршрут должен быть конкретным.
5. Если вопрос про геологию, пояснение должно быть связано с найденным блоком знаний.

Верни только JSON:
{{
  "confidence": число от 0 до 1,
  "need_retry": true или false,
  "comment": "короткое объяснение"
}}

Запрос пользователя:
{query}

Контекст:
{context}

Ответ:
{answer}
"""

    result = ollama_service.generate_json(prompt, temperature=0.0)

    confidence = result.get("confidence", 0.0)
    need_retry = result.get("need_retry", False)
    comment = result.get("comment", "")

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    if confidence < settings.min_confidence:
        need_retry = True

    state["confidence"] = confidence
    state["need_retry"] = bool(need_retry)
    state["verification_comment"] = comment

    return add_trace(
        state,
        "answer_verification",
        {
            "confidence": confidence,
            "need_retry": need_retry,
            "comment": comment,
            "raw": result,
        },
    )


def retry_prepare_node(state: AgentState) -> AgentState:
    retry_count = state.get("retry_count", 0) + 1
    state["retry_count"] = retry_count

    query = state["normalized_query"]

    prompt = f"""
Переформулируй пользовательский запрос для повторного поиска.
Нужно сохранить смысл, но добавить ключевые слова, которые помогут найти более релевантный контекст.

Верни только JSON:
{{
  "query": "новый поисковый запрос"
}}

Исходный запрос:
{query}

Комментарий проверки:
{state.get("verification_comment", "")}
"""

    result = ollama_service.generate_json(prompt, temperature=0.0)
    new_query = result.get("query", query)

    state["normalized_query"] = new_query

    return add_trace(
        state,
        "retry_prepare",
        {
            "retry_count": retry_count,
            "new_query": new_query,
        },
    )


def final_response_node(state: AgentState) -> AgentState:
    if not state.get("answer"):
        state["answer"] = (
            "Не удалось сформировать ответ по доступным данным. "
            "Попробуйте уточнить название вкладки, функции или геологического термина."
        )

    return add_trace(
        state,
        "final_response",
        {
            "confidence": state.get("confidence", 0.0),
            "retry_count": state.get("retry_count", 0),
        },
    )