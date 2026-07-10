import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String
from sqlalchemy import Enum as SQLEnum

from features.recommendations.domain import RecommendationPriority, RecommendationStatus
from infrastructure.database import Base


def utc_now():
    return datetime.now(timezone.utc)

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey('incidents.id', ondelete='CASCADE'), nullable=True, index=True)
    operation_id = Column(String, ForeignKey('operations.id', ondelete='CASCADE'), nullable=True, index=True)

    # Immutable fields (after creation)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    priority = Column(SQLEnum(RecommendationPriority), nullable=False)
    confidence = Column(Float, nullable=False)
    rationale = Column(JSON, nullable=False)

    # Mutable fields
    status = Column(SQLEnum(RecommendationStatus), nullable=False, default=RecommendationStatus.PENDING_APPROVAL)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Execution Tracking
    approved_by = Column(String, nullable=True)
    assigned_to = Column(String, nullable=True)
    assigned_by = Column(String, nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
