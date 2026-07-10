import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from features.evidence.repository import EvidenceRepository
from features.evidence.schemas import EvidenceCreate, EvidenceUpdate
from features.evidence.models import Evidence
from features.evidence.exceptions import InvalidEvidenceError, EvidenceNotFoundError

logger = logging.getLogger("crisispilot.evidence.service")

class EvidenceService:
    """Business logic and validation for Evidence."""
    
    def __init__(self, repository: EvidenceRepository):
        self.repository = repository

    def _validate_ownership(self, evidence_in: EvidenceCreate):
        if not any([evidence_in.operation_id, evidence_in.incident_id, evidence_in.mission_id, evidence_in.workflow_id]):
            logger.warning("Failed evidence creation: No ownership context provided.")
            raise InvalidEvidenceError("Evidence must belong to at least one entity (Operation, Incident, Mission, or Workflow).")

    async def create_evidence(self, db: AsyncSession, evidence_in: EvidenceCreate, submitted_by: str) -> Evidence:
        self._validate_ownership(evidence_in)
        
        evidence = await self.repository.create(db, evidence_in, submitted_by)
        logger.info(f"EvidenceService: Created evidence {evidence.id}")
        return evidence

    async def get_evidence(self, db: AsyncSession, evidence_id: str) -> Evidence:
        evidence = await self.repository.get(db, evidence_id)
        if not evidence:
            raise EvidenceNotFoundError(evidence_id)
        return evidence

    async def update_evidence(self, db: AsyncSession, evidence_id: str, update_data: EvidenceUpdate) -> Evidence:
        evidence = await self.repository.update(db, evidence_id, update_data)
        if not evidence:
            raise EvidenceNotFoundError(evidence_id)
        logger.info(f"EvidenceService: Updated evidence {evidence.id}")
        return evidence

    async def list_evidence_by_operation(self, db: AsyncSession, operation_id: str) -> List[Evidence]:
        return await self.repository.list_by_operation(db, operation_id)
        
    async def list_evidence_by_incident(self, db: AsyncSession, incident_id: str) -> List[Evidence]:
        return await self.repository.list_by_incident(db, incident_id)
        
    async def list_evidence_by_mission(self, db: AsyncSession, mission_id: str) -> List[Evidence]:
        return await self.repository.list_by_mission(db, mission_id)
        
    async def list_evidence_by_workflow(self, db: AsyncSession, workflow_id: str) -> List[Evidence]:
        return await self.repository.list_by_workflow(db, workflow_id)
