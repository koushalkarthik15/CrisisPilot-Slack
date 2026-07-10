import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from features.operations.models import Operation
from features.operations.schemas import OperationCreate, OperationUpdate
from features.operations.domain import OperationStatus

logger = logging.getLogger("crisispilot.operations.repository")

class OperationRepository:
    """Persistence layer for Operations."""
    
    async def create(self, db: AsyncSession, operation_in: OperationCreate, created_by: str) -> Operation:
        operation = Operation(
            name=operation_in.name,
            description=operation_in.description,
            category=operation_in.category,
            priority=operation_in.priority,
            created_by=created_by,
            status=OperationStatus.PLANNED
        )
        db.add(operation)
        await db.flush()
        await db.refresh(operation)
        logger.info(f"Created operation {operation.id} ({operation.name})")
        return operation

    async def get(self, db: AsyncSession, operation_id: str) -> Optional[Operation]:
        result = await db.execute(select(Operation).where(Operation.id == operation_id))
        return result.scalars().first()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Operation]:
        result = await db.execute(select(Operation).where(Operation.name == name))
        return result.scalars().first()

    async def list_active(self, db: AsyncSession) -> List[Operation]:
        result = await db.execute(
            select(Operation).where(Operation.status.in_([OperationStatus.PLANNED, OperationStatus.ACTIVE, OperationStatus.PAUSED]))
            .order_by(Operation.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, operation_id: str, update_data: OperationUpdate) -> Optional[Operation]:
        operation = await self.get(db, operation_id)
        if not operation:
            return None
            
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return operation
            
        for key, value in update_dict.items():
            setattr(operation, key, value)
            
        await db.flush()
        await db.refresh(operation)
        logger.info(f"Updated operation {operation_id}")
        return operation

    async def update_status(self, db: AsyncSession, operation_id: str, new_status: OperationStatus, **kwargs) -> Optional[Operation]:
        operation = await self.get(db, operation_id)
        if not operation:
            return None
            
        operation.status = new_status
        for key, value in kwargs.items():
            setattr(operation, key, value)
            
        await db.flush()
        await db.refresh(operation)
        logger.info(f"Updated status for operation {operation_id} to {new_status}")
        return operation
