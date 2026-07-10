import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from core.notifications import NotificationEngine
from core.services import registry
from core.state import StateManager
from features.evidence import EvidenceRepository, EvidenceService
from features.missions import MissionRepository, MissionService
from features.monitoring.evaluator import SituationEvaluator
from features.monitoring.notification_policy import NotificationPolicyEngine
from features.monitoring.repository import MonitoringRepository
from features.monitoring.service import MonitoringService
from features.operations import OperationRepository, OperationService
from features.timeline import TimelineRepository, TimelineService
from features.workflows import WorkflowRepository as OperationalWorkflowRepository
from features.workflows import WorkflowService as OperationalWorkflowService
from tests.mocks.mock_slack import MockSlackClient


class MockNotificationEngine(NotificationEngine):
    def __init__(self):
        self.slack_client = MockSlackClient()
        self.notifications_sent = []
        self._initialized = True

    async def send_notification(self, channel_id, message, blocks=None, thread_ts=None):
        self.notifications_sent.append({
            "channel_id": channel_id,
            "message": message
        })
        return {"ok": True, "ts": "1234.5678"}

    async def dispatch_message(self, channel_id, text, blocks=None, thread_ts=None):
        """Called by NotificationPolicyEngine — records as a sent notification."""
        self.notifications_sent.append({
            "channel_id": channel_id,
            "message": text
        })
        return {"ok": True, "ts": "1234.5678"}

class MockRecommendationService:
    def __init__(self):
        self.repository = type("MockRepo", (), {})()

    async def generate_recommendations(self, db, context, mcp_outputs):
        class MockRec:
            title = "Mock Rec"
        return [MockRec()]

class MockMissionExecutionEngine:
    pass

class MockMissionScheduler:
    def __init__(self):
        from features.mission_execution.strategies import StrategyRegistry
        from features.missions.domain import ExecutionStrategy, MissionStatus
        self.strategy_registry = StrategyRegistry()
        self._ExecutionStrategy = ExecutionStrategy
        self._MissionStatus = MissionStatus

    async def run_tick(self, db, state_manager):
        """Runs one scheduler tick using the strategy registry (mirrors real MissionScheduler)."""
        from features.mission_execution.engine import MissionExecutionEngine
        ExecutionStrategy = self._ExecutionStrategy
        MissionStatus = self._MissionStatus
        eligible = await state_manager.mission_service.repository.list_eligible_for_execution(
            db,
            strategy=ExecutionStrategy.SCHEDULED.value,
            statuses=[MissionStatus.SCHEDULED]
        )
        dummy_engine = MissionExecutionEngine.__new__(MissionExecutionEngine)
        for mission in eligible:
            try:
                handler = self.strategy_registry.get_handler(mission.strategy)
                await handler.execute(db, state_manager, dummy_engine, mission)
            except Exception as e:
                import logging
                logging.getLogger("crisispilot.mock_scheduler").error(
                    f"Failed to execute mission {mission.id} during scheduler tick: {e}"
                )

    async def dispatch_manual(self, db, state_manager, mission_id):
        pass

@pytest_asyncio.fixture
async def state_manager(db_session: AsyncSession) -> StateManager:
    registry.clear()

    # Core
    notif_engine = MockNotificationEngine()
    registry.register(NotificationEngine, notif_engine)

    # Repositories & Services
    op_repo = OperationRepository()
    registry.register(OperationRepository, op_repo)
    registry.register(OperationService, OperationService(repository=op_repo))

    mission_repo = MissionRepository()
    registry.register(MissionRepository, mission_repo)
    registry.register(MissionService, MissionService(repository=mission_repo))

    wf_repo = OperationalWorkflowRepository()
    registry.register(OperationalWorkflowRepository, wf_repo)
    registry.register(OperationalWorkflowService, OperationalWorkflowService(repository=wf_repo))

    tl_repo = TimelineRepository()
    registry.register(TimelineRepository, tl_repo)
    registry.register(TimelineService, TimelineService(repository=tl_repo))

    ev_repo = EvidenceRepository()
    registry.register(EvidenceRepository, ev_repo)
    registry.register(EvidenceService, EvidenceService(repository=ev_repo))

    mon_repo = MonitoringRepository()
    registry.register(MonitoringRepository, mon_repo)
    evaluator = SituationEvaluator()
    registry.register(SituationEvaluator, evaluator)
    policy_engine = NotificationPolicyEngine(notif_engine)
    registry.register(NotificationPolicyEngine, policy_engine)

    mon_svc = MonitoringService(repository=mon_repo, evaluator=evaluator, notification_policy=policy_engine)
    registry.register(MonitoringService, mon_svc)

    from features.mission_execution import MissionExecutionEngine, MissionScheduler
    registry.register(MissionExecutionEngine, MockMissionExecutionEngine())
    registry.register(MissionScheduler, MockMissionScheduler())

    from features.recommendations.intelligence import IncidentIntelligenceService
    class MockIncidentIntelligenceService:
        pass
    registry.register(IncidentIntelligenceService, MockIncidentIntelligenceService())

    from features.recommendations.router import RecommendationRouter
    class MockRecommendationRouter:
        pass
    registry.register(RecommendationRouter, MockRecommendationRouter())

    sm = StateManager()
    sm.recommendation_service = MockRecommendationService()
    await sm.initialize()

    return sm
