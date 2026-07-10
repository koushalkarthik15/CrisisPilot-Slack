import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from core.state import StateManager
from core.notifications import NotificationEngine
from features.monitoring.schemas import MonitoringProfileCreate
from features.monitoring.domain import MonitoringCategory, TargetType, MonitoringStatus, SituationState
from features.incident_management.schemas import IncidentCreate, IncidentUpdate
from features.incident_management.domain import IncidentStatus
from features.timeline.domain import TimelineEventType

@pytest.mark.asyncio
async def test_e2e_operational_workflow(db_session: AsyncSession, state_manager: StateManager):
    """
    Validates the complete end-to-end operational lifecycle:
    Monitoring -> Escalation -> Notification -> Recommendation -> Incident Creation -> Resolution -> Continued Monitoring
    """
    # 1. Monitoring Initialization
    profile_in = MonitoringProfileCreate(
        name="E2E Hurricane Watch",
        target_type=TargetType.REGION,
        region="Florida Coast",
        monitoring_category=MonitoringCategory.NATURAL_DISASTER,
        channel_id="C_HURRICANE",
        risk_threshold=8.0
    )
    
    profile = await state_manager.monitoring_service.create_monitoring_profile(
        db_session, state_manager, profile_in, created_by="U_AUTO"
    )
    
    assert profile.status == MonitoringStatus.ACTIVE
    assert profile.operation_id is not None
    
    op_id = profile.operation_id
    operation = await state_manager.get_operation(db_session, op_id)
    assert operation is not None
    
    # 2. First Scan (Normal)
    obs_normal = [{"type": "WEATHER", "severity": "LOW", "detail": "Clear skies"}]
    profile = await state_manager.monitoring_service.process_scan_results(
        db_session, state_manager, profile.id, obs_normal
    )
    
    assert profile.current_situation_state == SituationState.NORMAL
    
    # 3. Situation Escalation & Notification
    obs_critical = [{"type": "WEATHER", "severity": "CRITICAL", "detail": "Category 4 Hurricane forming"}]
    profile = await state_manager.monitoring_service.process_scan_results(
        db_session, state_manager, profile.id, obs_critical
    )
    
    assert profile.current_risk_score >= 8.0
    assert profile.current_situation_state in [SituationState.CRITICAL, SituationState.WARNING]
    
    # Verify Notification & Recommendation
    notif_engine = state_manager.workflow_service.notification_engine
    assert len(notif_engine.notifications_sent) > 0
    assert notif_engine.notifications_sent[-1]["channel_id"] == "C_HURRICANE"
    
    # Check Timeline for Recommendation
    events = await state_manager.timeline_service.repository.get_by_operation(db_session, op_id)
    assert any("Incident Recommendation Generated" in e.description for e in events)
    
    # 4. Human Action: Create Incident
    incident_in = IncidentCreate(
        title="Hurricane Bravo Impact",
        description="Hurricane approaching coast.",
        channel_id="C_INCIDENT_123",
        operation_id=op_id
    )
    incident = await state_manager.create_incident(db_session, incident_in)
    
    # Associate Incident with Operation
    await state_manager.associate_incident_to_operation(db_session, incident.id, op_id)
    
    # 5. Incident Resolution
    # We resolve it via the state manager
    resolved_incident = await state_manager.resolve_incident(
        db_session, incident.id, user_id="U_OPERATOR", comments="Hurricane passed, recovery complete."
    )
    
    assert resolved_incident.status == IncidentStatus.RESOLVED
    
    # 6. Verify Continued Monitoring
    # The monitoring profile should still be ACTIVE
    profile = await state_manager.monitoring_service.get_profile(db_session, profile.id)
    assert profile.status == MonitoringStatus.ACTIVE
    
    # Run another scan after incident resolution (Risk drops)
    obs_safe = [{"type": "WEATHER", "severity": "LOW", "detail": "Weather cleared"}]
    profile = await state_manager.monitoring_service.process_scan_results(
        db_session, state_manager, profile.id, obs_safe
    )
    
    # Risk score should have dropped, profile is still active
    assert profile.current_risk_score < 8.0
    assert profile.status == MonitoringStatus.ACTIVE
    
    # 7. Timeline Verification
    # Assert timeline captured the full history
    final_events = await state_manager.timeline_service.repository.get_by_operation(db_session, op_id)
    event_types = [e.event_type for e in final_events]
    
    assert TimelineEventType.LIFECYCLE_CHANGE in event_types  # Creation
    assert TimelineEventType.RECOMMENDATION_EVENT in event_types  # Critical Escalation
    
    # We also check that the operation is intact
    operation = await state_manager.get_operation(db_session, op_id)
    assert operation.name == "Monitoring: E2E Hurricane Watch"
