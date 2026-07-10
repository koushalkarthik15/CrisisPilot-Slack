import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from features.missions.schemas import MissionCreate
from features.monitoring.domain import (
    MonitoringCategory,
    MonitoringStatus,
)
from features.monitoring.evaluator import SituationEvaluator
from features.monitoring.exceptions import (
    DuplicateMonitoringProfileNameError,
    MonitoringProfileNotFoundError,
)
from features.monitoring.models import MonitoringProfile
from features.monitoring.notification_policy import NotificationPolicyEngine
from features.monitoring.repository import MonitoringRepository
from features.monitoring.schemas import MonitoringProfileCreate, MonitoringProfileUpdate
from features.operations.schemas import OperationCreate
from features.timeline.domain import (
    TimelineEventSeverity,
    TimelineEventSource,
    TimelineEventType,
)
from features.timeline.schemas import TimelineEventCreate
from features.workflows.domain import WorkflowStageType
from features.workflows.schemas import WorkflowCreate as OperationalWorkflowCreate

logger = logging.getLogger("crisispilot.monitoring.service")

def utc_now():
    return datetime.now(timezone.utc)

class MonitoringService:
    """Orchestrates Monitoring Profiles and coordinates automatic provisioning."""

    def __init__(self, repository: MonitoringRepository, evaluator: SituationEvaluator, notification_policy: NotificationPolicyEngine):
        self.repository = repository
        self.evaluator = evaluator
        self.notification_policy = notification_policy

    async def get_profile(self, db: AsyncSession, profile_id: str) -> Optional[MonitoringProfile]:
        return await self.repository.get(db, profile_id)

    async def list_active_profiles(self, db: AsyncSession) -> List[MonitoringProfile]:
        return await self.repository.list_active(db)

    async def create_monitoring_profile(self, db: AsyncSession, state_manager, profile_in: MonitoringProfileCreate, created_by: str) -> MonitoringProfile:
        existing = await self.repository.get_by_name(db, profile_in.name)
        if existing:
            raise DuplicateMonitoringProfileNameError(profile_in.name)

        profile = await self.repository.create(db, profile_in, created_by)

        # Automatic Provisioning Sequence
        try:
            # 1. Provision Operation
            op_create = OperationCreate(
                name=f"Monitoring: {profile.name}",
                description=profile.description or f"Auto-provisioned operation for monitoring {profile.region}",
                priority=profile.priority
            )
            operation = await state_manager.create_operation(db, op_create, created_by)

            # Link operation to profile
            profile = await self.repository.update(db, profile.id, MonitoringProfileUpdate())
            profile.operation_id = operation.id
            await db.flush()

            # 2. Provision Operational Workflow
            template_name = profile.workflow_template or f"{profile.monitoring_category.name}_RESPONSE_WORKFLOW"
            workflow_create = OperationalWorkflowCreate(
                name=template_name,
                description=f"Workflow for {profile.name}",
                stages=[WorkflowStageType.INVESTIGATION, WorkflowStageType.EVIDENCE_COLLECTION, WorkflowStageType.RECOMMENDATION],
                operation_id=operation.id
            )
            workflow = await state_manager.create_operational_workflow(db, workflow_create, created_by)

            # 3. Provision Missions based on template logic
            missions_to_create = self._get_template_missions(profile)
            for m_data in missions_to_create:
                mission_create = MissionCreate(
                    operation_id=operation.id,
                    name=m_data["name"],
                    objective=m_data["objective"],
                    strategy=m_data["strategy"]
                )
                mission = await state_manager.create_mission(db, mission_create, created_by)

            # 4. Update Status and Timeline
            from features.operations.domain import OperationStatus
            await state_manager.transition_operation_status(db, operation.id, OperationStatus.ACTIVE)

            profile = await self.repository.update_status(
                db, profile.id, MonitoringStatus.ACTIVE, started_at=utc_now()
            )

            tl_event = TimelineEventCreate(
                event_type=TimelineEventType.LIFECYCLE_CHANGE,
                source=TimelineEventSource.SYSTEM,
                severity=TimelineEventSeverity.INFO,
                description=f"Monitoring Profile '{profile.name}' started. Provisioned Operation, Workflow, and Missions.",
                operation_id=operation.id
            )
            await state_manager.create_timeline_event(db, tl_event)

            return profile

        except Exception as e:
            logger.error(f"Failed to auto-provision resources for profile {profile.id}: {e}", exc_info=True)
            profile.status = MonitoringStatus.STOPPED
            await db.flush()
            raise e

    def _get_template_missions(self, profile: MonitoringProfileCreate) -> List[Dict[str, str]]:
        missions = []
        if profile.monitoring_category == MonitoringCategory.FLOOD:
            missions = [
                {"name": f"Weather Scan - {profile.region}", "objective": "Monitor precipitation and forecasts", "strategy": "SCHEDULED"},
                {"name": f"News Scan - {profile.region}", "objective": "Monitor local news for flood reports", "strategy": "SCHEDULED"},
                {"name": f"Maps Scan - {profile.region}", "objective": "Monitor traffic and road closures", "strategy": "SCHEDULED"}
            ]
        elif profile.monitoring_category == MonitoringCategory.CYBERSECURITY:
            missions = [
                {"name": f"Threat Intel - {profile.region}", "objective": "Monitor threat feeds", "strategy": "SCHEDULED"},
                {"name": f"Vulnerability Scan - {profile.region}", "objective": "Check exposed infrastructure", "strategy": "SCHEDULED"},
                {"name": f"News Scan - {profile.region}", "objective": "Monitor security breaches in news", "strategy": "SCHEDULED"}
            ]
        else:
            missions = [
                {"name": f"General Intel - {profile.region}", "objective": f"Monitor {profile.region} for {profile.monitoring_category.name}", "strategy": "SCHEDULED"}
            ]
        return missions

    async def process_scan_results(self, db: AsyncSession, state_manager, profile_id: str, observations: List[Dict[str, Any]]) -> MonitoringProfile:
        profile = await self.repository.get(db, profile_id)
        if not profile:
            raise MonitoringProfileNotFoundError(profile_id)

        old_state = profile.current_situation_state
        old_risk = profile.current_risk_score

        # 1. Evaluate Situation
        new_state, new_risk = self.evaluator.evaluate(observations, profile.risk_threshold)

        # 2. Update Profile State
        update_data = MonitoringProfileUpdate(
            current_risk_score=new_risk,
            current_situation_state=new_state
        )
        profile = await self.repository.update(db, profile_id, update_data)
        profile.last_scan_at = utc_now()
        await db.flush()

        # 3. Execute Notification Policy
        await self.notification_policy.evaluate_and_notify(
            db, state_manager, profile, old_state, new_state, old_risk, new_risk
        )

        # 4. Generate Incident Recommendation if critical threshold crossed (and state escalated)
        if new_risk >= profile.risk_threshold and old_risk < profile.risk_threshold:
            # We crossed the threshold, so we generate an incident recommendation via RecommendationEngine
            try:
                context = {
                    "operation_id": profile.operation_id,
                    "title": f"Threshold Crossed: {profile.name}",
                    "description": f"Monitoring profile {profile.name} has crossed the risk threshold ({new_risk:.1f} >= {profile.risk_threshold:.1f}). Current State: {new_state.name}."
                }
                recs = await state_manager.recommendation_service.generate_recommendations(db, context, observations)
                logger.info(f"Generated {len(recs)} recommendations for Operation {profile.operation_id}.")

                # Publish recommendations to Slack
                for rec in recs:
                    if profile.notification_targets:
                        for target in profile.notification_targets.split(","):
                            target = target.strip()
                            if target:
                                try:
                                    await self.notification_policy.notification_engine.publish_recommendation(
                                        recommendation=rec,
                                        channel_id=target
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to publish recommendation to Slack channel {target}: {e}")

                # Create timeline event for the recommendation
                tl_event = TimelineEventCreate(
                    event_type=TimelineEventType.RECOMMENDATION_EVENT,
                    source=TimelineEventSource.SYSTEM,
                    severity=TimelineEventSeverity.WARNING,
                    description=f"Incident Recommendation Generated: {recs[0].title if recs else 'Assess Situation'}",
                    operation_id=profile.operation_id
                )
                await state_manager.create_timeline_event(db, tl_event)
            except Exception as e:
                logger.error(f"Failed to generate recommendation via RecommendationEngine: {e}", exc_info=True)

        return profile

    async def transition_status(self, db: AsyncSession, profile_id: str, new_status: MonitoringStatus) -> MonitoringProfile:
        profile = await self.repository.get(db, profile_id)
        if not profile:
            raise MonitoringProfileNotFoundError(profile_id)

        if profile.status == new_status:
            return profile

        kwargs = {}
        if new_status == MonitoringStatus.STOPPED:
            kwargs["stopped_at"] = utc_now()
        elif new_status == MonitoringStatus.ACTIVE and profile.status == MonitoringStatus.PAUSED:
            pass # Resuming

        profile = await self.repository.update_status(db, profile_id, new_status, **kwargs)
        return profile
