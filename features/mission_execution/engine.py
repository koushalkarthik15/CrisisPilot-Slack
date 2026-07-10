import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.orchestration.models import AgentRequest, ExecutionContext
from core.orchestration.supervisor import SupervisorAgent
from features.mission_execution.exceptions import (
    MissionExecutionError,
)
from features.missions.domain import MissionStatus
from features.missions.models import Mission
from features.timeline.domain import (
    TimelineEventSeverity,
    TimelineEventSource,
    TimelineEventType,
)
from features.timeline.schemas import TimelineEventCreate

logger = logging.getLogger("crisispilot.mission_execution.engine")

class MissionExecutionEngine:
    """Coordinates the execution of a Mission via the Supervisor and Mini-Agents."""

    def __init__(self, supervisor: SupervisorAgent):
        self.supervisor = supervisor

    async def execute(self, db: AsyncSession, state_manager: Any, mission: Mission) -> Mission:
        """Executes a mission. Handles lifecycle and timeline event creation."""

        # 1. Update status to RUNNING
        mission = await state_manager.mission_service.transition_status(db, mission.id, MissionStatus.RUNNING)
        await self._record_timeline(
            db, state_manager, mission,
            TimelineEventType.LIFECYCLE_CHANGE,
            f"Mission '{mission.name}' execution started.",
            TimelineEventSeverity.INFO
        )

        agent_name = mission.assigned_mini_agent_id
        if not agent_name:
            # Manual execution without an assigned AI agent just completes the mission immediately
            mission = await state_manager.mission_service.transition_status(db, mission.id, MissionStatus.COMPLETED)
            await self._record_timeline(
                db, state_manager, mission,
                TimelineEventType.LIFECYCLE_CHANGE,
                f"Mission '{mission.name}' completed manually (no AI agent assigned).",
                TimelineEventSeverity.INFO
            )
            return mission

        await self._record_timeline(
            db, state_manager, mission,
            TimelineEventType.MISSION_EVENT,
            f"Mini-Agent '{agent_name}' assigned to execute mission.",
            TimelineEventSeverity.INFO
        )

        # 2. Build execution context
        context = ExecutionContext(
            event_id=f"mission_{mission.id}_{uuid.uuid4().hex[:8]}",
            channel_id="mission_execution",
            metadata={"mission_id": mission.id, "operation_id": mission.operation_id}
        )

        prompt = f"Execute mission: {mission.name}\nObjective: {mission.objective}\nPriority: {mission.priority.value}"
        request = AgentRequest(context=context, prompt=prompt)

        # 3. Delegate to Agent
        try:
            logger.info(f"Engine delegating mission {mission.id} to Supervisor -> {agent_name}")
            response = await self.supervisor.delegate_to_agent(agent_name, request)

            # 4. Handle Success
            await self._record_timeline(
                db, state_manager, mission,
                TimelineEventType.AI_ACTION,
                f"Mini-Agent '{agent_name}' completed execution. Response: {response.content[:200]}...",
                TimelineEventSeverity.INFO
            )

            mission = await state_manager.mission_service.transition_status(db, mission.id, MissionStatus.COMPLETED)
            await self._record_timeline(
                db, state_manager, mission,
                TimelineEventType.LIFECYCLE_CHANGE,
                f"Mission '{mission.name}' execution completed successfully.",
                TimelineEventSeverity.INFO
            )

            return mission

        except Exception as e:
            # 5. Handle Failure
            error_msg = f"Mission execution failed during agent delegation: {str(e)}"
            logger.error(error_msg)
            await self._fail_mission(db, state_manager, mission, error_msg)
            raise MissionExecutionError(error_msg) from e

    async def _fail_mission(self, db: AsyncSession, state_manager: Any, mission: Mission, reason: str):
        await state_manager.mission_service.transition_status(db, mission.id, MissionStatus.FAILED)
        await self._record_timeline(
            db, state_manager, mission,
            TimelineEventType.LIFECYCLE_CHANGE,
            reason,
            TimelineEventSeverity.ERROR
        )

    async def _record_timeline(self, db: AsyncSession, state_manager: Any, mission: Mission, event_type: TimelineEventType, description: str, severity: TimelineEventSeverity):
        event_in = TimelineEventCreate(
            event_type=event_type,
            description=description,
            source=TimelineEventSource.MISSION_ENGINE,
            severity=severity,
            mission_id=mission.id,
            operation_id=mission.operation_id,
            incident_id=mission.incident_id
        )
        await state_manager.create_timeline_event(db, event_in)
