import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from core.state import StateManager
from features.monitoring.schemas import MonitoringProfileCreate
from features.monitoring.domain import MonitoringCategory, TargetType

@pytest.mark.asyncio
async def test_monitoring_provisioning_flow(db_session: AsyncSession, state_manager: StateManager):
    """
    Validates that creating a Monitoring Profile automatically provisions
    the necessary Operation, Workflow, Missions, and Timeline Events.
    """
    # Create the Monitoring Profile
    profile_in = MonitoringProfileCreate(
        name="Global Cyber Watch",
        target_type=TargetType.GLOBAL,
        monitoring_category=MonitoringCategory.CYBERSECURITY,
        channel_id="C_CYBER",
        risk_threshold=8.5
    )
    
    profile = await state_manager.monitoring_service.create_monitoring_profile(
        db_session, state_manager, profile_in, created_by="U_AUTO"
    )
    
    assert profile.id is not None
    assert profile.operation_id is not None
    
    # Verify Operation was provisioned
    operation = await state_manager.get_operation(db_session, profile.operation_id)
    assert operation is not None
    assert "Monitoring:" in operation.name
    
    # Verify Operational Workflow was provisioned
    workflows = await state_manager.operational_workflow_service.repository.get_by_operation_id(db_session, operation.id)
    assert len(workflows) == 1
    assert workflows[0].name == "CYBERSECURITY_RESPONSE_WORKFLOW"
    
    # Verify Missions were provisioned based on category
    missions = await state_manager.mission_service.repository.get_by_operation_id(db_session, operation.id)
    assert len(missions) > 0
    mission_names = [m.name for m in missions]
    assert any("Threat Intel" in name for name in mission_names)
    
    # Verify Timeline Event was logged
    events = await state_manager.timeline_service.repository.get_by_operation(db_session, operation.id)
    # 1 for operation creation/provisioning + missions created
    assert len(events) >= 1
    lifecycle_events = [e for e in events if "Monitoring Profile 'Global Cyber Watch' started" in e.description]
    assert len(lifecycle_events) == 1
