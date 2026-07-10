import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, JSON
from infrastructure.database import Base
from features.timeline.domain import TimelineEventType, TimelineEventSource, TimelineEventSeverity

def utc_now():
    return datetime.now(timezone.utc)

class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(SQLEnum(TimelineEventType), nullable=False)
    description = Column(String, nullable=False)
    source = Column(SQLEnum(TimelineEventSource), nullable=False, default=TimelineEventSource.SYSTEM)
    severity = Column(SQLEnum(TimelineEventSeverity), nullable=False, default=TimelineEventSeverity.INFO)
    
    correlation_id = Column(String, nullable=True)
    actor_id = Column(String, nullable=True)
    
    event_metadata = Column(JSON, nullable=True) # Renamed from metadata to avoid SQLAlchemy conflicts
    
    # Ownership
    operation_id = Column(String, nullable=True, index=True)
    incident_id = Column(String, nullable=True, index=True)
    mission_id = Column(String, nullable=True, index=True)
    workflow_id = Column(String, nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    # No updated_at intentionally to represent immutability natively
