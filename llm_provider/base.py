from abc import ABC, abstractmethod
from typing import Any, Dict, List


class LLMProvider(ABC):
    """Abstract interface for LLM backends (Ollama, llama.cpp, vLLM, OpenAI-compatible, etc.)."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] | None = None,
    ) -> str:
        """Sends a conversation history to the LLM and returns the assistant's response text."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Checks connectivity and returns status of the local LLM runtime."""
        pass
