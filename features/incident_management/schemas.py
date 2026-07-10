from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from features.incident_management.domain import IncidentStatus, IncidentSeverity

class IncidentCreate(BaseModel):
    title: str
    description: str
    channel_id: str
    operation_id: Optional[str] = None
    mission_id: Optional[str] = None
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.DRAFT
    execution_details: Optional[dict] = None

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[IncidentSeverity] = None
    execution_details: Optional[dict] = None

class IncidentResponse(BaseModel):
    id: str
    title: str
    description: str
    status: IncidentStatus
    severity: IncidentSeverity
    channel_id: str
    operation_id: Optional[str]
    mission_id: Optional[str]
    execution_details: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
