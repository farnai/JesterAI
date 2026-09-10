import time
from typing import Any, Dict, List, Optional
import httpx

from .base import LLMProvider, LLMRequest, LLMResponse, LLMTokenUsage, ProviderMetadata
from .exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseMalformedError,
    LLMTimeoutError,
)


class GeminiProvider(LLMProvider):
    """Production Cloud LLM Provider adapter for Google Gemini via async HTTP REST API.
    
    Zero heavy third-party SDK dependencies. Interacts directly with the
    Google Generative Language API endpoint using secure server-side credentials.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.75,
        top_p: float = 0.9,
        timeout_seconds: float = 60.0,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout_seconds
        self.base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self.model

    async def chat(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise LLMAuthenticationError(
                "GEMINI_API_KEY is not configured or is empty. "
                "Ensure GEMINI_API_KEY is set in environment variables or configuration.",
                provider=self.provider_name,
            )

        url = f"{self.base_url}/models/{self.model}:generateContent"

        # Separate system messages from conversational contents
        system_instruction_text = ""
        contents = []

        for m in request.messages:
            if m.role == "system":
                system_instruction_text += f"{m.content}\n"
            else:
                # Gemini maps assistant role to "model"
                gemini_role = "model" if m.role == "assistant" else "user"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": m.content}],
                })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature if request.temperature is not None else self.temperature,
                "topP": request.top_p if request.top_p is not None else self.top_p,
                "maxOutputTokens": request.max_tokens or 2048,
            },
        }

        if system_instruction_text.strip():
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction_text.strip()}]
            }

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                raise LLMConnectionError(
                    "Failed to connect to Google Gemini API",
                    provider=self.provider_name,
                    original_error=e,
                )
            except httpx.TimeoutException as e:
                raise LLMTimeoutError(
                    f"Gemini API request timed out after {self.timeout}s",
                    provider=self.provider_name,
                    original_error=e,
                )
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code in (401, 403):
                    raise LLMAuthenticationError(
                        f"Gemini authentication failed (HTTP {status_code})",
                        provider=self.provider_name,
                        original_error=e,
                    )
                elif status_code == 429:
                    raise LLMRateLimitError(
                        "Gemini rate limit / quota exceeded (HTTP 429)",
                        provider=self.provider_name,
                        original_error=e,
                    )
                raise LLMProviderError(
                    f"Gemini API returned HTTP {status_code}",
                    provider=self.provider_name,
                    original_error=e,
                )
            except Exception as e:
                if isinstance(e, LLMProviderError):
                    raise
                raise LLMResponseMalformedError(
                    f"Unexpected error calling Gemini API: {type(e).__name__}",
                    provider=self.provider_name,
                    original_error=e,
                )

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Extract generated content from Gemini response candidates
        candidates = data.get("candidates", [])
        if not candidates:
            raise LLMResponseMalformedError(
                "Gemini response did not contain candidates",
                provider=self.provider_name,
            )

        content_parts = candidates[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in content_parts)

        # Extract token usage from usageMetadata
        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount")
        completion_tokens = usage_meta.get("candidatesTokenCount")
        total_tokens = usage_meta.get("totalTokenCount")

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
        if not self.api_key:
            return ProviderMetadata(
                name=self.provider_name,
                current_model=self.model,
                is_cloud=True,
                healthy=False,
                details={"status": "missing_api_key", "error": "GEMINI_API_KEY is not set"},
            )

        url = f"{self.base_url}/models/{self.model}"
        headers = {"x-goog-api-key": self.api_key}
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return ProviderMetadata(
                        name=self.provider_name,
                        current_model=self.model,
                        is_cloud=True,
                        healthy=True,
                        details={
                            "status": "healthy",
                            "display_name": data.get("displayName", self.model),
                            "input_token_limit": data.get("inputTokenLimit"),
                            "output_token_limit": data.get("outputTokenLimit"),
                        },
                    )
                return ProviderMetadata(
                    name=self.provider_name,
                    current_model=self.model,
                    is_cloud=True,
                    healthy=False,
                    details={"status": "unhealthy", "error": f"HTTP {response.status_code}"},
                )
            except Exception as e:
                return ProviderMetadata(
                    name=self.provider_name,
                    current_model=self.model,
                    is_cloud=True,
                    healthy=False,
                    details={"status": "unreachable", "error": type(e).__name__},
                )
