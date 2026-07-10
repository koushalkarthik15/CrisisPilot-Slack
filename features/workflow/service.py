import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from features.workflow.domain import DecisionAction, WorkflowEventPayload, DecisionStatus
from features.workflow.schemas import DecisionRequest, AuditRecordCreate
from features.workflow.repository import AuditRepository
from features.workflow.exceptions import InvalidDecisionTransitionError
from features.recommendations.repository import RecommendationRepository
from features.recommendations.schemas import RecommendationUpdateStatus
from features.recommendations.domain import RecommendationStatus
from features.recommendations.exceptions import RecommendationNotFoundError
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.notifications import NotificationEngine

logger = logging.getLogger("crisispilot.workflow.service")

class WorkflowService:
    """
    Manages the Human-in-the-Loop decision lifecycle for recommendations.
    Enforces state transitions, updates recommendation status through the persistence layer,
    records the immutable audit trail, and triggers notification hooks.
    """
    def __init__(self, 
                 audit_repository: AuditRepository, 
                 recommendation_repository: RecommendationRepository,
                 notification_engine: 'NotificationEngine'):
        self.audit_repository = audit_repository
        self.recommendation_repository = recommendation_repository
        self.notification_engine = notification_engine

    def _map_action_to_status(self, action: DecisionAction) -> RecommendationStatus:
        """Maps a DecisionAction to the resulting RecommendationStatus."""
        mapping = {
            DecisionAction.APPROVE: RecommendationStatus.APPROVED,
            DecisionAction.REJECT: RecommendationStatus.REJECTED,
            DecisionAction.AUTO_APPROVE: RecommendationStatus.APPROVED,
            DecisionAction.ASSIGN: RecommendationStatus.ASSIGNED,
            DecisionAction.START_EXECUTION: RecommendationStatus.IN_PROGRESS,
            DecisionAction.COMPLETE_EXECUTION: RecommendationStatus.COMPLETED,
        }
        # Extend mapping as more actions (REQUEST_CHANGES, ESCALATE) are implemented
        if action not in mapping:
            raise ValueError(f"Action {action} is not yet supported for recommendation status transitions.")
        return mapping[action]

    async def apply_decision(self, db: AsyncSession, request: DecisionRequest) -> Any:
        """
        Processes a workflow decision.
        Workflow:
        1. Validate transition
        2. Persist Recommendation status via repository
        3. Persist Audit Record
        4. Trigger Notification Hook
        """
        logger.info(f"Processing decision {request.action.value} on recommendation {request.recommendation_id}")
        
        # 1. Fetch Recommendation
        rec = await self.recommendation_repository.get(db, request.recommendation_id)
        if not rec:
            raise RecommendationNotFoundError(f"Recommendation {request.recommendation_id} not found.")

        current_status = rec.status
        
        # 2. Validate workflow transition
        # Only allow transitions from valid previous states
        valid_transitions = {
            DecisionAction.APPROVE: [RecommendationStatus.PENDING_APPROVAL],
            DecisionAction.REJECT: [RecommendationStatus.PENDING_APPROVAL],
            DecisionAction.ASSIGN: [RecommendationStatus.PENDING_APPROVAL, RecommendationStatus.APPROVED, RecommendationStatus.ASSIGNED],
            DecisionAction.START_EXECUTION: [RecommendationStatus.ASSIGNED],
            DecisionAction.COMPLETE_EXECUTION: [RecommendationStatus.IN_PROGRESS],
        }
        
        allowed_states = valid_transitions.get(request.action, [])
        if current_status not in allowed_states:
            raise InvalidDecisionTransitionError(action=request.action.value, current_status=current_status.value)
            
        new_status = self._map_action_to_status(request.action)
        
        # 3. Persist Recommendation Status
        # We manually update fields on rec if needed, or pass them in obj_in
        update_schema = RecommendationUpdateStatus(
            status=new_status,
            reviewed_by=request.reviewer_id if request.action in [DecisionAction.APPROVE, DecisionAction.REJECT] else rec.reviewed_by,
            reviewed_at=datetime.now(timezone.utc) if request.action in [DecisionAction.APPROVE, DecisionAction.REJECT] else rec.reviewed_at
        )
        updated_rec = await self.recommendation_repository.update(db, db_obj=rec, obj_in=update_schema)
        
        # 4. Persist Audit Record
        audit_schema = AuditRecordCreate(
            recommendation_id=request.recommendation_id,
            reviewer_id=request.reviewer_id,
            action=request.action,
            previous_status=current_status.value,
            new_status=new_status.value,
            comments=request.comments
        )
        audit_record = await self.audit_repository.create(db, obj_in=audit_schema)
        
        # 5. Trigger Notification Hook
        event_payload = WorkflowEventPayload(
            recommendation_id=request.recommendation_id,
            action=request.action,
            reviewer_id=request.reviewer_id,
            status=DecisionStatus.COMPLETED,
            comments=request.comments
        )
        await self.notification_engine.publish_workflow_event(event_payload)
        
        return audit_record
        
    async def log_incident_action(self, db: AsyncSession, incident_id: str, user_id: str, action: DecisionAction, previous_status: str, new_status: str, comments: str = None):
        """Records an incident lifecycle event in the audit trail."""
        audit_schema = AuditRecordCreate(
            incident_id=incident_id,
            recommendation_id="N/A",  # Bypass SQLite NOT NULL constraint for legacy records
            reviewer_id=user_id,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            comments=comments
        )
        return await self.audit_repository.create(db, obj_in=audit_schema)
