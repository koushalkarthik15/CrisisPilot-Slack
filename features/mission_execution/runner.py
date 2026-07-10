import asyncio
import logging
from typing import Optional

from infrastructure.database import AsyncSessionLocal
from core.services import registry

logger = logging.getLogger("crisispilot.mission_execution.runner")

class MissionSchedulerBackgroundRunner:
    """
    Lightweight background loop that continuously ticks the MissionScheduler.
    """
    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self):
        """Starts the background scheduling loop."""
        if self._task is not None:
            logger.warning("MissionSchedulerBackgroundRunner is already running.")
            return

        self._stop_event.clear()
        logger.info(f"Starting MissionSchedulerBackgroundRunner (interval: {self.interval}s)")
        self._task = asyncio.create_task(self._monitoring_loop())

    async def stop(self):
        """Stops the background scheduling loop."""
        if self._task is None:
            return

        logger.info("Stopping MissionSchedulerBackgroundRunner...")
        self._stop_event.set()
        
        try:
            await asyncio.wait_for(self._task, timeout=5.0)
        except asyncio.TimeoutError:
            self._task.cancel()
        except asyncio.CancelledError:
            pass
            
        self._task = None
        logger.info("MissionSchedulerBackgroundRunner stopped.")

    async def _monitoring_loop(self):
        from core.state import StateManager
        while not self._stop_event.is_set():
            try:
                state_manager = registry.get(StateManager)
                async with AsyncSessionLocal() as session:
                    await state_manager.run_mission_scheduler_tick(session)
            except Exception as e:
                logger.error(f"Unexpected error in MissionScheduler tick loop: {e}", exc_info=True)
            
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
