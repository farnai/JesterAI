from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The message from the user/lord.")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Unique conversation session identifier. Generated automatically if omitted.",
    )


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    model: str


class MessageItem(BaseModel):
    role: str
    content: str


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[MessageItem]


class HealthResponse(BaseModel):
    status: str
    model: str
    ollama: Dict[str, Any]


class PersonaResponse(BaseModel):
    system_prompt: str
    rules_summary: Dict[str, Any]
