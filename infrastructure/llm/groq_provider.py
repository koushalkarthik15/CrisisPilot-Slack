import logging
from typing import Optional
from groq import AsyncGroq, APIError, APIConnectionError, RateLimitError, AuthenticationError
from core.config import get_settings
from core.llm.base import BaseLLMProvider
from core.llm.models import LLMRequest, LLMResponse, UsageMetrics
from core.llm.exceptions import (
    LLMProviderError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMRateLimitError
)
from core.llm.guardrails import UsageGuardrail

logger = logging.getLogger("crisispilot.llm.groq")

class GroqProvider(BaseLLMProvider):
    """
    Production integration with the official Groq SDK.
    Enforces central guardrails and normalizes errors.
    """
    def __init__(self, guardrail: Optional[UsageGuardrail] = None):
        self.settings = get_settings()
        self.client: Optional[AsyncGroq] = None
        self.guardrail = guardrail or UsageGuardrail()
        self.model = self.settings.GROQ_MODEL

    async def initialize(self) -> None:
        logger.info("Initializing Groq Provider...")
        if not self.settings.GROQ_API_KEY:
            raise LLMAuthenticationError("GROQ_API_KEY is not configured.")
        
        # We explicitly inject the API key and enforce a default timeout (e.g., 30s)
        self.client = AsyncGroq(
            api_key=self.settings.GROQ_API_KEY,
            timeout=30.0,
            max_retries=2
        )
        logger.info(f"Groq Provider initialized with model: {self.model}")

    async def shutdown(self) -> None:
        logger.info("Shutting down Groq Provider...")
        if self.client:
            await self.client.close()
            self.client = None

    def _normalize_exception(self, e: Exception) -> Exception:
        """Translates Groq-specific exceptions into standard CrisisPilot LLM exceptions."""
        if isinstance(e, AuthenticationError):
            return LLMAuthenticationError(str(e))
        elif isinstance(e, RateLimitError):
            return LLMRateLimitError(str(e))
        elif isinstance(e, APIConnectionError):
            return LLMTimeoutError(f"Connection to Groq failed: {e}")
        elif isinstance(e, APIError):
            return LLMProviderError(f"Groq API Error: {e}")
        return LLMProviderError(f"Unexpected Groq error: {e}")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.client:
            raise LLMProviderError("Provider is not initialized.")
            
        logger.debug("Running guardrail checks...")
        # 1. Enforce Guardrails Before Execution
        await self.guardrail.check_before_execution()

        try:
            # 2. Build Request
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            
            messages.append({"role": "user", "content": request.prompt})

            # 3. Execute Request
            logger.info(f"Executing Groq chat completion request to model: {self.model}")
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
            if request.response_format:
                kwargs["response_format"] = request.response_format

            response = await self.client.chat.completions.create(**kwargs)

            # 4. Normalize Response
            content = response.choices[0].message.content or ""
            usage = response.usage
            
            metrics = UsageMetrics(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0
            )

            logger.info(f"[GroqProvider] Completed inference | total_tokens: {metrics.total_tokens}")

            # 5. Record Usage Guardrail Metrics After Execution
            await self.guardrail.record_after_execution(metrics)

            return LLMResponse(
                content=content,
                usage=metrics,
                metadata={"provider": "groq", "model": self.model}
            )

        except Exception as e:
            # On failure, release concurrency lock
            await self.guardrail.release_concurrency()
            logger.error(f"Groq Provider failed: {e}", exc_info=True)
            raise self._normalize_exception(e)
