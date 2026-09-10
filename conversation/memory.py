from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class ConversationMemory(ABC):
    """Abstract interface for storing and retrieving conversation history."""

    @abstractmethod
    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        """Appends a message to the conversation."""
        pass

    @abstractmethod
    def get_history(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Retrieves history for a conversation."""
        pass

    @abstractmethod
    def clear(self, conversation_id: str) -> None:
        """Deletes history for a conversation."""
        pass

    @abstractmethod
    def list_conversations(self) -> List[str]:
        """Lists active conversation IDs."""
        pass
