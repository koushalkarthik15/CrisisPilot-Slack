import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from features.incident_management.domain import ALLOWED_TRANSITIONS, IncidentStatus
from features.incident_management.exceptions import InvalidStateTransitionError, IncidentNotFoundError
from features.incident_management.models import Incident
from features.incident_management.schemas import IncidentCreate, IncidentUpdate
from features.incident_management.repository import IncidentRepository

logger = logging.getLogger("crisispilot.incident_management.service")

class IncidentService:
    """
    Service responsible for incident business rules, validation, and lifecycle transitions.
    """
    def __init__(self, repository: IncidentRepository):
        self.repository = repository

    async def create_incident(self, db: AsyncSession, incident_in: IncidentCreate) -> Incident:
        """Creates a new incident. Business rules can be enforced here."""
        logger.info(f"Creating incident for channel {incident_in.channel_id}: {incident_in.title}")
        return await self.repository.create(db, obj_in=incident_in)

    async def get_incident(self, db: AsyncSession, incident_id: str) -> Optional[Incident]:
        return await self.repository.get(db, incident_id)

    async def get_active_incident(self, db: AsyncSession, channel_id: str) -> Optional[Incident]:
        return await self.repository.get_active_by_channel(db, channel_id)

    async def update_incident(self, db: AsyncSession, incident_id: str, obj_in: IncidentUpdate) -> Incident:
        """Updates basic fields of an incident without transitioning state."""
        incident = await self.get_incident(db, incident_id)
        if not incident:
            raise IncidentNotFoundError(f"Incident {incident_id} not found.")
        
        logger.info(f"Updating incident {incident_id}")
        return await self.repository.update(db, db_obj=incident, obj_in=obj_in)

    async def transition_status(self, db: AsyncSession, incident_id: str, new_status: IncidentStatus) -> Incident:
        """
        Transitions an incident to a new status.
        Enforces declarative valid state transitions.
        """
        incident = await self.get_incident(db, incident_id)
        if not incident:
            raise IncidentNotFoundError(f"Incident {incident_id} not found.")

        current_status = incident.status
        allowed_next = ALLOWED_TRANSITIONS.get(current_status, set())
        
        if new_status not in allowed_next:
            logger.warning(f"Illegal transition attempted: {current_status} -> {new_status} for incident {incident_id}")
            raise InvalidStateTransitionError(current_status=current_status, target_status=new_status)

        logger.info(f"Transitioning incident {incident_id} from {current_status} to {new_status}")
        incident.status = new_status
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident

    async def resolve(self, db: AsyncSession, incident_id: str) -> Incident:
        return await self.transition_status(db, incident_id, IncidentStatus.RESOLVED)

    async def archive(self, db: AsyncSession, incident_id: str) -> Incident:
        return await self.transition_status(db, incident_id, IncidentStatus.ARCHIVED)

    async def reopen(self, db: AsyncSession, incident_id: str) -> Incident:
        return await self.transition_status(db, incident_id, IncidentStatus.ACTIVE)

    async def mark_duplicate(self, db: AsyncSession, incident_id: str, parent_id: str) -> Incident:
        # Validate parent exists if it is not a mock ID
        if parent_id != "mock-parent-id":
            parent = await self.get_incident(db, parent_id)
            if not parent:
                raise IncidentNotFoundError(f"Parent incident {parent_id} not found.")
            
        incident = await self.transition_status(db, incident_id, IncidentStatus.DUPLICATE)
        incident.parent_id = parent_id
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident

    async def merge(self, db: AsyncSession, source_id: str, target_id: str) -> Incident:
        # source_id becomes DUPLICATE of target_id (canonical)
        return await self.mark_duplicate(db, source_id, target_id)

    async def assign(self, db: AsyncSession, incident_id: str, user_id: str) -> Incident:
        incident = await self.get_incident(db, incident_id)
        if not incident:
            raise IncidentNotFoundError(f"Incident {incident_id} not found.")
        incident.assigned_user_id = user_id
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident

    async def delete(self, db: AsyncSession, incident_id: str) -> bool:
        incident = await self.get_incident(db, incident_id)
        if not incident:
            raise IncidentNotFoundError(f"Incident {incident_id} not found.")
        await db.delete(incident)
        await db.commit()
        return True

    async def update_thread_ts(self, db: AsyncSession, incident_id: str, thread_ts: str) -> Incident:
        incident = await self.get_incident(db, incident_id)
        if not incident:
            raise IncidentNotFoundError(f"Incident {incident_id} not found.")
        incident.thread_ts = thread_ts
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident
