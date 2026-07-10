import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, JSON, Float
from infrastructure.database import Base
from features.evidence.domain import EvidenceType

def utc_now():
    return datetime.now(timezone.utc)

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    source = Column(String, nullable=True)
    evidence_type = Column(SQLEnum(EvidenceType), nullable=False)
    content = Column(String, nullable=True)
    
    confidence_score = Column(Float, nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)
    
    evidence_metadata = Column(JSON, nullable=True) # Renamed to avoid conflicts
    
    submitted_by = Column(String, nullable=True)
    
    # Ownership
    operation_id = Column(String, nullable=True, index=True)
    incident_id = Column(String, nullable=True, index=True)
    mission_id = Column(String, nullable=True, index=True)
    workflow_id = Column(String, nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
