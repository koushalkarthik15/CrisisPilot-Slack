import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from features.workflows.domain import WorkflowStatus
from features.workflows.models import Workflow
from features.workflows.schemas import WorkflowCreate, WorkflowUpdate

logger = logging.getLogger("crisispilot.workflows.repository")

class WorkflowRepository:
    """Persistence layer for Workflows."""

    async def create(self, db: AsyncSession, workflow_in: WorkflowCreate, created_by: str) -> Workflow:
        workflow = Workflow(
            name=workflow_in.name,
            description=workflow_in.description,
            category=workflow_in.category,
            priority=workflow_in.priority,
            stages=[stage.value for stage in workflow_in.stages],
            current_stage_index=0,
            operation_id=workflow_in.operation_id,
            incident_id=workflow_in.incident_id,
            created_by=created_by,
            status=WorkflowStatus.DRAFT
        )
        db.add(workflow)
        await db.flush()
        await db.refresh(workflow)
        logger.info(f"Created workflow {workflow.id} ({workflow.name})")
        return workflow

    async def get(self, db: AsyncSession, workflow_id: str) -> Optional[Workflow]:
        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
        return result.scalars().first()

    async def list_by_operation(self, db: AsyncSession, operation_id: str) -> List[Workflow]:
        result = await db.execute(
            select(Workflow).where(Workflow.operation_id == operation_id)
            .order_by(Workflow.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_incident(self, db: AsyncSession, incident_id: str) -> List[Workflow]:
        result = await db.execute(
            select(Workflow).where(Workflow.incident_id == incident_id)
            .order_by(Workflow.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, workflow_id: str, update_data: WorkflowUpdate) -> Optional[Workflow]:
        workflow = await self.get(db, workflow_id)
        if not workflow:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return workflow

        for key, value in update_dict.items():
            setattr(workflow, key, value)

        await db.flush()
        await db.refresh(workflow)
        logger.info(f"Updated workflow {workflow_id}")
        return workflow

    async def update_status(self, db: AsyncSession, workflow_id: str, new_status: WorkflowStatus, **kwargs) -> Optional[Workflow]:
        workflow = await self.get(db, workflow_id)
        if not workflow:
            return None

        workflow.status = new_status
        for key, value in kwargs.items():
            setattr(workflow, key, value)

        await db.flush()
        await db.refresh(workflow)
        logger.info(f"Updated status for workflow {workflow_id} to {new_status}")
        return workflow

    async def advance_stage(self, db: AsyncSession, workflow_id: str, new_index: int) -> Optional[Workflow]:
        workflow = await self.get(db, workflow_id)
        if not workflow:
            return None

        workflow.current_stage_index = new_index
        await db.flush()
        await db.refresh(workflow)
        logger.info(f"Advanced workflow {workflow_id} to stage index {new_index}")
        return workflow
