import time
from typing import Any, Dict, List, Optional
import httpx

from .base import LLMProvider, LLMRequest, LLMResponse, LLMTokenUsage, ProviderMetadata
from .exceptions import (
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseMalformedError,
    LLMTimeoutError,
)


class OllamaProvider(LLMProvider):
    """Ollama API provider implementation using asynchronous HTTP requests."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3.6:latest",
        temperature: float = 0.85,
        top_p: float = 0.9,
        frequency_penalty: Optional[float] = 0.35,
        num_ctx: int = 8192,
        timeout_seconds: float = 240.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.num_ctx = num_ctx
        self.timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self.model

    async def chat(self, request: LLMRequest) -> LLMResponse:
        url = f"{self.base_url}/api/chat"

        opts: Dict[str, Any] = {
            "temperature": request.temperature if request.temperature is not None else self.temperature,
            "top_p": request.top_p if request.top_p is not None else self.top_p,
            "num_ctx": self.num_ctx,
        }
        if self.frequency_penalty is not None:
            opts["frequency_penalty"] = self.frequency_penalty
        if request.extra_options:
            opts.update(request.extra_options)

        # Convert LLMMessage models to dictionaries for Ollama API
        messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]

        payload = {
            "model": self.model,
            "messages": messages_payload,
            "stream": False,
            "options": opts,
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                raise LLMConnectionError(
                    f"Unable to connect to Ollama at {self.base_url}. "
                    f"Ensure 'ollama serve' is running. Error: {e}",
                    provider=self.provider_name,
                    original_error=e,
                )
            except httpx.TimeoutException as e:
                raise LLMTimeoutError(
                    f"Ollama request timed out after {self.timeout}s: {e}",
                    provider=self.provider_name,
                    original_error=e,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise LLMRateLimitError(
                        f"Ollama rate limit / resource exhaustion: {e.response.text}",
                        provider=self.provider_name,
                        original_error=e,
                    )
                raise LLMProviderError(
                    f"Ollama returned HTTP {e.response.status_code}: {e.response.text}",
                    provider=self.provider_name,
                    original_error=e,
                )
            except Exception as e:
                if isinstance(e, (LLMProviderError,)):
                    raise
                raise LLMResponseMalformedError(
                    f"Failed to process Ollama response: {e}",
                    provider=self.provider_name,
                    original_error=e,
                )

        latency_ms = (time.perf_counter() - start_time) * 1000
        message_data = data.get("message", {})
        content = message_data.get("content", "")

        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        total_tokens = None
        if prompt_tokens is not None or completion_tokens is not None:
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

        usage = LLMTokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider_name,
            latency_ms=round(latency_ms, 2),
            usage=usage,
            raw_response=data,
        )

    async def health_check(self) -> ProviderMetadata:
        url = f"{self.base_url}/api/tags"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    model_found = any(self.model in m for m in models)
                    return ProviderMetadata(
                        name=self.provider_name,
                        current_model=self.model,
                        is_cloud=False,
                        healthy=model_found,
                        details={
                            "status": "healthy" if model_found else "model_not_found",
                            "model_ready": model_found,
                            "available_models": models,
                            "base_url": self.base_url,
                        },
                    )
                return ProviderMetadata(
                    name=self.provider_name,
                    current_model=self.model,
                    is_cloud=False,
                    healthy=False,
                    details={"error": f"HTTP {response.status_code}", "base_url": self.base_url},
                )
            except Exception as e:
                return ProviderMetadata(
                    name=self.provider_name,
                    current_model=self.model,
                    is_cloud=False,
                    healthy=False,
                    details={"error": str(e), "base_url": self.base_url},
                )
