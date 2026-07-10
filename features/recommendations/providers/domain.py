from typing import List
from pydantic import BaseModel
from features.recommendations.domain import RecommendationPriority

class ProviderResult(BaseModel):
    title: str
    summary: str
    priority: RecommendationPriority
    immediate_actions: List[str]
    short_term_actions: List[str]
    long_term_actions: List[str]
    escalation_guidance: str
    rationale: List[str]
    confidence: float
