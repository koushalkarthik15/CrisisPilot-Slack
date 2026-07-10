from abc import ABC, abstractmethod
from core.llm.models import LLMRequest, LLMResponse

class BaseLLMProvider(ABC):
    """
    Provider-agnostic abstraction for Large Language Models.
    Future providers (Groq, OpenAI, Gemini) must implement this interface
    so that business logic and Mini-Agents remain vendor-agnostic.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Bootstraps the provider, validates credentials and config."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully tears down provider resources and active connections."""
        pass

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Executes a normalized request against the underlying provider SDK
        and returns a normalized response.
        """
        pass
