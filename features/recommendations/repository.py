from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from features.recommendations.models import Recommendation
from features.recommendations.schemas import (
    RecommendationCreate,
    RecommendationUpdateStatus,
)
from shared.repository import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation, RecommendationCreate, RecommendationUpdateStatus]):
    def __init__(self):
        super().__init__(Recommendation)

    async def get_by_incident_id(self, db: AsyncSession, incident_id: str) -> List[Recommendation]:
        """Fetches all recommendations associated with a specific incident."""
        result = await db.execute(
            select(self.model)
            .filter(self.model.incident_id == incident_id)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_operation_id(self, db: AsyncSession, operation_id: str) -> List[Recommendation]:
        """Fetches all recommendations associated with a specific operation."""
        result = await db.execute(
            select(self.model)
            .filter(self.model.operation_id == operation_id)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_entities(self, db: AsyncSession):
        """Fetches distinct incident and operation IDs that have pending recommendations."""
        from sqlalchemy import String, cast

        from features.recommendations.domain import RecommendationStatus

        result = await db.execute(
            select(
                self.model.incident_id,
                self.model.operation_id
            ).filter(cast(self.model.status, String).in_([RecommendationStatus.PENDING_APPROVAL.name, "Pending Approval", "PENDING_REVIEW"]))
        )

        incident_ids = set()
        operation_ids = set()

        for row in result:
            if row[0]:
                incident_ids.add(row[0])
            elif row[1]:
                operation_ids.add(row[1])

        return list(incident_ids), list(operation_ids)

    async def get_orphaned_pending(self, db: AsyncSession):
        from sqlalchemy import String, cast

        from features.recommendations.domain import RecommendationStatus
        result = await db.execute(
            select(self.model)
            .filter(cast(self.model.status, String).in_([RecommendationStatus.PENDING_APPROVAL.name, "Pending Approval", "PENDING_REVIEW"]))
            .filter(self.model.incident_id.is_(None))
            .filter(self.model.operation_id.is_(None))
        )
        return list(result.scalars().all())

    async def get_all_pending(self, db: AsyncSession):
        from sqlalchemy import String, cast

        from features.recommendations.domain import RecommendationStatus
        result = await db.execute(
            select(self.model)
            .filter(cast(self.model.status, String).in_([RecommendationStatus.PENDING_APPROVAL.name, "Pending Approval", "PENDING_REVIEW"]))
        )
        return list(result.scalars().all())

