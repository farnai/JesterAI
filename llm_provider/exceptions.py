"""Standardized exception hierarchy for JESTER LLM Providers."""

class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""
    def __init__(self, message: str, provider: str = "unknown", original_error: Exception | None = None):
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error


class LLMConnectionError(LLMProviderError):
    """Raised when JESTER cannot establish a connection to the LLM backend or daemon."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when API credentials (e.g. GEMINI_API_KEY) are invalid or missing."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when the LLM provider rate limits requests or runs out of quota."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when the LLM provider fails to return within the timeout threshold."""
    pass


class LLMResponseMalformedError(LLMProviderError):
    """Raised when the LLM provider returns an unparseable or corrupted payload."""
    pass
