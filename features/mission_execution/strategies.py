import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from features.missions.models import Mission
from features.missions.domain import ExecutionStrategy
from features.mission_execution.engine import MissionExecutionEngine
from features.mission_execution.exceptions import UnsupportedExecutionStrategyError

logger = logging.getLogger("crisispilot.mission_execution.strategies")

class BaseStrategyHandler:
    """Base interface for all mission execution strategy handlers."""
    
    async def execute(self, db: AsyncSession, state_manager: Any, engine: MissionExecutionEngine, mission: Mission) -> Mission:
        raise NotImplementedError("Strategy handler must implement execute()")

class ManualExecutionHandler(BaseStrategyHandler):
    """Handles execution for MANUAL strategy missions."""
    
    async def execute(self, db: AsyncSession, state_manager: Any, engine: MissionExecutionEngine, mission: Mission) -> Mission:
        logger.info(f"Executing manual mission {mission.id}")
        return await engine.execute(db, state_manager, mission)

class ScheduledExecutionHandler(BaseStrategyHandler):
    """Handles execution for SCHEDULED strategy missions."""
    
    async def execute(self, db: AsyncSession, state_manager: Any, engine: MissionExecutionEngine, mission: Mission) -> Mission:
        logger.info(f"Executing scheduled mission {mission.id}")
        return await engine.execute(db, state_manager, mission)

class UnsupportedExecutionHandler(BaseStrategyHandler):
    """Placeholder handler that gracefully fails unsupported strategies."""
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        
    async def execute(self, db: AsyncSession, state_manager: Any, engine: MissionExecutionEngine, mission: Mission) -> Mission:
        logger.warning(f"Strategy {self.strategy_name} is registered but not implemented. Skipping mission {mission.id}.")
        # We don't fail the mission in DB, we just skip it to allow future framework support
        # Or we can raise the error if preferred, but user requested graceful handling with logging
        return mission


class StrategyRegistry:
    """Registry mapping ExecutionStrategy to StrategyHandlers."""
    
    def __init__(self):
        self._handlers = {
            ExecutionStrategy.MANUAL: ManualExecutionHandler(),
            ExecutionStrategy.SCHEDULED: ScheduledExecutionHandler(),
            ExecutionStrategy.EVENT_DRIVEN: UnsupportedExecutionHandler(ExecutionStrategy.EVENT_DRIVEN.value),
            ExecutionStrategy.THRESHOLD_DRIVEN: UnsupportedExecutionHandler(ExecutionStrategy.THRESHOLD_DRIVEN.value),
            ExecutionStrategy.STATE_DRIVEN: UnsupportedExecutionHandler(ExecutionStrategy.STATE_DRIVEN.value),
            ExecutionStrategy.CHAINED: UnsupportedExecutionHandler(ExecutionStrategy.CHAINED.value),
            ExecutionStrategy.CONTINUOUS: UnsupportedExecutionHandler(ExecutionStrategy.CONTINUOUS.value)
        }
        
    def get_handler(self, strategy: ExecutionStrategy) -> BaseStrategyHandler:
        handler = self._handlers.get(strategy)
        if not handler:
            # Fallback if somehow a strategy exists without registration
            logger.error(f"Unknown strategy {strategy}")
            raise UnsupportedExecutionStrategyError(strategy.value if hasattr(strategy, "value") else str(strategy))
        return handler
