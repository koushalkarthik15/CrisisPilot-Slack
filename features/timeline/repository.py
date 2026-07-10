import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from features.timeline.models import TimelineEvent
from features.timeline.schemas import TimelineEventCreate

logger = logging.getLogger("crisispilot.timeline.repository")

class TimelineRepository:
    """Append-only persistence layer for Timeline Events."""
    
    async def create(self, db: AsyncSession, event_in: TimelineEventCreate) -> TimelineEvent:
        event = TimelineEvent(
            event_type=event_in.event_type,
            description=event_in.description,
            source=event_in.source,
            severity=event_in.severity,
            correlation_id=event_in.correlation_id,
            actor_id=event_in.actor_id,
            event_metadata=event_in.event_metadata,
            operation_id=event_in.operation_id,
            incident_id=event_in.incident_id,
            mission_id=event_in.mission_id,
            workflow_id=event_in.workflow_id
        )
        db.add(event)
        await db.flush()
        await db.refresh(event)
        logger.info(f"Created timeline event {event.id} ({event.event_type.value})")
        return event

    async def get(self, db: AsyncSession, event_id: str) -> Optional[TimelineEvent]:
        result = await db.execute(select(TimelineEvent).where(TimelineEvent.id == event_id))
        return result.scalars().first()

    async def list_by_operation(self, db: AsyncSession, operation_id: str) -> List[TimelineEvent]:
        result = await db.execute(
            select(TimelineEvent).where(TimelineEvent.operation_id == operation_id)
            .order_by(TimelineEvent.created_at.desc())
        )
        return list(result.scalars().all())
        
    async def list_by_incident(self, db: AsyncSession, incident_id: str) -> List[TimelineEvent]:
        result = await db.execute(
            select(TimelineEvent).where(TimelineEvent.incident_id == incident_id)
            .order_by(TimelineEvent.created_at.desc())
        )
        return list(result.scalars().all())
        
    async def list_by_mission(self, db: AsyncSession, mission_id: str) -> List[TimelineEvent]:
        result = await db.execute(
            select(TimelineEvent).where(TimelineEvent.mission_id == mission_id)
            .order_by(TimelineEvent.created_at.desc())
        )
        return list(result.scalars().all())
        
    async def list_by_workflow(self, db: AsyncSession, workflow_id: str) -> List[TimelineEvent]:
        result = await db.execute(
            select(TimelineEvent).where(TimelineEvent.workflow_id == workflow_id)
            .order_by(TimelineEvent.created_at.desc())
        )
        return list(result.scalars().all())
        
    # NOTE: Intentionally omitted update() and delete() to enforce immutability at the repository level.
