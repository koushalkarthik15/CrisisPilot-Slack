from pydantic import BaseModel
from typing import Dict

class IncidentMetrics(BaseModel):
    total_active: int
    newly_created_today: int
    total_resolved: int
    severity_distribution: Dict[str, int]

class OperationMetrics(BaseModel):
    total_active: int
    completed: int

class MissionMetrics(BaseModel):
    total_active: int
    completed: int
    failed: int

class RecommendationMetrics(BaseModel):
    total_pending: int
    total_approved: int
    total_rejected: int
    approval_rate_percent: float

class WatchlistMetrics(BaseModel):
    total_enabled: int
    articles_processed: int

class MiniAgentMetrics(BaseModel):
    total_registered: int
    total_enabled: int

class LLMMetrics(BaseModel):
    requests_today: int
    tokens_today: int
    max_tokens_per_day: int
    max_requests_per_day: int
    concurrent_requests: int

class OperationalSummary(BaseModel):
    incidents: IncidentMetrics
    operations: OperationMetrics
    missions: MissionMetrics
    recommendations: RecommendationMetrics
    watchlists: WatchlistMetrics
    mini_agents: MiniAgentMetrics
    llm: LLMMetrics
    mcp: Dict[str, str] = {"status": "Not Available (Audit Trail Pending)"}
