import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.metrics import MetricsProvider
from features.analytics.schemas import (
    IncidentMetrics,
    LLMMetrics,
    MiniAgentMetrics,
    MissionMetrics,
    OperationalSummary,
    OperationMetrics,
    RecommendationMetrics,
    WatchlistMetrics,
)
from features.incident_management.domain import IncidentStatus
from features.incident_management.models import Incident
from features.mini_agents.models import MiniAgentModel
from features.recommendations.domain import RecommendationStatus
from features.recommendations.models import Recommendation
from features.watchlists.models import Watchlist, WatchlistArticle
from features.workflow.domain import DecisionAction
from features.workflow.models import AuditRecord

logger = logging.getLogger("crisispilot.analytics.service")

class AnalyticsService:
    def __init__(self, llm_metrics_provider: MetricsProvider):
        self.llm_metrics_provider = llm_metrics_provider

    async def get_operational_summary(self, db: AsyncSession) -> OperationalSummary:
        logger.info("Generating Operational Summary...")

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Incident Metrics
        active_statuses = [
            IncidentStatus.DRAFT.name,
            IncidentStatus.CREATED.name,
            IncidentStatus.ACTIVE.name,
            IncidentStatus.UPDATED.name,
            IncidentStatus.MONITORING.name
        ]

        total_active_res = await db.execute(select(func.count(Incident.id)).filter(Incident.status.in_(active_statuses)))
        total_active = total_active_res.scalar() or 0

        new_today_res = await db.execute(select(func.count(Incident.id)).filter(Incident.created_at >= today_start))
        newly_created_today = new_today_res.scalar() or 0

        resolved_res = await db.execute(select(func.count(Incident.id)).filter(Incident.status == IncidentStatus.RESOLVED.name))
        total_resolved = resolved_res.scalar() or 0

        severity_dist_res = await db.execute(select(Incident.severity, func.count(Incident.id)).group_by(Incident.severity))
        severity_distribution = {row[0].name: row[1] for row in severity_dist_res.all()}

        incident_metrics = IncidentMetrics(
            total_active=total_active,
            newly_created_today=newly_created_today,
            total_resolved=total_resolved,
            severity_distribution=severity_distribution
        )

        # 1.5 Operation Metrics
        from features.operations.domain import OperationStatus
        from features.operations.models import Operation

        op_active_res = await db.execute(select(func.count(Operation.id)).filter(Operation.status != OperationStatus.COMPLETED.name))
        op_active = op_active_res.scalar() or 0

        op_comp_res = await db.execute(select(func.count(Operation.id)).filter(Operation.status == OperationStatus.COMPLETED.name))
        op_completed = op_comp_res.scalar() or 0

        operation_metrics = OperationMetrics(
            total_active=op_active,
            completed=op_completed
        )

        # 1.6 Mission Metrics
        from features.missions.domain import MissionStatus
        from features.missions.models import Mission

        mission_active_res = await db.execute(select(func.count(Mission.id)).filter(
            Mission.status.in_([
                MissionStatus.CREATED.name,
                MissionStatus.SCHEDULED.name,
                MissionStatus.RUNNING.name,
                MissionStatus.PAUSED.name
            ])
        ))
        mission_active = mission_active_res.scalar() or 0

        mission_comp_res = await db.execute(select(func.count(Mission.id)).filter(Mission.status == MissionStatus.COMPLETED.name))
        mission_completed = mission_comp_res.scalar() or 0

        mission_fail_res = await db.execute(select(func.count(Mission.id)).filter(Mission.status == MissionStatus.FAILED.name))
        mission_failed = mission_fail_res.scalar() or 0

        mission_metrics = MissionMetrics(
            total_active=mission_active,
            completed=mission_completed,
            failed=mission_failed
        )

        # 2. Recommendation Metrics
        pending_res = await db.execute(select(func.count(Recommendation.id)).filter(
            Recommendation.status.in_([RecommendationStatus.PENDING_APPROVAL, "PENDING_REVIEW"])
        ))
        total_pending = pending_res.scalar() or 0

        approved_res = await db.execute(select(func.count(AuditRecord.id)).filter(AuditRecord.action == DecisionAction.APPROVE))
        total_approved = approved_res.scalar() or 0

        rejected_res = await db.execute(select(func.count(AuditRecord.id)).filter(AuditRecord.action == DecisionAction.REJECT))
        total_rejected = rejected_res.scalar() or 0

        total_decisions = total_approved + total_rejected
        approval_rate = (total_approved / total_decisions * 100) if total_decisions > 0 else 0.0

        recommendation_metrics = RecommendationMetrics(
            total_pending=total_pending,
            total_approved=total_approved,
            total_rejected=total_rejected,
            approval_rate_percent=round(approval_rate, 2)
        )

        # 3. Watchlist Metrics
        enabled_wl_res = await db.execute(select(func.count(Watchlist.id)).filter(Watchlist.enabled == True))
        total_enabled = enabled_wl_res.scalar() or 0

        articles_res = await db.execute(select(func.count(WatchlistArticle.id)))
        articles_processed = articles_res.scalar() or 0

        watchlist_metrics = WatchlistMetrics(
            total_enabled=total_enabled,
            articles_processed=articles_processed
        )

        # 4. Mini-Agent Metrics
        total_agents_res = await db.execute(select(func.count(MiniAgentModel.id)))
        total_registered = total_agents_res.scalar() or 0

        enabled_agents_res = await db.execute(select(func.count(MiniAgentModel.id)).filter(MiniAgentModel.is_enabled == True))
        total_enabled_agents = enabled_agents_res.scalar() or 0

        mini_agent_metrics = MiniAgentMetrics(
            total_registered=total_registered,
            total_enabled=total_enabled_agents
        )

        # 5. LLM Metrics
        llm_raw = await self.llm_metrics_provider.get_metrics()
        llm_metrics = LLMMetrics(
            requests_today=llm_raw.get("requests_today", 0),
            tokens_today=llm_raw.get("tokens_today", 0),
            max_tokens_per_day=llm_raw.get("max_tokens_per_day", 0),
            max_requests_per_day=llm_raw.get("max_requests_per_day", 0),
            concurrent_requests=llm_raw.get("concurrent_requests", 0)
        )

        return OperationalSummary(
            incidents=incident_metrics,
            operations=operation_metrics,
            missions=mission_metrics,
            recommendations=recommendation_metrics,
            watchlists=watchlist_metrics,
            mini_agents=mini_agent_metrics,
            llm=llm_metrics
        )
