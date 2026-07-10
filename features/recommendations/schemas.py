from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from features.recommendations.domain import RecommendationPriority, RecommendationStatus


class RecommendationCreate(BaseModel):
    incident_id: Optional[str] = None
    operation_id: Optional[str] = None
    title: str
    description: str
    priority: RecommendationPriority
    confidence: float
    rationale: List[str]

class RecommendationUpdateStatus(BaseModel):
    """Only allows updating mutable review fields."""
    status: RecommendationStatus
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

class RecommendationResponse(BaseModel):
    id: str
    incident_id: Optional[str]
    operation_id: Optional[str]
    title: str
    description: str
    priority: RecommendationPriority
    confidence: float
    rationale: List[str]
    status: RecommendationStatus
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
