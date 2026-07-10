import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String
from sqlalchemy import Enum as SQLEnum

from features.workflow.domain import DecisionAction
from infrastructure.database import Base


def utc_now():
    return datetime.now(timezone.utc)

class AuditRecord(Base):
    __tablename__ = "audit_trails"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=True, index=True)
    recommendation_id = Column(String, nullable=True, index=True)
    reviewer_id = Column(String, nullable=False)
    action = Column(SQLEnum(DecisionAction), nullable=False)
    previous_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    comments = Column(String, nullable=True)

    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)
