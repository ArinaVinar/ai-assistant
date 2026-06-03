from typing import Optional, Literal
from pydantic import BaseModel, Field

#это для одного сообщения в чате
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

#это для схемы входящего запроса на endpoint
class OpenAIChatRequest(BaseModel):
    model: Optional[str] = None
    messages: list[ChatMessage]
    temperature: Optional[float] = 0.2
    stream: Optional[bool] = False

#это для описания источника информации
class SourceItem(BaseModel):
    source_type: Literal["neo4j", "postgres"]
    source_id: str | int | None = None
    title: str | None = None
    content: str | None = None
    score: float | None = None

#это для ответа по навигации
class NavigatorAnswer(BaseModel):
    answer: str
    route: list[str] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)
    confidence: float = 0.0
    intent: Literal["navigation", "geo_knowledge", "mixed", "out_of_domain", "unknown"] = "unknown"
    retry_count: int = 0

#это для сообщения которое возвращает ассистент в формате openai
class OpenAIChoiceMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str

#это для других ответов. в openai-api каждый вар ответа назыв choice
class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIChoiceMessage
    finish_reason: str = "stop"

#это для итогового ответа
class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChoice]