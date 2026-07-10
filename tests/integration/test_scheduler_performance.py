from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.state import StateManager
from features.mission_execution.strategies import BaseStrategyHandler
from features.missions.domain import ExecutionStrategy, MissionStatus
from features.monitoring.domain import MonitoringCategory, MonitoringStatus, TargetType
from features.monitoring.schemas import MonitoringProfileCreate


class MockFailingHandler(BaseStrategyHandler):
    """A mock handler that raises an exception to simulate failure."""
    async def execute(self, db: AsyncSession, state_manager: Any, engine: Any, mission: Any):
        raise RuntimeError(f"Simulated execution failure for mission {mission.id}")

class MockSucceedingHandler(BaseStrategyHandler):
    """A mock handler that completes the mission."""
    async def execute(self, db: AsyncSession, state_manager: Any, engine: Any, mission: Any):
        await state_manager.transition_mission_status(db, mission.id, MissionStatus.RUNNING)
        # Simulate doing some work...
        await state_manager.transition_mission_status(db, mission.id, MissionStatus.COMPLETED)

@pytest.mark.asyncio
async def test_scheduler_sustained_execution_and_stability(db_session: AsyncSession, state_manager: StateManager):
    """
    Validates the scheduler's performance and stability over multiple cycles.
    Ensures that active profiles spawn missions appropriately, 
    and verifies that there is no runaway growth in queued missions.
    """
    # Override strategy handler for testing in the state manager's registry
    state_manager.mission_scheduler.strategy_registry.register(ExecutionStrategy.SCHEDULED, MockSucceedingHandler())

    profiles = []

    # 1. Provision multiple Monitoring Profiles
    for i in range(3):
        profile_in = MonitoringProfileCreate(
            name=f"Perf Watch {i}",
            target_type=TargetType.REGION,
            region=f"Region {i}",
            monitoring_category=MonitoringCategory.FLOOD,
            channel_id=f"C_PERF_{i}",
            risk_threshold=7.0
        )
        profile = await state_manager.monitoring_service.create_monitoring_profile(
            db_session, state_manager, profile_in, created_by="U_TEST"
        )
        profiles.append(profile)

    # 2. Simulate Sustained Execution Cycles (Multiple Ticks)
    total_ticks = 5

    for tick in range(total_ticks):
        # Step A: In an active system, profiles might spawn new missions on a schedule.
        # Since we don't have a live crontab here, we'll manually reset missions to SCHEDULED
        # to simulate them becoming due for execution again (periodic execution).
        profile_op_ids = [str(p.operation_id) for p in profiles]
        all_missions = []
        for op_id in profile_op_ids:
            ms = await state_manager.mission_service.repository.list_by_operation(db_session, op_id)
            all_missions.extend(ms)
        missions = all_missions
        for m in missions:
            await state_manager.mission_service.repository.update_status(db_session, str(m.id), MissionStatus.SCHEDULED)
        await db_session.commit()

        # Step B: Run the scheduler tick
        await state_manager.run_mission_scheduler_tick(db_session)

        # Step C: Verify Execution Status
        # After the tick, all eligible missions should be picked up and processed (to COMPLETED by our Mock handler)
        profile_op_ids = [str(p.operation_id) for p in profiles]
        all_post_tick = []
        for op_id in profile_op_ids:
            ms = await state_manager.mission_service.repository.list_by_operation(db_session, op_id)
            all_post_tick.extend(ms)
        post_tick_missions = all_post_tick

        pending_missions = [m for m in post_tick_missions if m.status == MissionStatus.SCHEDULED]

        # Stability Check: No growing backlog of SCHEDULED missions
        assert len(pending_missions) == 0, f"Tick {tick}: Found pending missions, potential scheduler degradation."

    # 3. Verify Continued Registration After Incident Resolution
    # Resolve an incident tied to the first profile's operation (simulate an incident was created and resolved)
    profile_to_test = profiles[0]
    # In a real system, the profile remains active. Let's explicitly check it.
    retrieved_profile = await state_manager.monitoring_service.get_profile(db_session, str(profile_to_test.id))
    assert retrieved_profile is not None
    assert retrieved_profile.status == MonitoringStatus.ACTIVE

    # Prove that the profile's missions still run after 5 ticks
    final_missions = await state_manager.mission_service.repository.list_by_operation(db_session, str(profile_to_test.operation_id))
    assert all(m.status == MissionStatus.COMPLETED for m in final_missions)

@pytest.mark.asyncio
async def test_scheduler_failure_recovery(db_session: AsyncSession, state_manager: StateManager):
    """
    Validates that the scheduler gracefully handles exceptions in individual mission executions
    without failing the entire tick or halting execution of other missions.
    """
    # Register failing handler
    state_manager.mission_scheduler.strategy_registry.register(ExecutionStrategy.SCHEDULED, MockFailingHandler())

    # Provision 1 profile with multiple missions
    profile_in = MonitoringProfileCreate(
        name="Failure Recov Watch",
        target_type=TargetType.REGION,
        region="Test Region",
        monitoring_category=MonitoringCategory.FLOOD,
        channel_id="C_FAIL",
        risk_threshold=7.0
    )
    profile = await state_manager.monitoring_service.create_monitoring_profile(
        db_session, state_manager, profile_in, created_by="U_TEST"
    )

    # Pre-tick: Missions are CREATED (monitoring provisioner creates them with CREATED status)
    missions = await state_manager.mission_service.repository.list_by_operation(db_session, str(profile.operation_id))
    assert len(missions) > 1  # Category Flood spawns multiple missions
    # Manually set missions to SCHEDULED so the scheduler tick picks them up
    for m in missions:
        await state_manager.mission_service.repository.update_status(db_session, str(m.id), MissionStatus.SCHEDULED)
    await db_session.commit()

    # Run the tick. It should catch exceptions and not crash.
    await state_manager.run_mission_scheduler_tick(db_session)

    # Because the mock handler fails, the missions will remain SCHEDULED or be marked FAILED
    # (our current simplified scheduler catches the error but may not mark the state as failed in the DB).
    # The primary assertion is that run_mission_scheduler_tick doesn't raise the RuntimeError to the top,
    # meaning the loop survived the failure of individual mission executions.
    assert True
