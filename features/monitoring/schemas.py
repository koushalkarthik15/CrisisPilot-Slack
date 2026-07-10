from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from features.monitoring.domain import (
    MonitoringCategory,
    MonitoringFrequency,
    MonitoringStatus,
    SituationState,
    TargetType,
)
from features.operations.domain import OperationPriority


class MonitoringProfileBase(BaseModel):
    name: str = Field(..., description="Name of the monitoring profile")
    description: Optional[str] = Field(None, description="Description of the monitoring profile")
    monitoring_category: MonitoringCategory = Field(..., description="Category to monitor")
    target_type: TargetType = Field(default=TargetType.REGION, description="Type of target to monitor")
    region: str = Field(..., description="Geographic region or specific target name")
    priority: OperationPriority = Field(default=OperationPriority.MEDIUM)
    frequency: MonitoringFrequency = Field(default=MonitoringFrequency.FIVE_MINUTES)
    custom_frequency: Optional[str] = None
    risk_threshold: float = Field(default=70.0, ge=0.0, le=100.0)
    workflow_template: Optional[str] = None
    notification_targets: Optional[str] = None

class MonitoringProfileCreate(MonitoringProfileBase):
    pass

class MonitoringProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[OperationPriority] = None
    frequency: Optional[MonitoringFrequency] = None
    risk_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    current_risk_score: Optional[float] = None
    current_situation_state: Optional[SituationState] = None
    notification_targets: Optional[str] = None

class MonitoringProfileRead(MonitoringProfileBase):
    id: str
    status: MonitoringStatus
    current_risk_score: float
    current_situation_state: SituationState
    operation_id: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    last_scan_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
