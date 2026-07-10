from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from features.timeline.domain import (
    TimelineEventSeverity,
    TimelineEventSource,
    TimelineEventType,
)


class TimelineEventBase(BaseModel):
    event_type: TimelineEventType = Field(..., description="The type of the event")
    description: str = Field(..., description="Human-readable description of the event")
    source: TimelineEventSource = Field(default=TimelineEventSource.SYSTEM, description="Source of the event")
    severity: TimelineEventSeverity = Field(default=TimelineEventSeverity.INFO, description="Severity of the event")
    correlation_id: Optional[str] = Field(None, description="Optional ID to correlate multiple events")
    actor_id: Optional[str] = Field(None, description="The user or system agent that caused the event")
    event_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional structured metadata")

class TimelineEventCreate(TimelineEventBase):
    operation_id: Optional[str] = None
    incident_id: Optional[str] = None
    mission_id: Optional[str] = None
    workflow_id: Optional[str] = None

class TimelineEventRead(TimelineEventBase):
    id: str
    operation_id: Optional[str]
    incident_id: Optional[str]
    mission_id: Optional[str]
    workflow_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
