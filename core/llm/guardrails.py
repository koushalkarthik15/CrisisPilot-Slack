import asyncio
import logging
import time
from datetime import datetime, timezone
from core.config import get_settings
from core.llm.exceptions import LLMGuardrailError
from core.llm.models import UsageMetrics
from core.metrics import MetricsProvider

logger = logging.getLogger("crisispilot.llm.guardrails")

class UsageGuardrail(MetricsProvider):
    """
    In-memory, thread-safe guardrail tracking.
    Enforces LLM provider usage constraints without coupling to SQLite (yet).
    """
    def __init__(self):
        self.settings = get_settings()
        self.lock = asyncio.Lock()
        
        # State tracking
        self.current_day = datetime.now(timezone.utc).date()
        self.requests_today = 0
        self.tokens_today = 0
        
        # Sliding window for requests per minute
        self.request_timestamps = []
        
        self.concurrent_requests = 0

    async def _reset_if_new_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self.current_day:
            self.current_day = today
            self.requests_today = 0
            self.tokens_today = 0

    async def _clean_sliding_window(self):
        now = time.time()
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]

    async def check_before_execution(self):
        """Validates limits before allowing the request to proceed to the provider."""
        if not self.settings.LLM_GUARDRAILS_ENABLED:
            return

        async with self.lock:
            await self._reset_if_new_day()
            await self._clean_sliding_window()

            if self.requests_today >= self.settings.LLM_MAX_REQUESTS_PER_DAY:
                logger.error("Guardrail violation: Max daily requests exceeded.")
                raise LLMGuardrailError(f"Daily request limit reached ({self.settings.LLM_MAX_REQUESTS_PER_DAY}).")

            if self.tokens_today >= self.settings.LLM_MAX_TOKENS_PER_DAY:
                logger.error("Guardrail violation: Max daily tokens exceeded.")
                raise LLMGuardrailError(f"Daily token limit reached ({self.settings.LLM_MAX_TOKENS_PER_DAY}).")

            if len(self.request_timestamps) >= self.settings.LLM_MAX_REQUESTS_PER_MINUTE:
                logger.error("Guardrail violation: Rate limit exceeded (requests per minute).")
                raise LLMGuardrailError(f"Rate limit reached ({self.settings.LLM_MAX_REQUESTS_PER_MINUTE} req/min).")

            if self.concurrent_requests >= self.settings.LLM_MAX_CONCURRENT_REQUESTS:
                logger.error("Guardrail violation: Max concurrent requests exceeded.")
                raise LLMGuardrailError(f"Concurrent request limit reached ({self.settings.LLM_MAX_CONCURRENT_REQUESTS}).")

            # Admit the request
            self.concurrent_requests += 1
            self.request_timestamps.append(time.time())
            self.requests_today += 1

    async def record_after_execution(self, metrics: UsageMetrics):
        """Records token consumption and releases concurrency locks after execution."""
        if not self.settings.LLM_GUARDRAILS_ENABLED:
            return

        async with self.lock:
            self.concurrent_requests = max(0, self.concurrent_requests - 1)
            self.tokens_today += metrics.total_tokens
            logger.debug(f"UsageGuardrail state | Today reqs: {self.requests_today} | Today tokens: {self.tokens_today} | Active: {self.concurrent_requests}")

    async def release_concurrency(self):
        """Releases the concurrency lock if an exception bypasses record_after_execution."""
        if not self.settings.LLM_GUARDRAILS_ENABLED:
            return

        async with self.lock:
            self.concurrent_requests = max(0, self.concurrent_requests - 1)

    async def get_metrics(self) -> dict:
        """Exposes runtime usage metrics for the Analytics layer."""
        async with self.lock:
            return {
                "requests_today": self.requests_today,
                "tokens_today": self.tokens_today,
                "concurrent_requests": self.concurrent_requests,
                "max_requests_per_day": self.settings.LLM_MAX_REQUESTS_PER_DAY,
                "max_tokens_per_day": self.settings.LLM_MAX_TOKENS_PER_DAY,
            }
