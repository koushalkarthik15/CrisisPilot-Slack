import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy import Enum as SQLEnum

from features.missions.domain import ExecutionStrategy, MissionPriority, MissionStatus
from infrastructure.database import Base


def utc_now():
    return datetime.now(timezone.utc)

class Mission(Base):
    __tablename__ = "missions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    objective = Column(String, nullable=False)

    status = Column(SQLEnum(MissionStatus), nullable=False, default=MissionStatus.CREATED)
    strategy = Column(SQLEnum(ExecutionStrategy), nullable=False, default=ExecutionStrategy.MANUAL)
    priority = Column(SQLEnum(MissionPriority), nullable=False, default=MissionPriority.MEDIUM)

    # Ownership (at least one must be populated, enforced by service)
    operation_id = Column(String, nullable=True, index=True)
    incident_id = Column(String, nullable=True, index=True)

    # Collaborative Assignment
    assigned_human_ids = Column(JSON, nullable=True) # JSON string array of IDs
    assigned_mini_agent_id = Column(String, nullable=True)

    created_by = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
