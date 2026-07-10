import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from core.state import StateManager
from features.operations.schemas import OperationCreate
from features.missions.schemas import MissionCreate, MissionUpdate
from features.missions.domain import MissionStatus, MissionAssignment

@pytest.mark.asyncio
async def test_mission_lifecycle_integration(db_session: AsyncSession, state_manager: StateManager):
    """
    Validates the interaction between Missions, Evidence, and the Timeline.
    """
    op_create = OperationCreate(name="Mission Op", description="Test Op")
    operation = await state_manager.create_operation(db_session, op_create, user_id="U1")
    
    mission_create = MissionCreate(
        operation_id=operation.id,
        name="Test Mission",
        objective="Verify integration",
        strategy="SCHEDULED"
    )
    mission = await state_manager.create_mission(db_session, mission_create, user_id="U1")
    
    # Mission created -> Timeline event should be recorded
    events = await state_manager.timeline_service.repository.get_by_operation(db_session, operation.id)
    assert len(events) >= 1
    assert any("Mission 'Test Mission' created" in e.description for e in events)
    
    # Assign Mission
    assignment = MissionAssignment(assigned_human_ids=["U2"])
    mission = await state_manager.assign_mission(db_session, mission.id, assignment)
    
    events = await state_manager.timeline_service.repository.get_by_operation(db_session, operation.id)
    assert any("Mission assigned to: <@U2>" in e.description for e in events)
    
    # Transition Status
    mission = await state_manager.transition_mission_status(db_session, mission.id, MissionStatus.ACTIVE)
    assert mission.status == MissionStatus.ACTIVE
    
    # Finally, complete the mission
    mission = await state_manager.transition_mission_status(db_session, mission.id, MissionStatus.COMPLETED)
    assert mission.status == MissionStatus.COMPLETED
