class LLMProviderError(Exception):
    """Base exception for all LLM Provider errors."""
    pass

class LLMGuardrailError(LLMProviderError):
    """Raised when an LLM request exceeds configured safety limits (tokens, rate, etc.)."""
    pass

class LLMTimeoutError(LLMProviderError):
    """Raised when the LLM provider fails to respond in time."""
    pass

class LLMAuthenticationError(LLMProviderError):
    """Raised when the LLM provider rejects the API key or authentication."""
    pass

class LLMRateLimitError(LLMProviderError):
    """Raised when the external LLM provider throttles the request (HTTP 429)."""
    pass
