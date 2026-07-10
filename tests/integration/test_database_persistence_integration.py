import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.state import StateManager
from features.evidence.schemas import EvidenceCreate
from features.missions.schemas import MissionCreate
from features.monitoring.domain import MonitoringCategory, TargetType
from features.monitoring.schemas import MonitoringProfileCreate
from features.operations.schemas import OperationCreate
from features.timeline.domain import (
    TimelineEventSeverity,
    TimelineEventSource,
    TimelineEventType,
)
from features.timeline.schemas import TimelineEventCreate


@pytest.mark.asyncio
async def test_database_persistence_integration(db_session: AsyncSession, state_manager: StateManager):
    """
    Verifies entities created across the operational flow are correctly persisted 
    and retrieved through the repository layer.
    """

    # 1. Create Operation
    op_create = OperationCreate(name="Test Op", description="Integration Test Operation")
    operation = await state_manager.create_operation(db_session, op_create, user_id="U123")
    assert operation.id is not None

    # Verify retrieval
    retrieved_op = await state_manager.get_operation(db_session, operation.id)
    assert retrieved_op.name == "Test Op"

    # 2. Create Monitoring Profile
    mon_create = MonitoringProfileCreate(
        name="Test Profile",
        target_type=TargetType.REGION,
        region="Test Region",
        monitoring_category=MonitoringCategory.FLOOD,
        channel_id="C123",
        risk_threshold=7.0
    )
    profile = await state_manager.monitoring_service.repository.create(db_session, mon_create, "U123")
    assert profile.id is not None

    # Verify retrieval
    retrieved_profile = await state_manager.monitoring_service.get_profile(db_session, profile.id)
    assert retrieved_profile.name == "Test Profile"

    # 3. Create Mission
    mission_create = MissionCreate(
        operation_id=operation.id,
        name="Test Mission",
        objective="Gather intel",
        strategy="SCHEDULED"
    )
    mission = await state_manager.create_mission(db_session, mission_create, user_id="U123")
    assert mission.id is not None
    assert mission.operation_id == operation.id

    # Verify retrieval
    retrieved_mission = await state_manager.get_mission(db_session, mission.id)
    assert retrieved_mission.name == "Test Mission"

    # 4. Create Timeline Event
    event_create = TimelineEventCreate(
        event_type=TimelineEventType.EVIDENCE_COLLECTED,
        source=TimelineEventSource.USER,
        severity=TimelineEventSeverity.INFO,
        description="Found some intel",
        operation_id=operation.id
    )
    event = await state_manager.create_timeline_event(db_session, event_create)
    assert event.id is not None
    assert event.operation_id == operation.id

    # Verify retrieval
    retrieved_event = await state_manager.get_timeline_event(db_session, event.id)
    assert retrieved_event.description == "Found some intel"

    # 5. Create Evidence
    ev_create = EvidenceCreate(
        operation_id=operation.id,
        description="Screenshot of weather map",
        source="Weather API"
    )
    evidence = await state_manager.create_evidence(db_session, ev_create, user_id="U123")
    assert evidence.id is not None
    assert evidence.operation_id == operation.id

    # Verify retrieval
    retrieved_evidence = await state_manager.get_evidence(db_session, evidence.id)
    assert retrieved_evidence.description == "Screenshot of weather map"
