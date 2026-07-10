import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from features.missions.repository import MissionRepository
from features.missions.schemas import MissionCreate, MissionUpdate, MissionAssignment
from features.missions.models import Mission
from features.missions.domain import MissionStatus
from features.missions.exceptions import MissionNotFoundError, InvalidMissionStateTransitionError, InvalidMissionOwnershipError, InvalidMissionAssignmentError

logger = logging.getLogger("crisispilot.missions.service")

def utc_now():
    return datetime.now(timezone.utc)

class MissionService:
    """Business logic and lifecycle management for Missions."""
    
    ALLOWED_TRANSITIONS = {
        MissionStatus.CREATED: [MissionStatus.SCHEDULED, MissionStatus.RUNNING, MissionStatus.CANCELLED],
        MissionStatus.SCHEDULED: [MissionStatus.RUNNING, MissionStatus.CANCELLED],
        MissionStatus.RUNNING: [MissionStatus.PAUSED, MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED],
        MissionStatus.PAUSED: [MissionStatus.RUNNING, MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED],
        MissionStatus.COMPLETED: [],
        MissionStatus.FAILED: [],
        MissionStatus.CANCELLED: []
    }

    def __init__(self, repository: MissionRepository):
        self.repository = repository

    def _validate_ownership(self, operation_id: Optional[str], incident_id: Optional[str]):
        if not operation_id and not incident_id:
            raise InvalidMissionOwnershipError()

    async def create_mission(self, db: AsyncSession, mission_in: MissionCreate, created_by: str) -> Mission:
        self._validate_ownership(mission_in.operation_id, mission_in.incident_id)
            
        mission = await self.repository.create(db, mission_in, created_by)
        logger.info(f"MissionService: Created mission {mission.id}")
        return mission

    async def get_mission(self, db: AsyncSession, mission_id: str) -> Mission:
        mission = await self.repository.get(db, mission_id)
        if not mission:
            raise MissionNotFoundError(mission_id)
        return mission

    async def update_mission(self, db: AsyncSession, mission_id: str, update_data: MissionUpdate) -> Mission:
        mission = await self.repository.update(db, mission_id, update_data)
        if not mission:
            raise MissionNotFoundError(mission_id)
        logger.info(f"MissionService: Updated mission {mission_id}")
        return mission

    async def transition_status(self, db: AsyncSession, mission_id: str, new_status: MissionStatus) -> Mission:
        mission = await self.get_mission(db, mission_id)
        current_status = mission.status
        
        if new_status not in self.ALLOWED_TRANSITIONS.get(current_status, []):
            logger.warning(f"MissionService: Failed transition for {mission_id}: {current_status.value} -> {new_status.value}")
            raise InvalidMissionStateTransitionError(current_status.value, new_status.value)
            
        kwargs = {}
        if new_status == MissionStatus.RUNNING and not mission.started_at:
            kwargs["started_at"] = utc_now()
        elif new_status == MissionStatus.COMPLETED:
            kwargs["completed_at"] = utc_now()
            
        updated = await self.repository.update_status(db, mission_id, new_status, **kwargs)
        logger.info(f"MissionService: Transitioned {mission_id} to {new_status.value}")
        return updated

    async def assign_mission(self, db: AsyncSession, mission_id: str, assignment: MissionAssignment) -> Mission:
        mission = await self.get_mission(db, mission_id)
        
        if mission.status in [MissionStatus.COMPLETED, MissionStatus.CANCELLED, MissionStatus.FAILED]:
            raise InvalidMissionAssignmentError("Cannot assign a mission that is already completed, failed, or cancelled.")
            
        updated = await self.repository.assign(db, mission_id, assignment)
        logger.info(f"MissionService: Updated assignment for {mission_id}")
        return updated
