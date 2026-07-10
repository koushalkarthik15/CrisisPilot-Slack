from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from shared.repository import BaseRepository
from features.workflow.models import AuditRecord
from features.workflow.schemas import AuditRecordCreate

# Note: Audit records are immutable, so we don't have an Update schema
class AuditRecordUpdateDummy:
    pass

class AuditRepository(BaseRepository[AuditRecord, AuditRecordCreate, AuditRecordUpdateDummy]):
    def __init__(self):
        super().__init__(AuditRecord)

    async def get_by_recommendation_id(self, db: AsyncSession, recommendation_id: str) -> List[AuditRecord]:
        """Fetches the complete immutable history of a recommendation."""
        result = await db.execute(
            select(self.model)
            .filter(self.model.recommendation_id == recommendation_id)
            .order_by(self.model.timestamp.asc())
        )
        return list(result.scalars().all())
