import json
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.graph.workflow import navigator_workflow
from app.schemas_json import (
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIChoice,
    OpenAIChoiceMessage,
)
from app.services.embedding_service import embedding_service
from app.services.neo4j_service import neo4j_service
from app.services.postgresql_service import postgres_service


app = FastAPI(
    title="Navigator AI Assistant API",
    description="API-сервис AI-ассистента для ПК «Навигатор»",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_last_user_message(messages) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content

    raise HTTPException(
        status_code=400,
        detail="В запросе нет сообщения пользователя"
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "navigator-ai-api",
        "ollama_model": settings.ollama_model,
        "embedding_model": settings.embedding_model,
    }


@app.post("/api/embedding")
def create_embedding(payload: dict):
    text = payload.get("text")

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Поле 'text' обязательно"
        )

    vector = embedding_service.embed_query(text)

    return {
        "model": settings.embedding_model,
        "dimension": len(vector),
        "embedding": vector,
    }


@app.post("/api/search/neo4j")
def search_neo4j(payload: dict):
    query = payload.get("query")

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Поле 'query' обязательно"
        )

    results = neo4j_service.search_elements_semantic(query)

    return {
        "query": query,
        "results": results,
    }


@app.post("/api/search/postgres")
def search_postgres(payload: dict):
    query = payload.get("query")

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Поле 'query' обязательно"
        )

    results = postgres_service.search_geology_blocks(query)

    return {
        "query": query,
        "results": results,
    }


@app.post("/api/chat")
def chat(payload: dict):
    query = payload.get("query")
    session_id = payload.get("session_id", str(uuid.uuid4()))

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Поле 'query' обязательно"
        )

    result = navigator_workflow.invoke(
        {
            "session_id": session_id,
            "user_query": query,
            "retry_count": 0,
            "trace": [],
        }
    )

    return {
        "session_id": session_id,
        "answer": result.get("answer"),
        "intent": result.get("intent"),
        "route": result.get("route", []),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0.0),
        "retry_count": result.get("retry_count", 0),
        "verification_comment": result.get("verification_comment", ""),
        "trace": result.get("trace", []),
    }


@app.post("/v1/chat/completions", response_model=OpenAIChatResponse)
def openai_compatible_chat(request: OpenAIChatRequest):
    user_query = get_last_user_message(request.messages)
    session_id = str(uuid.uuid4())

    result = navigator_workflow.invoke(
        {
            "session_id": session_id,
            "user_query": user_query,
            "retry_count": 0,
            "trace": [],
        }
    )

    answer_text = result.get("answer", "")

    service_payload = {
        "intent": result.get("intent"),
        "route": result.get("route", []),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0.0),
        "retry_count": result.get("retry_count", 0),
    }

    content = (
        f"{answer_text}\n\n"
        f"---\n"
        f"Служебная информация:\n"
        f"```json\n"
        f"{json.dumps(service_payload, ensure_ascii=False, indent=2)}\n"
        f"```"
    )

    return OpenAIChatResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=request.model or settings.ollama_model,
        choices=[
            OpenAIChoice(
                message=OpenAIChoiceMessage(
                    role="assistant",
                    content=content,
                )
            )
        ],
    )

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "navigator-assistant",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "navigator-ai-api"
            }
        ]
    }


@app.on_event("shutdown")
def shutdown_event():
    neo4j_service.close()