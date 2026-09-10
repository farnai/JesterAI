import threading
from typing import Dict, List, Optional
from .memory import ConversationMemory


class InMemoryStore(ConversationMemory):
    """Thread-safe in-memory store for multi-session conversation history."""

    def __init__(self, max_messages_per_conversation: int = 100):
        self._store: Dict[str, List[Dict[str, str]]] = {}
        self._lock = threading.Lock()
        self.max_messages = max_messages_per_conversation

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        with self._lock:
            if conversation_id not in self._store:
                self._store[conversation_id] = []
            self._store[conversation_id].append({"role": role, "content": content})
            # Trim store to prevent unbounded memory growth
            if len(self._store[conversation_id]) > self.max_messages:
                self._store[conversation_id] = self._store[conversation_id][-self.max_messages :]

    def get_history(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        with self._lock:
            history = list(self._store.get(conversation_id, []))
            if limit is not None and limit > 0:
                return history[-limit:]
            return history

    def clear(self, conversation_id: str) -> None:
        with self._lock:
            if conversation_id in self._store:
                del self._store[conversation_id]

    def list_conversations(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
