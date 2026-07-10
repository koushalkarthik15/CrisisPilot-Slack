import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from features.timeline.repository import TimelineRepository
from features.timeline.schemas import TimelineEventCreate
from features.timeline.models import TimelineEvent
from features.timeline.exceptions import InvalidTimelineEventError

logger = logging.getLogger("crisispilot.timeline.service")

class TimelineService:
    """Business logic and validation for Timeline Events."""
    
    def __init__(self, repository: TimelineRepository):
        self.repository = repository

    def _validate_ownership(self, event_in: TimelineEventCreate):
        if not any([event_in.operation_id, event_in.incident_id, event_in.mission_id, event_in.workflow_id]):
            logger.warning("Failed timeline event creation: No ownership context provided.")
            raise InvalidTimelineEventError("A timeline event must belong to at least one entity (Operation, Incident, Mission, or Workflow).")

    async def create_event(self, db: AsyncSession, event_in: TimelineEventCreate) -> TimelineEvent:
        self._validate_ownership(event_in)
        
        event = await self.repository.create(db, event_in)
        logger.info(f"TimelineService: Created event {event.id}")
        return event

    async def get_event(self, db: AsyncSession, event_id: str) -> Optional[TimelineEvent]:
        return await self.repository.get(db, event_id)

    async def list_events_by_operation(self, db: AsyncSession, operation_id: str) -> List[TimelineEvent]:
        return await self.repository.list_by_operation(db, operation_id)
        
    async def list_events_by_incident(self, db: AsyncSession, incident_id: str) -> List[TimelineEvent]:
        return await self.repository.list_by_incident(db, incident_id)
        
    async def list_events_by_mission(self, db: AsyncSession, mission_id: str) -> List[TimelineEvent]:
        return await self.repository.list_by_mission(db, mission_id)
        
    async def list_events_by_workflow(self, db: AsyncSession, workflow_id: str) -> List[TimelineEvent]:
        return await self.repository.list_by_workflow(db, workflow_id)
