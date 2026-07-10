import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from features.missions.domain import ExecutionStrategy, MissionStatus
from features.mission_execution.engine import MissionExecutionEngine
from features.mission_execution.strategies import StrategyRegistry

logger = logging.getLogger("crisispilot.mission_execution.scheduler")

class MissionScheduler:
    """Discovers and dispatches eligible missions for execution."""
    
    def __init__(self, engine: MissionExecutionEngine, strategy_registry: StrategyRegistry):
        self.engine = engine
        self.strategy_registry = strategy_registry

    async def run_tick(self, db: AsyncSession, state_manager: Any):
        """Scheduler loop tick. Discovers and dispatches scheduled missions."""
        logger.info("Scheduler tick started.")
        
        # Discover eligible SCHEDULED missions
        try:
            eligible_missions = await state_manager.mission_service.repository.list_eligible_for_execution(
                db, 
                strategy=ExecutionStrategy.SCHEDULED.value, 
                statuses=[MissionStatus.SCHEDULED]
            )
        except Exception as e:
            logger.error(f"Scheduler failed to query eligible missions: {e}")
            return
            
        logger.info(f"Discovered {len(eligible_missions)} eligible missions for execution.")
        
        for mission in eligible_missions:
            logger.info(f"Dispatching scheduled mission {mission.id}")
            try:
                handler = self.strategy_registry.get_handler(mission.strategy)
                await handler.execute(db, state_manager, self.engine, mission)
            except Exception as e:
                logger.error(f"Failed to execute mission {mission.id} during scheduler tick: {e}")

    async def dispatch_manual(self, db: AsyncSession, state_manager: Any, mission_id: str):
        """Entrypoint for manual execution dispatching."""
        mission = await state_manager.mission_service.get_mission(db, mission_id)
        
        handler = self.strategy_registry.get_handler(ExecutionStrategy.MANUAL)
        logger.info(f"Dispatching manual mission {mission.id}")
        return await handler.execute(db, state_manager, self.engine, mission)
