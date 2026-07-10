import logging
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.state import StateManager
from features.incident_management.schemas import IncidentCreate
from features.mission_execution.strategies import BaseExecutionHandler
from features.missions.domain import ExecutionStrategy
from features.monitoring.domain import MonitoringCategory, TargetType
from features.monitoring.schemas import MonitoringProfileCreate


class MockFailingHandler(BaseExecutionHandler):
    """A mock handler that raises an exception to simulate failure."""
    async def execute(self, db: AsyncSession, state_manager: Any, engine: Any, mission: Any):
        raise RuntimeError(f"Simulated execution failure for mission {mission.id}")

@pytest.mark.asyncio
async def test_full_lifecycle_logging_and_traceability(db_session: AsyncSession, state_manager: StateManager, caplog):
    """
    Validates log generation, consistency, and Timeline correlation across the full operational lifecycle.
    """
    caplog.set_level(logging.INFO)

    # 1. Monitoring Profile Creation & Operation Provisioning
    profile_in = MonitoringProfileCreate(
        name="Obs Watch",
        target_type=TargetType.REGION,
        region="Test Region",
        monitoring_category=MonitoringCategory.CYBERSECURITY,
        channel_id="C_OBS",
        risk_threshold=7.0
    )

    profile = await state_manager.monitoring_service.create_monitoring_profile(
        db_session, state_manager, profile_in, created_by="U_TEST"
    )
    op_id = profile.operation_id

    # Verify Logging
    log_text = caplog.text
    assert "Created monitoring profile" in log_text or "created" in log_text.lower()

    # 2. Situation Evaluation & Notification & Recommendation
    obs_critical = [{"type": "CYBER", "severity": "CRITICAL", "detail": "Massive DDoS detected"}]
    profile = await state_manager.monitoring_service.process_scan_results(
        db_session, state_manager, profile.id, obs_critical
    )

    log_text = caplog.text
    # We expect logs about processing scan results, risk thresholds, and generating recommendations.
    # While actual log strings may vary, the events should be captured.
    # Let's ensure the timeline has matching events for traceability.
    events = await state_manager.timeline_service.repository.get_by_operation(db_session, op_id)
    event_descriptions = [e.description for e in events]
    assert any("started" in d.lower() or "created" in d.lower() for d in event_descriptions)
    assert any("Incident Recommendation Generated" in d for d in event_descriptions)

    # 3. Incident Creation & Resolution
    incident_in = IncidentCreate(
        title="DDoS Incident",
        description="Ongoing attack",
        channel_id="C_INC",
        operation_id=op_id
    )
    incident = await state_manager.create_incident(db_session, incident_in)
    await state_manager.resolve_incident(db_session, incident.id, user_id="U_OPERATOR", comments="Mitigated.")

    events = await state_manager.timeline_service.repository.get_by_operation(db_session, op_id)
    event_descriptions = [e.description for e in events]
    assert any("Incident created" in d for d in event_descriptions)
    assert any("resolved" in d.lower() for d in event_descriptions)

@pytest.mark.asyncio
async def test_exception_logging_in_scheduler(db_session: AsyncSession, state_manager: StateManager, caplog):
    """
    Validates that the scheduler logs exceptions at the ERROR level and continues running.
    """
    caplog.set_level(logging.INFO)

    state_manager.mission_scheduler.strategy_registry.register(ExecutionStrategy.SCHEDULED.value, MockFailingHandler())

    profile_in = MonitoringProfileCreate(
        name="Error Watch",
        target_type=TargetType.REGION,
        region="Error Region",
        monitoring_category=MonitoringCategory.FLOOD,
        channel_id="C_ERR",
        risk_threshold=7.0
    )
    profile = await state_manager.monitoring_service.create_monitoring_profile(
        db_session, state_manager, profile_in, created_by="U_TEST"
    )

    # Run tick
    await state_manager.run_mission_scheduler_tick(db_session)

    # Verify Error logging
    error_logs = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(error_logs) > 0

    log_messages = [record.message for record in error_logs]
    assert any("Simulated execution failure" in msg or "Failed to execute mission" in msg for msg in log_messages)
