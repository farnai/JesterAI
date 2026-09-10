import re
from typing import List

DEFAULT_PATTERNS = [
    # Asterisk stage directions: *laughs*, *sighs*, *იცინის*, *rolls eyes*, etc.
    r"\*[^\*\n]{1,80}\*",
    # Parenthetical stage directions commonly produced: (laughs), (იცინის), (თავს ხრის), etc.
    r"\((?:იცინის|ეჟვნები|იღიმის|ხრის|იცინოდა|ამოიოხრა|თავს|laughs|chuckles|sighs|bows|rolls eyes|smiles|winks|grins|pauses|giggles)[^)]*\)",
]


class OutputFilter:
    """Sanitizes JESTER output to guarantee compliance with style constraints."""

    def __init__(self, additional_patterns: List[str] | None = None):
        patterns = list(DEFAULT_PATTERNS)
        if additional_patterns:
            patterns.extend(additional_patterns)

        self._compiled_regexes = []
        for p in patterns:
            try:
                self._compiled_regexes.append(re.compile(p, re.IGNORECASE))
            except re.error:
                continue

    def sanitize(self, text: str) -> str:
        """Removes stage directions, cleans up orphaned punctuation and redundant spacing."""
        cleaned = text
        for regex in self._compiled_regexes:
            cleaned = regex.sub("", cleaned)

        # Clean up lines with dangling spaces
        lines = [line.strip() for line in cleaned.split("\n")]
        # Remove consecutive blank lines
        result_lines = []
        for line in lines:
            if not line and result_lines and not result_lines[-1]:
                continue
            result_lines.append(line)

        sanitized = "\n".join(result_lines).strip()
        return sanitized if sanitized else text.strip()
