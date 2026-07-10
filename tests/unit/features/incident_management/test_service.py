import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from features.incident_management.service import IncidentService
from features.incident_management.repository import IncidentRepository
from features.incident_management.schemas import IncidentCreate
from features.incident_management.domain import IncidentStatus, IncidentSeverity
from features.incident_management.exceptions import InvalidStateTransitionError, IncidentNotFoundError

@pytest.fixture
def repo():
    return IncidentRepository()

@pytest.fixture
def service(repo):
    return IncidentService(repository=repo)

@pytest.mark.asyncio
async def test_create_incident(db_session: AsyncSession, service: IncidentService):
    incident_in = IncidentCreate(
        title="Service Test",
        description="Testing service create",
        channel_id="C_SVC_1",
        severity=IncidentSeverity.MEDIUM
    )
    incident = await service.create_incident(db_session, incident_in)
    
    assert incident.id is not None
    assert incident.status == IncidentStatus.DRAFT

@pytest.mark.asyncio
async def test_transition_status(db_session: AsyncSession, service: IncidentService):
    incident_in = IncidentCreate(title="Trans", description="Desc", channel_id="C1")
    incident = await service.create_incident(db_session, incident_in)
    
    # Valid transition DRAFT -> ACTIVE
    updated = await service.transition_status(db_session, incident.id, IncidentStatus.ACTIVE)
    assert updated.status == IncidentStatus.ACTIVE

@pytest.mark.asyncio
async def test_invalid_transition(db_session: AsyncSession, service: IncidentService):
    incident_in = IncidentCreate(title="Invalid Trans", description="Desc", channel_id="C2")
    incident = await service.create_incident(db_session, incident_in)
    
    # Valid transition DRAFT -> ARCHIVED
    await service.transition_status(db_session, incident.id, IncidentStatus.ARCHIVED)
    
    # Invalid transition ARCHIVED -> ACTIVE
    with pytest.raises(InvalidStateTransitionError):
        await service.transition_status(db_session, incident.id, IncidentStatus.ACTIVE)

@pytest.mark.asyncio
async def test_mark_duplicate(db_session: AsyncSession, service: IncidentService):
    parent = await service.create_incident(db_session, IncidentCreate(title="Parent", description="P", channel_id="C3"))
    duplicate = await service.create_incident(db_session, IncidentCreate(title="Dup", description="D", channel_id="C3"))
    
    updated_dup = await service.mark_duplicate(db_session, duplicate.id, parent.id)
    assert updated_dup.status == IncidentStatus.DUPLICATE
    assert updated_dup.parent_id == parent.id

@pytest.mark.asyncio
async def test_assign(db_session: AsyncSession, service: IncidentService):
    incident = await service.create_incident(db_session, IncidentCreate(title="Assign", description="A", channel_id="C4"))
    assigned = await service.assign(db_session, incident.id, "U12345")
    assert assigned.assigned_user_id == "U12345"
