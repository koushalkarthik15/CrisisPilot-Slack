import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from features.incident_management.domain import IncidentSeverity, IncidentStatus
from features.incident_management.repository import IncidentRepository
from features.incident_management.schemas import IncidentCreate, IncidentUpdate


@pytest.fixture
def repo():
    return IncidentRepository()

@pytest.mark.asyncio
async def test_create_incident(db_session: AsyncSession, repo: IncidentRepository):
    incident_in = IncidentCreate(
        title="Test Incident",
        description="A test incident",
        channel_id="C12345",
        severity=IncidentSeverity.HIGH
    )
    incident = await repo.create(db_session, incident_in)

    assert incident.id is not None
    assert incident.title == "Test Incident"
    assert incident.channel_id == "C12345"
    assert incident.status == IncidentStatus.DRAFT

@pytest.mark.asyncio
async def test_get_active_by_channel(db_session: AsyncSession, repo: IncidentRepository):
    # Create an active incident
    incident_in = IncidentCreate(
        title="Active Incident",
        description="Active",
        channel_id="C999",
        status=IncidentStatus.ACTIVE
    )
    await repo.create(db_session, incident_in)

    # Create an archived incident
    archived_in = IncidentCreate(
        title="Archived",
        description="Archived",
        channel_id="C999",
        status=IncidentStatus.ARCHIVED
    )
    await repo.create(db_session, archived_in)

    active = await repo.get_active_by_channel(db_session, "C999")
    assert active is not None
    assert active.title == "Active Incident"
    assert active.status == IncidentStatus.ACTIVE

@pytest.mark.asyncio
async def test_update_incident(db_session: AsyncSession, repo: IncidentRepository):
    incident_in = IncidentCreate(
        title="Old Title",
        description="Old Description",
        channel_id="C12345"
    )
    incident = await repo.create(db_session, incident_in)

    update_in = IncidentUpdate(title="New Title")
    updated = await repo.update(db_session, incident, update_in)

    assert updated.title == "New Title"
    assert updated.description == "Old Description"
