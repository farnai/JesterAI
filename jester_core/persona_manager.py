from pathlib import Path
from typing import Any, Dict, List
import yaml


class PersonaManager:
    """Loads, compiles, and manages JESTER persona documents and configurations."""

    def __init__(self, persona_dir: Path):
        self.persona_dir = persona_dir
        self.system_prompt_path = self.persona_dir / "system_prompt.md"
        self.rules_path = self.persona_dir / "rules.yaml"
        self.forbidden_path = self.persona_dir / "forbidden.yaml"
        self.examples_path = self.persona_dir / "examples.yaml"

        self._cached_prompt: str | None = None
        self._cached_rules: Dict[str, Any] = {}
        self._cached_forbidden: Dict[str, Any] = {}
        self._cached_examples: List[Dict[str, str]] = []
        self.load()

    def load(self) -> None:
        """Reads all persona definition files from disk."""
        # 1. Base Markdown System Prompt
        if self.system_prompt_path.exists():
            with open(self.system_prompt_path, "r", encoding="utf-8") as f:
                base_prompt = f.read().strip()
        else:
            base_prompt = "You are JESTER, a witty medieval court jester."

        # 2. Rules YAML
        if self.rules_path.exists():
            with open(self.rules_path, "r", encoding="utf-8") as f:
                self._cached_rules = yaml.safe_load(f) or {}
        else:
            self._cached_rules = {}

        # 3. Forbidden YAML
        if self.forbidden_path.exists():
            with open(self.forbidden_path, "r", encoding="utf-8") as f:
                self._cached_forbidden = yaml.safe_load(f) or {}
        else:
            self._cached_forbidden = {}

        # 4. Examples YAML
        if self.examples_path.exists():
            with open(self.examples_path, "r", encoding="utf-8") as f:
                raw_ex = yaml.safe_load(f) or {}
                self._cached_examples = raw_ex.get("examples", [])
        else:
            self._cached_examples = []

        # Compile full system instructions
        lines = [base_prompt, "\n## OPERATIONAL RULES & BEHAVIORAL PROTOCOLS:"]

        personality = self._cached_rules.get("personality", {})
        if personality:
            lines.append("### Persona Attributes:")
            for k, v in personality.items():
                lines.append(f"- {k.replace('_', ' ').title()}: {v}")

        scenarios = self._cached_rules.get("scenarios", {})
        if scenarios:
            lines.append("\n### Situational Behavior Directives:")
            for sc_name, sc_data in scenarios.items():
                directive = sc_data.get("directive", "") if isinstance(sc_data, dict) else str(sc_data)
                lines.append(f"- When facing {sc_name.replace('_', ' ')}: {directive}")

        forbidden = self._cached_forbidden.get("forbidden_behaviors", [])
        if forbidden:
            lines.append("\n### STRICT PROHIBITIONS & STYLE VIOLATIONS (NEVER DO THESE):")
            for item in forbidden:
                lines.append(f"- {item}")

        self._cached_prompt = "\n".join(lines)

    def reload(self) -> None:
        """Forces reload of persona files from disk."""
        self.load()

    def get_compiled_system_prompt(self) -> str:
        if self._cached_prompt is None:
            self.load()
        return self._cached_prompt or ""

    def get_examples(self) -> List[Dict[str, str]]:
        return self._cached_examples

    def get_strip_patterns(self) -> List[str]:
        return self._cached_forbidden.get("regex_strip_patterns", [])

    def get_rules_summary(self) -> Dict[str, Any]:
        return {
            "rules": self._cached_rules,
            "forbidden": self._cached_forbidden,
            "example_count": len(self._cached_examples),
        }
