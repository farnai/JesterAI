from typing import Any
from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .gemini_provider import GeminiProvider
from .mock_provider import MockProvider


def get_llm_provider(settings: Any) -> LLMProvider:
    """Factory function instantiating the configured LLMProvider implementation.
    
    Decouples JESTER Core from vendor-specific provider selection.
    """
    provider_type = getattr(settings.llm, "provider", "ollama").lower()

    if provider_type == "ollama":
        return OllamaProvider(
            base_url=settings.llm.base_url,
            model=settings.llm.model,
            temperature=settings.llm.temperature,
            top_p=settings.llm.top_p,
            num_ctx=getattr(settings.llm, "num_ctx", 8192),
            timeout_seconds=getattr(settings.llm, "timeout_seconds", 120.0),
        )
    elif provider_type == "gemini":
        return GeminiProvider(
            api_key=getattr(settings.llm, "api_key", ""),
            model=settings.llm.model,
            temperature=settings.llm.temperature,
            top_p=settings.llm.top_p,
            timeout_seconds=getattr(settings.llm, "timeout_seconds", 60.0),
        )
    elif provider_type == "mock":
        return MockProvider(
            model=settings.llm.model,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: '{provider_type}'")
