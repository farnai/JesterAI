from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field


class QuotaDecision(BaseModel):
    """Decision returned by the EntitlementService before LLM inference."""
    allowed: bool = Field(..., description="Whether the user is permitted to invoke the LLM")
    remaining_free_questions: int = Field(..., description="Number of remaining free questions")
    is_subscribed: bool = Field(default=False, description="Whether the user has an active paid subscription")
    rejection_code: Optional[str] = Field(default=None, description="Code if rejected (e.g. 'QUOTA_EXCEEDED')")
    rejection_message: Optional[str] = Field(default=None, description="Human-readable rejection explanation in Georgian")


class EntitlementService(ABC):
    """Abstract gatekeeper protecting LLM inference resources.
    
    The Main App is the canonical authority for billing and subscription logic.
    JESTER checks access BEFORE any LLM call to guarantee ZERO unfunded inferences.
    """

    @abstractmethod
    async def check_access(self, user_id: str, entitlement_token: Optional[str] = None) -> QuotaDecision:
        """Evaluates whether the user is permitted to proceed with LLM generation (read-only)."""
        pass

    @abstractmethod
    async def reserve_quota(self, user_id: str, entitlement_token: Optional[str] = None) -> QuotaDecision:
        """Atomically reserves one turn before LLM inference if quota is available."""
        pass

    @abstractmethod
    async def commit_quota(self, user_id: str) -> None:
        """Finalizes the quota consumption after successful LLM inference."""
        pass

    @abstractmethod
    async def release_quota(self, user_id: str) -> None:
        """Releases a previously held reservation if LLM inference failed."""
        pass

    @abstractmethod
    async def consume_quota(self, user_id: str) -> None:
        """Records one consumed question turn (direct/legacy consumption)."""
        pass
