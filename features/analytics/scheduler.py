import asyncio
import logging
from typing import Optional

from core.config import get_settings
from infrastructure.database import AsyncSessionLocal
from core.services import registry
from core.notifications import NotificationEngine
from core.llm.guardrails import UsageGuardrail
from features.analytics.service import AnalyticsService
from features.analytics.formatter import format_operational_summary_blocks

logger = logging.getLogger("crisispilot.analytics.scheduler")

class SummaryDigestScheduler:
    """
    Lightweight background scheduler for automated operational digests.
    """
    def __init__(self):
        self.settings = get_settings()
        self.enabled = self.settings.OPS_SUMMARY_ENABLED
        self.interval = self.settings.OPS_SUMMARY_INTERVAL_SECONDS
        self.channel_id = self.settings.OPS_SUMMARY_CHANNEL_ID
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self):
        """Starts the background summary loop."""
        if not self.enabled:
            logger.info("SummaryDigestScheduler is disabled via configuration.")
            return
            
        if self._task is not None:
            logger.warning("SummaryDigestScheduler is already running.")
            return

        self._stop_event.clear()
        logger.info(f"Starting SummaryDigestScheduler (interval: {self.interval}s)")
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stops the background summary loop."""
        if self._task is None:
            return

        logger.info("Stopping SummaryDigestScheduler...")
        self._stop_event.set()
        
        try:
            await asyncio.wait_for(self._task, timeout=5.0)
        except asyncio.TimeoutError:
            self._task.cancel()
        except asyncio.CancelledError:
            pass
            
        self._task = None
        logger.info("SummaryDigestScheduler stopped.")

    async def _scheduler_loop(self):
        while not self._stop_event.is_set():
            try:
                # Wait for the interval first before sending the first digest
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                # Timeout means interval elapsed without being stopped
                try:
                    logger.info("Generating scheduled Operational Summary Digest...")
                    async with AsyncSessionLocal() as session:
                        metrics_provider = registry.get(UsageGuardrail)
                        svc = AnalyticsService(metrics_provider)
                        summary = await svc.get_operational_summary(session)
                        blocks = format_operational_summary_blocks(summary)
                        
                        notification_engine = registry.get(NotificationEngine)
                        await notification_engine.publish_operational_summary(blocks, self.channel_id)
                        logger.info("Scheduled Operational Summary Digest published.")
                except Exception as e:
                    logger.error(f"Unexpected error in SummaryDigestScheduler loop: {e}", exc_info=True)
            except asyncio.CancelledError:
                break
