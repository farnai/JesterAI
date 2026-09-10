from typing import Any, Dict, List, Optional
from .persona_manager import PersonaManager
from llm_provider.base import LLMMessage


# Sensitive attribute keys that should not be injected into the LLM context
SENSITIVE_ATTRIBUTE_KEYWORDS = (
    "token", "secret", "password", "api_key", "apikey", "auth",
    "credential", "session_id", "cookie", "private", "access_key",
)


class ContextBuilder:
    """Builds the full LLM prompt context by combining persona, sovereign attributes (UserContext),
    few-shot examples, and conversation history.
    """

    def __init__(self, persona_manager: PersonaManager, max_history_messages: int = 20):
        self.persona_manager = persona_manager
        self.max_history_messages = max_history_messages

    def format_sovereign_context(self, user_context: Any | None) -> str:
        """Formats read-only user attributes from Main App into a courtly context block."""
        if not user_context:
            return ""

        # Handle both Pydantic UserContext and plain dicts
        name = getattr(user_context, "name", None) if not isinstance(user_context, dict) else user_context.get("name")
        zodiac = getattr(user_context, "zodiac", None) if not isinstance(user_context, dict) else user_context.get("zodiac")
        birth_date = getattr(user_context, "birth_date", None) if not isinstance(user_context, dict) else user_context.get("birth_date")
        daily_energy = getattr(user_context, "daily_energy", None) if not isinstance(user_context, dict) else user_context.get("daily_energy")
        custom_attrs = getattr(user_context, "custom_attributes", {}) if not isinstance(user_context, dict) else user_context.get("custom_attributes", {})

        lines = []
        if name:
            lines.append(f"- Name / Title: {name}")
        if zodiac:
            lines.append(f"- Zodiac Sign: {zodiac}")
        if birth_date:
            lines.append(f"- Birth Date: {birth_date}")
        if daily_energy is not None:
            lines.append(f"- Daily Energy Score: {daily_energy} / 100")
        if custom_attrs and isinstance(custom_attrs, dict):
            for k, v in custom_attrs.items():
                k_str = str(k).lower().strip()
                if any(kw in k_str for kw in SENSITIVE_ATTRIBUTE_KEYWORDS):
                    continue
                v_str = str(v).strip()
                if len(v_str) > 200:
                    v_str = v_str[:197] + "..."
                label = str(k).replace("_", " ").title()
                lines.append(f"- {label}: {v_str}")

        if not lines:
            return ""

        return (
            "\n\n### THE CURRENT SOVEREIGN (USER ATTRIBUTES)\n"
            + "\n".join(lines)
            + "\n*Court Instruction*: Use these personal attributes subtly to craft targeted witticisms, "
            "royal banter, and philosophical observations when relevant. Do not recite them mechanically "
            "like an automated database read."
        )

    def build_messages(
        self,
        current_message: str,
        history: List[Dict[str, str]] | None = None,
        include_examples: bool = True,
        user_context: Any | None = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        # 1. System Prompt + Sovereign User Context
        system_content = self.persona_manager.get_compiled_system_prompt()
        sovereign_block = self.format_sovereign_context(user_context)
        if sovereign_block:
            system_content += sovereign_block

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
                role = msg["role"] if isinstance(msg, dict) else getattr(msg, "role", "user")
                content = msg["content"] if isinstance(msg, dict) else getattr(msg, "content", "")
                messages.append({"role": role, "content": content})

        # 4. Current User Query
        messages.append({"role": "user", "content": current_message})

        return messages

    def build_llm_messages(
        self,
        current_message: str,
        history: List[Dict[str, str]] | None = None,
        include_examples: bool = True,
        user_context: Any | None = None,
    ) -> List[LLMMessage]:
        """Convenience method returning typed LLMMessage objects for LLMRequest."""
        raw_msgs = self.build_messages(
            current_message=current_message,
            history=history,
            include_examples=include_examples,
            user_context=user_context,
        )
        return [LLMMessage(role=m["role"], content=m["content"]) for m in raw_msgs]
