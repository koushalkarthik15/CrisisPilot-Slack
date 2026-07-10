import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import StateError
from features.incident_management import IncidentService, IncidentRepository, IncidentCreate, IncidentUpdate, IncidentStatus
from features.recommendations import RecommendationService, RecommendationRepository, RecommendationUpdateStatus
from features.recommendations.intelligence import IncidentIntelligenceService
from features.recommendations.router import RecommendationRouter
from features.workflow.domain import DecisionAction
from features.workflow import WorkflowService, AuditRepository, DecisionRequest
from features.operations import OperationService, OperationCreate, OperationUpdate, OperationStatus
from features.missions import MissionService, MissionCreate, MissionUpdate, MissionStatus, MissionAssignment
from features.workflows import (
    WorkflowService as OperationalWorkflowService,
    WorkflowCreate as OperationalWorkflowCreate,
    WorkflowUpdate as OperationalWorkflowUpdate,
    WorkflowStatus as OperationalWorkflowStatus
)
from features.timeline import TimelineService, TimelineEventCreate
from features.timeline.domain import TimelineEventType, TimelineEventSource, TimelineEventSeverity
from features.evidence import EvidenceService, EvidenceCreate, EvidenceUpdate
from features.monitoring.service import MonitoringService
from features.mission_execution import MissionExecutionEngine, MissionScheduler
from core.services import registry as service_registry
from core.notifications import NotificationEngine

logger = logging.getLogger("crisispilot.state")


class StateManager:
    """
    Central owner of application state.
    Coordinates between the Supervisor Agent, features, and the persistence layer.
    """
    def __init__(self):
        # In future sprints, repositories for agents, etc. will be injected here.
        self.incident_service = IncidentService(repository=IncidentRepository())
        
        intelligence_svc = service_registry.get(IncidentIntelligenceService)
        router = service_registry.get(RecommendationRouter)
        
        self.recommendation_service = RecommendationService(
            repository=RecommendationRepository(),
            intelligence_service=intelligence_svc,
            router=router
        )
        self._initialized = False

    async def initialize(self) -> None:
        """Bootstraps the State Manager resources."""
        logger.info("Initializing State Manager...")
        # Lazy inject WorkflowService so we can grab the NotificationEngine from registry
        notification_engine = service_registry.get(NotificationEngine)
        self.workflow_service = WorkflowService(
            audit_repository=AuditRepository(),
            recommendation_repository=self.recommendation_service.repository,
            notification_engine=notification_engine
        )
        self.operation_service = service_registry.get(OperationService)
        self.mission_service = service_registry.get(MissionService)
        self.operational_workflow_service = service_registry.get(OperationalWorkflowService)
        self.timeline_service = service_registry.get(TimelineService)
        self.evidence_service = service_registry.get(EvidenceService)
        self.monitoring_service = service_registry.get(MonitoringService)
        self.mission_engine = service_registry.get(MissionExecutionEngine)
        self.mission_scheduler = service_registry.get(MissionScheduler)
        self._initialized = True
        logger.info("State Manager operational.")

    async def shutdown(self) -> None:
        """Gracefully shuts down state management resources."""
        logger.info("Shutting down State Manager...")
        self._initialized = False

    async def get_active_incident_context(self, db: AsyncSession, channel_id: str) -> dict:
        """Foundation interface: Retrieves active operational context for a given channel."""
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        incident = await self.incident_service.get_active_incident(db, channel_id)
        if incident:
            return {
                "id": incident.id,
                "title": incident.title,
                "status": incident.status.value,
                "severity": incident.severity.value,
            }
        return {}

    async def create_incident(self, db: AsyncSession, incident_in: IncidentCreate):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.incident_service.create_incident(db, incident_in)

    async def update_incident(self, db: AsyncSession, incident_id: str, incident_in: IncidentUpdate):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.incident_service.update_incident(db, incident_id, incident_in)

    async def transition_incident_status(self, db: AsyncSession, incident_id: str, new_status: IncidentStatus, user_id: str, action: DecisionAction = None, comments: str = None):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        incident = await self.incident_service.get_incident(db, incident_id)
        if not incident:
            return None
        previous = incident.status.value
        updated = await self.incident_service.transition_status(db, incident_id, new_status)
        if action:
            await self.workflow_service.log_incident_action(db, incident_id, user_id, action, previous, new_status.value, comments)
        return updated
        
    async def resolve_incident(self, db: AsyncSession, incident_id: str, user_id: str, comments: str = None):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        incident = await self.incident_service.get_incident(db, incident_id)
        if incident and incident.status == IncidentStatus.RESOLVED:
            # If already resolved, auto-archive it instead of throwing transition error
            return await self.transition_incident_status(db, incident_id, IncidentStatus.ARCHIVED, user_id, DecisionAction.ARCHIVE_INCIDENT, comments="Auto-archived from resolve button")
            
        return await self.transition_incident_status(db, incident_id, IncidentStatus.RESOLVED, user_id, DecisionAction.RESOLVE_INCIDENT, comments=comments)

    async def archive_incident(self, db: AsyncSession, incident_id: str, user_id: str):
        return await self.transition_incident_status(db, incident_id, IncidentStatus.ARCHIVED, user_id, DecisionAction.ARCHIVE_INCIDENT)

    async def mark_incident_duplicate(self, db: AsyncSession, incident_id: str, parent_id: str, user_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        incident = await self.incident_service.get_incident(db, incident_id)
        if not incident:
            return None
        previous = incident.status.value
        updated = await self.incident_service.mark_duplicate(db, incident_id, parent_id)
        await self.workflow_service.log_incident_action(db, incident_id, user_id, DecisionAction.MARK_DUPLICATE, previous, IncidentStatus.DUPLICATE.value, f"Duplicate of {parent_id}")
        return updated

    async def assign_incident(self, db: AsyncSession, incident_id: str, user_id: str, assignee_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        incident = await self.incident_service.get_incident(db, incident_id)
        if not incident:
            return None
        updated = await self.incident_service.assign(db, incident_id, assignee_id)
        await self.workflow_service.log_incident_action(db, incident_id, user_id, DecisionAction.ASSIGN, incident.status.value, incident.status.value, f"Assigned to {assignee_id}")
        return updated
        
    async def update_incident_thread_ts(self, db: AsyncSession, incident_id: str, thread_ts: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.incident_service.update_thread_ts(db, incident_id, thread_ts)

    async def delete_incident(self, db: AsyncSession, incident_id: str, user_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        incident = await self.incident_service.get_incident(db, incident_id)
        if not incident:
            return False
        previous = incident.status.value
        await self.incident_service.delete(db, incident_id)
        await self.workflow_service.log_incident_action(db, incident_id, user_id, DecisionAction.DELETE_INCIDENT, previous, "Deleted")
        return True

    async def check_inventory(self, resource_type: str, location: str) -> dict:
        """
        Retrieves inventory levels from the persistence layer.
        (Mocked until the full database schema is implemented)
        """
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        
        return {
            "resource": resource_type,
            "location": location,
            "quantity": 500,
            "status": "Available"
        }

    async def generate_incident_recommendations(self, db: AsyncSession, incident_context: dict, mcp_outputs: list):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.recommendation_service.generate_recommendations(db, incident_context, mcp_outputs)

    async def get_recommendations_for_incident(self, db: AsyncSession, incident_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.recommendation_service.get_by_incident(db, incident_id)

    async def process_recommendation_decision(self, db: AsyncSession, request: DecisionRequest):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.workflow_service.apply_decision(db, request)

    # --- Operation Management ---

    async def create_operation(self, db: AsyncSession, operation_in: OperationCreate, user_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operation_service.create_operation(db, operation_in, user_id)

    async def get_operation(self, db: AsyncSession, operation_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operation_service.get_operation(db, operation_id)

    async def update_operation(self, db: AsyncSession, operation_id: str, operation_in: OperationUpdate):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operation_service.update_operation(db, operation_id, operation_in)

    async def list_active_operations(self, db: AsyncSession):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operation_service.list_active_operations(db)

    async def transition_operation_status(self, db: AsyncSession, operation_id: str, new_status: OperationStatus):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operation_service.transition_status(db, operation_id, new_status)

    async def associate_incident_to_operation(self, db: AsyncSession, incident_id: str, operation_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        incident = await self.incident_service.get_incident(db, incident_id)
        if not incident:
            return None
        return await self.operation_service.associate_incident(db, operation_id, incident)

    async def detach_incident_from_operation(self, db: AsyncSession, incident_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        incident = await self.incident_service.get_incident(db, incident_id)
        if not incident:
            return None
        return await self.operation_service.detach_incident(db, incident)

    # --- Mission Management ---

    async def create_mission(self, db: AsyncSession, mission_in: MissionCreate, user_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        mission = await self.mission_service.create_mission(db, mission_in, user_id)
        
        await self.create_timeline_event(db, TimelineEventCreate(
            event_type=TimelineEventType.LIFECYCLE_CHANGE,
            description=f"Mission '{mission.name}' created by user <@{user_id}>",
            source=TimelineEventSource.USER,
            severity=TimelineEventSeverity.INFO,
            mission_id=mission.id,
            operation_id=mission.operation_id
        ))
        
        return mission

    async def get_mission(self, db: AsyncSession, mission_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.mission_service.get_mission(db, mission_id)

    async def update_mission(self, db: AsyncSession, mission_id: str, mission_in: MissionUpdate):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.mission_service.update_mission(db, mission_id, mission_in)

    async def transition_mission_status(self, db: AsyncSession, mission_id: str, new_status: MissionStatus):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        mission = await self.mission_service.transition_status(db, mission_id, new_status)
        
        # Auto-resolve incident if mission completes
        if new_status in [MissionStatus.COMPLETED]:
            incidents = await self.incident_service.repository.get_by_mission_id(db, mission_id)
            for incident in incidents:
                if incident.status not in [IncidentStatus.RESOLVED, IncidentStatus.ARCHIVED]:
                    await self.resolve_incident(db, incident.id, user_id="system", comments=f"Auto-resolved due to Mission '{mission.name}' completion.")
        
        return mission

    async def assign_mission(self, db: AsyncSession, mission_id: str, assignment: MissionAssignment):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        mission = await self.mission_service.assign_mission(db, mission_id, assignment)
        
        assignees = []
        if assignment.assigned_human_ids:
            assignees.extend([f"<@{uid}>" for uid in assignment.assigned_human_ids])
        if assignment.assigned_mini_agent_id:
            assignees.append(f"🤖 {assignment.assigned_mini_agent_id}")
            
        desc = f"Mission assigned to: {', '.join(assignees)}" if assignees else "Mission unassigned"
        
        await self.create_timeline_event(db, TimelineEventCreate(
            event_type=TimelineEventType.HUMAN_ACTION,
            description=desc,
            source=TimelineEventSource.USER,
            severity=TimelineEventSeverity.INFO,
            mission_id=mission.id,
            operation_id=mission.operation_id
        ))
        
        return mission

    # --- Mission Execution Management ---
    
    async def execute_mission_manually(self, db: AsyncSession, mission_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.mission_scheduler.dispatch_manual(db, self, mission_id)
        
    async def run_mission_scheduler_tick(self, db: AsyncSession):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.mission_scheduler.run_tick(db, self)

    # --- Operational Workflow Management ---

    async def create_operational_workflow(self, db: AsyncSession, workflow_in: OperationalWorkflowCreate, user_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operational_workflow_service.create_workflow(db, workflow_in, user_id)

    async def get_operational_workflow(self, db: AsyncSession, workflow_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operational_workflow_service.get_workflow(db, workflow_id)

    async def update_operational_workflow(self, db: AsyncSession, workflow_id: str, workflow_in: OperationalWorkflowUpdate):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operational_workflow_service.update_workflow(db, workflow_id, workflow_in)

    async def transition_operational_workflow_status(self, db: AsyncSession, workflow_id: str, new_status: OperationalWorkflowStatus):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operational_workflow_service.transition_status(db, workflow_id, new_status)

    async def advance_operational_workflow_stage(self, db: AsyncSession, workflow_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.operational_workflow_service.advance_stage(db, workflow_id)

    # --- Timeline Management ---

    async def create_timeline_event(self, db: AsyncSession, event_in: TimelineEventCreate):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.timeline_service.create_event(db, event_in)
        
    async def get_timeline_event(self, db: AsyncSession, event_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.timeline_service.get_event(db, event_id)
        
    # --- Evidence Management ---

    async def create_evidence(self, db: AsyncSession, evidence_in: EvidenceCreate, user_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.evidence_service.create_evidence(db, evidence_in, user_id)
        
    async def get_evidence(self, db: AsyncSession, evidence_id: str):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.evidence_service.get_evidence(db, evidence_id)
        
    async def update_evidence(self, db: AsyncSession, evidence_id: str, update_data: EvidenceUpdate):
        if not self._initialized:
            raise StateError("State Manager is not initialized.")
        return await self.evidence_service.update_evidence(db, evidence_id, update_data)




