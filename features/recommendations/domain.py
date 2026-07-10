from enum import Enum
from pydantic import BaseModel
from typing import List

class RecommendationPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class RecommendationStatus(str, Enum):
    PENDING_APPROVAL = "Pending Approval"
    PENDING_REVIEW = "PENDING_REVIEW"  # Legacy support for seeded mock data
    APPROVED = "Approved"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    REJECTED = "Rejected"

class RecommendationRuleResult(BaseModel):
    title: str
    description: str
    priority: RecommendationPriority
    confidence: float
    rationale: List[str]
