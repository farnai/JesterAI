from typing import Any, Dict, List
import httpx
from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama API provider implementation using asynchronous HTTP requests."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        temperature: float = 0.75,
        top_p: float = 0.9,
        num_ctx: int = 8192,
        timeout_seconds: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.num_ctx = num_ctx
        self.timeout = timeout_seconds

    async def chat(
        self,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] | None = None,
    ) -> str:
        url = f"{self.base_url}/api/chat"

        opts = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_ctx": self.num_ctx,
        }
        if options:
            opts.update(options)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": opts,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                message = data.get("message", {})
                return message.get("content", "")
            except httpx.ConnectError as e:
                raise ConnectionError(
                    f"Unable to connect to Ollama at {self.base_url}. "
                    f"Ensure 'ollama serve' is running. Error: {e}"
                )
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"Ollama returned HTTP error {e.response.status_code}: {e.response.text}"
                )
            except Exception as e:
                raise RuntimeError(f"Unexpected error calling Ollama: {e}")

    async def health_check(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/tags"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    model_found = any(self.model in m for m in models)
                    return {
                        "status": "healthy" if model_found else "model_not_found",
                        "provider": "ollama",
                        "configured_model": self.model,
                        "model_ready": model_found,
                        "available_models": models,
                    }
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                }
            except Exception as e:
                return {
                    "status": "unreachable",
                    "error": str(e),
                    "base_url": self.base_url,
                }
