from typing import Any, Dict, List
from .persona_manager import PersonaManager


class ContextBuilder:
    """Builds the full LLM prompt context by combining persona, few-shot examples,

    and conversation history.
    """

    def __init__(self, persona_manager: PersonaManager, max_history_messages: int = 20):
        self.persona_manager = persona_manager
        self.max_history_messages = max_history_messages

    def build_messages(
        self,
        current_message: str,
        history: List[Dict[str, str]] | None = None,
        include_examples: bool = True,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        # 1. System Prompt
        system_content = self.persona_manager.get_compiled_system_prompt()
        messages.append({"role": "system", "content": system_content})

        # 2. Few-shot Examples (as conversational context)
        if include_examples:
            examples = self.persona_manager.get_examples()
            for ex in examples:
                user_text = ex.get("user")
                asst_text = ex.get("assistant")
                if user_text and asst_text:
                    messages.append({"role": "user", "content": user_text})
                    messages.append({"role": "assistant", "content": asst_text})

        # 3. Conversation History (sliding window)
        if history:
            trimmed_history = history[-self.max_history_messages :]
            for msg in trimmed_history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        # 4. Current User Query
        messages.append({"role": "user", "content": current_message})

        return messages
