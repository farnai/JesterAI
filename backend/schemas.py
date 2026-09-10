from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """Ephemeral sovereign profile attributes supplied by the Main Application."""
    name: Optional[str] = Field(default=None, max_length=100, description="The user's display name or royal title")
    birth_date: Optional[str] = Field(default=None, description="ISO format date YYYY-MM-DD")
    zodiac: Optional[str] = Field(default=None, max_length=50, description="Astrological sign (e.g. ლომი, მშვილდოსანი)")
    daily_energy: Optional[int] = Field(default=None, ge=0, le=100, description="Daily vitality score 0-100")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Safe forward-compatible metadata")


class UsageInfo(BaseModel):
    """Usage and performance metrics returned with the chat response."""
    remaining_free_questions: int = Field(..., description="Questions remaining before paywall")
    is_paid_user: bool = Field(default=False, description="Whether user has an active subscription")
    prompt_tokens: Optional[int] = Field(default=None, description="Prompt tokens evaluated")
    completion_tokens: Optional[int] = Field(default=None, description="Tokens generated")
    latency_ms: Optional[float] = Field(default=None, description="Inference latency in milliseconds")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The message from the sovereign user.")
    user_id: str = Field(..., min_length=1, description="Unique user identifier from the Main App. Mandatory.")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Unique conversation session identifier. Generated automatically if omitted.",
    )
    user_context: Optional[UserContext] = Field(
        default=None,
        description="Optional sovereign context (name, zodiac, daily energy) supplied by Main App.",
    )


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    model: str
    provider: str = "ollama"
    usage: Optional[UsageInfo] = None


class QuotaExceededResponse(BaseModel):
    """Returned as HTTP 402 when user has exhausted free questions."""
    error: str = "QUOTA_EXCEEDED"
    message: str
    user_id: str
    remaining_free_questions: int = 0
    upgrade_url: str = "/billing/plans"


class QuotaStatusResponse(BaseModel):
    """Response model for quota status checks."""
    user_id: str
    remaining_free_questions: int
    is_paid_user: bool
    allowed: bool


class MessageItem(BaseModel):
    role: str
    content: str


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[MessageItem]


class HealthResponse(BaseModel):
    """Provider-agnostic health response."""
    status: str
    model: str
    provider: str
    provider_details: Dict[str, Any] = Field(default_factory=dict)


class PersonaResponse(BaseModel):
    system_prompt: str
    rules_summary: Dict[str, Any]
