import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, JSON
from infrastructure.database import Base
from features.incident_management.domain import IncidentStatus, IncidentSeverity

def utc_now():
    return datetime.now(timezone.utc)

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(SQLEnum(IncidentStatus), nullable=False, default=IncidentStatus.DRAFT)
    severity = Column(SQLEnum(IncidentSeverity), nullable=False, default=IncidentSeverity.MEDIUM)
    channel_id = Column(String, nullable=False, index=True)
    operation_id = Column(String, nullable=True, index=True)
    mission_id = Column(String, nullable=True, index=True)
    parent_id = Column(String, nullable=True, index=True)
    thread_ts = Column(String, nullable=True)
    assigned_user_id = Column(String, nullable=True, index=True)
    execution_details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
