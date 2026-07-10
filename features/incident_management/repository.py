from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from shared.repository import BaseRepository
from features.incident_management.models import Incident
from features.incident_management.schemas import IncidentCreate, IncidentUpdate
from features.incident_management.domain import IncidentStatus

class IncidentRepository(BaseRepository[Incident, IncidentCreate, IncidentUpdate]):
    def __init__(self):
        super().__init__(Incident)

    async def get_active_by_channel(self, db: AsyncSession, channel_id: str) -> Optional[Incident]:
        """
        Fetches the most recent active incident for a given channel.
        Active incidents are those not in ARCHIVED or RESOLVED status.
        """
        inactive_statuses = [IncidentStatus.ARCHIVED, IncidentStatus.RESOLVED]
        result = await db.execute(
            select(self.model)
            .filter(self.model.channel_id == channel_id)
            .filter(~self.model.status.in_(inactive_statuses))
            .order_by(self.model.created_at.desc())
        )
        return result.scalars().first()

    async def get_by_mission_id(self, db: AsyncSession, mission_id: str) -> list[Incident]:
        result = await db.execute(select(self.model).filter(self.model.mission_id == mission_id))
        return list(result.scalars().all())
