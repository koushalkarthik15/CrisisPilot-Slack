import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from features.evidence.models import Evidence
from features.evidence.schemas import EvidenceCreate, EvidenceUpdate

logger = logging.getLogger("crisispilot.evidence.repository")

class EvidenceRepository:
    """Persistence layer for Evidence."""
    
    async def create(self, db: AsyncSession, evidence_in: EvidenceCreate, submitted_by: str) -> Evidence:
        evidence = Evidence(
            title=evidence_in.title,
            description=evidence_in.description,
            source=evidence_in.source,
            evidence_type=evidence_in.evidence_type,
            content=evidence_in.content,
            confidence_score=evidence_in.confidence_score,
            collected_at=evidence_in.collected_at,
            evidence_metadata=evidence_in.evidence_metadata,
            operation_id=evidence_in.operation_id,
            incident_id=evidence_in.incident_id,
            mission_id=evidence_in.mission_id,
            workflow_id=evidence_in.workflow_id,
            submitted_by=submitted_by
        )
        db.add(evidence)
        await db.flush()
        await db.refresh(evidence)
        logger.info(f"Created evidence {evidence.id}")
        return evidence

    async def get(self, db: AsyncSession, evidence_id: str) -> Optional[Evidence]:
        result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
        return result.scalars().first()

    async def update(self, db: AsyncSession, evidence_id: str, update_data: EvidenceUpdate) -> Optional[Evidence]:
        evidence = await self.get(db, evidence_id)
        if not evidence:
            return None
            
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return evidence
            
        for key, value in update_dict.items():
            setattr(evidence, key, value)
            
        await db.flush()
        await db.refresh(evidence)
        logger.info(f"Updated evidence {evidence.id}")
        return evidence

    async def list_by_operation(self, db: AsyncSession, operation_id: str) -> List[Evidence]:
        result = await db.execute(
            select(Evidence).where(Evidence.operation_id == operation_id)
            .order_by(Evidence.created_at.desc())
        )
        return list(result.scalars().all())
        
    async def list_by_incident(self, db: AsyncSession, incident_id: str) -> List[Evidence]:
        result = await db.execute(
            select(Evidence).where(Evidence.incident_id == incident_id)
            .order_by(Evidence.created_at.desc())
        )
        return list(result.scalars().all())
        
    async def list_by_mission(self, db: AsyncSession, mission_id: str) -> List[Evidence]:
        result = await db.execute(
            select(Evidence).where(Evidence.mission_id == mission_id)
            .order_by(Evidence.created_at.desc())
        )
        return list(result.scalars().all())
        
    async def list_by_workflow(self, db: AsyncSession, workflow_id: str) -> List[Evidence]:
        result = await db.execute(
            select(Evidence).where(Evidence.workflow_id == workflow_id)
            .order_by(Evidence.created_at.desc())
        )
        return list(result.scalars().all())
