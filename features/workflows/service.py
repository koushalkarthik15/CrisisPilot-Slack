import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from features.workflows.domain import WorkflowStatus
from features.workflows.exceptions import (
    InvalidWorkflowOwnershipError,
    InvalidWorkflowStateTransitionError,
    WorkflowNotFoundError,
    WorkflowStageProgressionError,
)
from features.workflows.models import Workflow
from features.workflows.repository import WorkflowRepository
from features.workflows.schemas import WorkflowCreate, WorkflowUpdate

logger = logging.getLogger("crisispilot.workflows.service")

def utc_now():
    return datetime.now(timezone.utc)

class WorkflowService:
    """Business logic and lifecycle management for Workflows."""

    ALLOWED_TRANSITIONS = {
        WorkflowStatus.DRAFT: [WorkflowStatus.ACTIVE, WorkflowStatus.ARCHIVED],
        WorkflowStatus.ACTIVE: [WorkflowStatus.PAUSED, WorkflowStatus.COMPLETED, WorkflowStatus.ARCHIVED],
        WorkflowStatus.PAUSED: [WorkflowStatus.ACTIVE, WorkflowStatus.COMPLETED, WorkflowStatus.ARCHIVED],
        WorkflowStatus.COMPLETED: [WorkflowStatus.ARCHIVED],
        WorkflowStatus.ARCHIVED: []
    }

    def __init__(self, repository: WorkflowRepository):
        self.repository = repository

    def _validate_ownership(self, operation_id: Optional[str], incident_id: Optional[str]):
        if not operation_id and not incident_id:
            raise InvalidWorkflowOwnershipError()

    async def create_workflow(self, db: AsyncSession, workflow_in: WorkflowCreate, created_by: str) -> Workflow:
        self._validate_ownership(workflow_in.operation_id, workflow_in.incident_id)

        if not workflow_in.stages:
            raise WorkflowStageProgressionError("A workflow must have at least one stage defined.")

        workflow = await self.repository.create(db, workflow_in, created_by)
        logger.info(f"WorkflowService: Created workflow {workflow.id}")
        return workflow

    async def get_workflow(self, db: AsyncSession, workflow_id: str) -> Workflow:
        workflow = await self.repository.get(db, workflow_id)
        if not workflow:
            raise WorkflowNotFoundError(workflow_id)
        return workflow

    async def update_workflow(self, db: AsyncSession, workflow_id: str, update_data: WorkflowUpdate) -> Workflow:
        workflow = await self.repository.update(db, workflow_id, update_data)
        if not workflow:
            raise WorkflowNotFoundError(workflow_id)
        logger.info(f"WorkflowService: Updated workflow {workflow_id}")
        return workflow

    async def transition_status(self, db: AsyncSession, workflow_id: str, new_status: WorkflowStatus) -> Workflow:
        workflow = await self.get_workflow(db, workflow_id)
        current_status = workflow.status

        if new_status not in self.ALLOWED_TRANSITIONS.get(current_status, []):
            logger.warning(f"WorkflowService: Failed transition for {workflow_id}: {current_status.value} -> {new_status.value}")
            raise InvalidWorkflowStateTransitionError(current_status.value, new_status.value)

        kwargs = {}
        if new_status == WorkflowStatus.ACTIVE and not workflow.started_at:
            kwargs["started_at"] = utc_now()
        elif new_status == WorkflowStatus.COMPLETED:
            kwargs["completed_at"] = utc_now()

        updated = await self.repository.update_status(db, workflow_id, new_status, **kwargs)
        logger.info(f"WorkflowService: Transitioned {workflow_id} to {new_status.value}")
        return updated

    async def advance_stage(self, db: AsyncSession, workflow_id: str) -> Workflow:
        """Advances the workflow to the next stage."""
        workflow = await self.get_workflow(db, workflow_id)

        if workflow.status == WorkflowStatus.ARCHIVED:
            raise WorkflowStageProgressionError("Cannot advance an archived workflow.")

        if workflow.status == WorkflowStatus.PAUSED:
            raise WorkflowStageProgressionError("Cannot advance a paused workflow.")

        if workflow.status == WorkflowStatus.COMPLETED:
            return workflow

        if workflow.status != WorkflowStatus.ACTIVE:
            raise WorkflowStageProgressionError(f"Workflow must be ACTIVE to advance stages, currently {workflow.status.value}.")

        total_stages = len(workflow.stages)
        current_index = workflow.current_stage_index

        if current_index >= total_stages - 1:
            return await self.transition_status(db, workflow_id, WorkflowStatus.COMPLETED)

        # Move to next stage strictly
        new_index = current_index + 1

        updated = await self.repository.advance_stage(db, workflow_id, new_index)
        logger.info(f"WorkflowService: Advanced workflow {workflow_id} to stage {new_index} ({workflow.stages[new_index]})")
        return updated
