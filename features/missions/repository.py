import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from features.missions.domain import MissionStatus
from features.missions.models import Mission
from features.missions.schemas import MissionAssignment, MissionCreate, MissionUpdate

logger = logging.getLogger("crisispilot.missions.repository")

class MissionRepository:
    """Persistence layer for Missions."""

    async def create(self, db: AsyncSession, mission_in: MissionCreate, created_by: str) -> Mission:
        mission = Mission(
            name=mission_in.name,
            description=mission_in.description,
            objective=mission_in.objective,
            strategy=mission_in.strategy,
            priority=mission_in.priority,
            operation_id=mission_in.operation_id,
            incident_id=mission_in.incident_id,
            assigned_human_ids=mission_in.assigned_human_ids,
            assigned_mini_agent_id=mission_in.assigned_mini_agent_id,
            created_by=created_by,
            status=MissionStatus.CREATED
        )
        db.add(mission)
        await db.flush()
        await db.refresh(mission)
        logger.info(f"Created mission {mission.id} ({mission.name})")
        return mission

    async def get(self, db: AsyncSession, mission_id: str) -> Optional[Mission]:
        result = await db.execute(select(Mission).where(Mission.id == mission_id))
        return result.scalars().first()

    async def list_by_operation(self, db: AsyncSession, operation_id: str) -> List[Mission]:
        result = await db.execute(
            select(Mission).where(Mission.operation_id == operation_id)
            .order_by(Mission.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_incident(self, db: AsyncSession, incident_id: str) -> List[Mission]:
        result = await db.execute(
            select(Mission).where(Mission.incident_id == incident_id)
            .order_by(Mission.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, mission_id: str, update_data: MissionUpdate) -> Optional[Mission]:
        mission = await self.get(db, mission_id)
        if not mission:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return mission

        for key, value in update_dict.items():
            setattr(mission, key, value)

        await db.flush()
        await db.refresh(mission)
        logger.info(f"Updated mission {mission_id}")
        return mission

    async def update_status(self, db: AsyncSession, mission_id: str, new_status: MissionStatus, **kwargs) -> Optional[Mission]:
        mission = await self.get(db, mission_id)
        if not mission:
            return None

        mission.status = new_status
        for key, value in kwargs.items():
            setattr(mission, key, value)

        await db.flush()
        await db.refresh(mission)
        logger.info(f"Updated status for mission {mission_id} to {new_status}")
        return mission

    async def assign(self, db: AsyncSession, mission_id: str, assignment: MissionAssignment) -> Optional[Mission]:
        mission = await self.get(db, mission_id)
        if not mission:
            return None

        if assignment.assigned_human_ids is not None:
            mission.assigned_human_ids = assignment.assigned_human_ids

        if assignment.assigned_mini_agent_id is not None:
            mission.assigned_mini_agent_id = assignment.assigned_mini_agent_id

        await db.flush()
        await db.refresh(mission)
        logger.info(f"Assigned mission {mission_id}")
        return mission

    async def list_eligible_for_execution(self, db: AsyncSession, strategy: str, statuses: List[MissionStatus]) -> List[Mission]:
        result = await db.execute(
            select(Mission)
            .where(Mission.strategy == strategy)
            .where(Mission.status.in_(statuses))
            .order_by(Mission.created_at.asc())
        )
        return list(result.scalars().all())
