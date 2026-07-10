import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy import Enum as SQLEnum

from features.workflows.domain import WorkflowPriority, WorkflowStatus
from infrastructure.database import Base


def utc_now():
    return datetime.now(timezone.utc)

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    priority = Column(SQLEnum(WorkflowPriority), nullable=False, default=WorkflowPriority.MEDIUM)

    status = Column(SQLEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.DRAFT)

    stages = Column(JSON, nullable=False) # JSON array of WorkflowStageType
    current_stage_index = Column(Integer, nullable=False, default=0)

    # Ownership (at least one must be populated, enforced by service)
    operation_id = Column(String, nullable=True, index=True)
    incident_id = Column(String, nullable=True, index=True)

    created_by = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
