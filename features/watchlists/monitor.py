import asyncio
import logging
from typing import Optional

from core.config import get_settings
from core.services import registry
from features.incident_management.repository import IncidentRepository
from features.incident_management.service import IncidentService
from features.recommendations.intelligence import IncidentIntelligenceService
from features.recommendations.repository import RecommendationRepository
from features.recommendations.router import RecommendationRouter
from features.recommendations.service import RecommendationService
from features.watchlists.repository import (
    WatchlistArticleRepository,
    WatchlistRepository,
)
from features.watchlists.service import WatchlistMonitoringService
from infrastructure.database import AsyncSessionLocal

logger = logging.getLogger("crisispilot.watchlists.monitor")

class NewsMonitorCoordinator:
    """
    Lightweight background scheduler for automated news polling.
    Delegates all business logic to the WatchlistMonitoringService.
    """
    def __init__(self):
        self.settings = get_settings()
        self.interval = self.settings.NEWS_POLLING_INTERVAL_SECONDS
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self):
        """Starts the background monitoring loop."""
        if self._task is not None:
            logger.warning("NewsMonitorCoordinator is already running.")
            return

        self._stop_event.clear()
        logger.info(f"Starting NewsMonitorCoordinator (interval: {self.interval}s)")
        self._task = asyncio.create_task(self._monitoring_loop())

    async def stop(self):
        """Stops the background monitoring loop."""
        if self._task is None:
            return

        logger.info("Stopping NewsMonitorCoordinator...")
        self._stop_event.set()

        try:
            await asyncio.wait_for(self._task, timeout=5.0)
        except asyncio.TimeoutError:
            self._task.cancel()
        except asyncio.CancelledError:
            pass

        self._task = None
        logger.info("NewsMonitorCoordinator stopped.")

    async def _monitoring_loop(self):
        while not self._stop_event.is_set():
            try:
                # Instantiate per-cycle session and services to ensure fresh DB state
                async with AsyncSessionLocal() as session:
                    intelligence_svc = registry.get(IncidentIntelligenceService)
                    router = registry.get(RecommendationRouter)

                    monitoring_service = WatchlistMonitoringService(
                        watchlist_repo=WatchlistRepository(),
                        article_repo=WatchlistArticleRepository(),
                        incident_service=IncidentService(IncidentRepository()),
                        recommendation_service=RecommendationService(
                            repository=RecommendationRepository(),
                            intelligence_service=intelligence_svc,
                            router=router
                        )
                    )
                    await monitoring_service.run_monitoring_cycle(session)
            except Exception as e:
                logger.error(f"Unexpected error in NewsMonitorCoordinator loop: {e}", exc_info=True)

            # Wait for the next interval or until stopped
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                # Timeout means stop event was not set, so we loop again
                pass
