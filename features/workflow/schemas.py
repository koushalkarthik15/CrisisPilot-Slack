from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from features.workflow.domain import DecisionAction


class DecisionRequest(BaseModel):
    recommendation_id: str
    reviewer_id: str
    action: DecisionAction
    comments: Optional[str] = None

class AuditRecordCreate(BaseModel):
    incident_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    reviewer_id: str
    action: DecisionAction
    previous_status: str
    new_status: str
    comments: Optional[str] = None

class AuditRecordResponse(BaseModel):
    id: str
    incident_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    reviewer_id: str
    action: DecisionAction
    previous_status: str
    new_status: str
    comments: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True
