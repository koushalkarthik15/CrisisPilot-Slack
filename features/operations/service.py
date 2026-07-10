import logging
from datetime import datetime, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from features.incident_management.models import Incident
from features.operations.domain import OperationStatus
from features.operations.exceptions import (
    DuplicateOperationNameError,
    InvalidOperationStateTransitionError,
    OperationNotFoundError,
)
from features.operations.models import Operation
from features.operations.repository import OperationRepository
from features.operations.schemas import OperationCreate, OperationUpdate

logger = logging.getLogger("crisispilot.operations.service")

def utc_now():
    return datetime.now(timezone.utc)

class OperationService:
    """Business logic and lifecycle management for Operations."""

    ALLOWED_TRANSITIONS = {
        OperationStatus.PLANNED: [OperationStatus.ACTIVE, OperationStatus.PAUSED, OperationStatus.ARCHIVED],
        OperationStatus.ACTIVE: [OperationStatus.PAUSED, OperationStatus.COMPLETED, OperationStatus.ARCHIVED],
        OperationStatus.PAUSED: [OperationStatus.ACTIVE, OperationStatus.COMPLETED, OperationStatus.ARCHIVED],
        OperationStatus.COMPLETED: [OperationStatus.ARCHIVED],
        OperationStatus.ARCHIVED: []
    }

    def __init__(self, repository: OperationRepository):
        self.repository = repository

    async def create_operation(self, db: AsyncSession, operation_in: OperationCreate, created_by: str) -> Operation:
        # Enforce duplicate name check
        existing = await self.repository.get_by_name(db, operation_in.name)
        if existing and existing.status != OperationStatus.ARCHIVED:
            raise DuplicateOperationNameError(operation_in.name)

        operation = await self.repository.create(db, operation_in, created_by)
        logger.info(f"OperationService: Created operation {operation.id}")
        return operation

    async def get_operation(self, db: AsyncSession, operation_id: str) -> Operation:
        operation = await self.repository.get(db, operation_id)
        if not operation:
            raise OperationNotFoundError(operation_id)
        return operation

    async def list_active_operations(self, db: AsyncSession) -> List[Operation]:
        return await self.repository.list_active(db)

    async def update_operation(self, db: AsyncSession, operation_id: str, update_data: OperationUpdate) -> Operation:
        # Check duplicate name if updating name
        if update_data.name:
            existing = await self.repository.get_by_name(db, update_data.name)
            if existing and existing.id != operation_id and existing.status != OperationStatus.ARCHIVED:
                raise DuplicateOperationNameError(update_data.name)

        operation = await self.repository.update(db, operation_id, update_data)
        if not operation:
            raise OperationNotFoundError(operation_id)
        logger.info(f"OperationService: Updated operation {operation_id}")
        return operation

    async def transition_status(self, db: AsyncSession, operation_id: str, new_status: OperationStatus) -> Operation:
        operation = await self.get_operation(db, operation_id)
        current_status = operation.status

        if new_status not in self.ALLOWED_TRANSITIONS.get(current_status, []):
            logger.warning(f"OperationService: Failed transition for {operation_id}: {current_status.value} -> {new_status.value}")
            raise InvalidOperationStateTransitionError(current_status.value, new_status.value)

        kwargs = {}
        if new_status == OperationStatus.ACTIVE and current_status == OperationStatus.PLANNED:
            kwargs["started_at"] = utc_now()
        elif new_status == OperationStatus.COMPLETED:
            kwargs["completed_at"] = utc_now()

        updated = await self.repository.update_status(db, operation_id, new_status, **kwargs)
        logger.info(f"OperationService: Transitioned {operation_id} to {new_status.value}")
        return updated

    async def associate_incident(self, db: AsyncSession, operation_id: str, incident: Incident) -> Incident:
        operation = await self.get_operation(db, operation_id)

        # Validations: cannot associate to archived operation
        if operation.status == OperationStatus.ARCHIVED:
            raise InvalidOperationStateTransitionError("ARCHIVED", "ASSOCIATE_INCIDENT")

        incident.operation_id = operation.id
        await db.flush()
        logger.info(f"OperationService: Associated incident {incident.id} with operation {operation_id}")
        return incident

    async def detach_incident(self, db: AsyncSession, incident: Incident) -> Incident:
        if incident.operation_id:
            logger.info(f"OperationService: Detached incident {incident.id} from operation {incident.operation_id}")
            incident.operation_id = None
            await db.flush()
        return incident
