import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Float
from infrastructure.database import Base
from features.monitoring.domain import (
    MonitoringStatus,
    MonitoringCategory,
    TargetType,
    MonitoringFrequency,
    SituationState
)
from features.operations.domain import OperationPriority

def utc_now():
    return datetime.now(timezone.utc)

class MonitoringProfile(Base):
    __tablename__ = "monitoring_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    
    monitoring_category = Column(SQLEnum(MonitoringCategory), nullable=False)
    target_type = Column(SQLEnum(TargetType), nullable=False, default=TargetType.REGION)
    region = Column(String, nullable=False) # e.g. 'Hyderabad'
    
    priority = Column(SQLEnum(OperationPriority), nullable=False, default=OperationPriority.MEDIUM)
    frequency = Column(SQLEnum(MonitoringFrequency), nullable=False, default=MonitoringFrequency.FIVE_MINUTES)
    custom_frequency = Column(String, nullable=True)
    
    risk_threshold = Column(Float, nullable=False, default=70.0) # 0 to 100 score threshold
    current_risk_score = Column(Float, nullable=False, default=0.0)
    current_situation_state = Column(SQLEnum(SituationState), nullable=False, default=SituationState.NORMAL)
    
    status = Column(SQLEnum(MonitoringStatus), nullable=False, default=MonitoringStatus.PLANNED)
    
    # Associated generated components
    operation_id = Column(String, nullable=True, index=True)
    workflow_template = Column(String, nullable=True)
    notification_targets = Column(String, nullable=True)
    
    created_by = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)
