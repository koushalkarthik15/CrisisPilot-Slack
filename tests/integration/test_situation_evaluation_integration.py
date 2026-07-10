import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.notifications import NotificationEngine
from core.state import StateManager
from features.monitoring.domain import MonitoringCategory, SituationState, TargetType
from features.monitoring.schemas import MonitoringProfileCreate


@pytest.mark.asyncio
async def test_situation_evaluation_and_notification(db_session: AsyncSession, state_manager: StateManager):
    """
    Validates that processing scan results updates the situation state,
    triggers notifications, and generates recommendations if thresholds are crossed.
    """
    profile_in = MonitoringProfileCreate(
        name="Flood Watch",
        target_type=TargetType.REGION,
        region="Mumbai",
        monitoring_category=MonitoringCategory.FLOOD,
        channel_id="C_FLOOD",
        notification_targets="C_FLOOD",
        risk_threshold=7.5
    )

    profile = await state_manager.monitoring_service.create_monitoring_profile(
        db_session, state_manager, profile_in, created_by="U_AUTO"
    )

    assert profile.current_situation_state == SituationState.NORMAL
    assert profile.current_risk_score == 0.0

    # severity=5 → risk_score=5.0, which is below threshold 7.5 → NORMAL/WATCH
    observations_low = [
        {"type": "WEATHER", "severity": 5, "detail": "Light rain"}
    ]

    profile = await state_manager.monitoring_service.process_scan_results(
        db_session, state_manager, str(profile.id), observations_low
    )

    assert profile.current_risk_score > 0.0
    assert profile.current_risk_score < 7.5
    assert profile.current_situation_state in [SituationState.NORMAL, SituationState.WATCH]

    # Get the mock notification engine
    from core.services import registry
    notif_engine = registry.get(NotificationEngine)
    notifications_so_far = len(notif_engine.notifications_sent)

    # Simulate second scan (Crosses Threshold)
    observations_critical = [
        {"type": "WEATHER", "severity": 90, "detail": "Severe flooding expected"}
    ]

    profile = await state_manager.monitoring_service.process_scan_results(
        db_session, state_manager, str(profile.id), observations_critical
    )

    assert profile.current_risk_score >= 7.5

    # Verify Notification was sent
    assert len(notif_engine.notifications_sent) > notifications_so_far
    latest_notif = notif_engine.notifications_sent[-1]
    assert latest_notif["channel_id"] == "C_FLOOD"

    # Verify Timeline Event for Recommendation Generated
    events = await state_manager.timeline_service.repository.list_by_operation(db_session, str(profile.operation_id))
    rec_events = [e for e in events if e.event_type.value == "RECOMMENDATION_EVENT"]
    assert len(rec_events) == 1
    assert "Incident Recommendation Generated" in rec_events[0].description
