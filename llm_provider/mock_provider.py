from typing import List, Optional
from .base import LLMProvider, LLMRequest, LLMResponse, LLMTokenUsage, ProviderMetadata


class MockProvider(LLMProvider):
    """Deterministic Mock LLM Provider for unit testing and offline development."""

    def __init__(
        self,
        model: str = "mock-qwen3.6",
        default_response: str = "Mock jester speaks with courtly mockery.",
        latency_ms: float = 15.0,
    ):
        self.model = model
        self.default_response = default_response
        self.latency_ms = latency_ms
        self.calls: List[LLMRequest] = []
        self.simulated_error: Optional[Exception] = None

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self.model

    async def chat(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if self.simulated_error:
            raise self.simulated_error

        return LLMResponse(
            content=self.default_response,
            model=self.model,
            provider=self.provider_name,
            latency_ms=self.latency_ms,
            usage=LLMTokenUsage(prompt_tokens=20, completion_tokens=15, total_tokens=35),
            raw_response={"mock": True},
        )

    async def health_check(self) -> ProviderMetadata:
        return ProviderMetadata(
            name=self.provider_name,
            current_model=self.model,
            is_cloud=False,
            healthy=True,
            details={"status": "healthy", "mode": "mock"},
        )
