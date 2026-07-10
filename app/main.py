import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.errors import CrisisPilotError, ServiceInitializationError
from core.llm.guardrails import UsageGuardrail
from core.notifications import NotificationEngine
from core.orchestration.registry import AgentRegistry
from core.orchestration.supervisor import SupervisorAgent
from core.services import registry
from core.state import StateManager
from features.analytics.scheduler import SummaryDigestScheduler
from features.evidence import EvidenceRepository, EvidenceService
from features.mission_execution import (
    MissionExecutionEngine,
    MissionScheduler,
    StrategyRegistry,
)
from features.missions import MissionRepository, MissionService
from features.monitoring.evaluator import SituationEvaluator
from features.monitoring.notification_policy import NotificationPolicyEngine
from features.monitoring.repository import MonitoringRepository
from features.monitoring.service import MonitoringService
from features.operations import OperationRepository, OperationService
from features.recommendations.intelligence import (
    IncidentDomainEnum,
    IncidentIntelligenceService,
)
from features.recommendations.providers.cybersecurity import CybersecurityProvider
from features.recommendations.providers.environmental import EnvironmentalProvider
from features.recommendations.providers.generic import GenericProvider
from features.recommendations.providers.humanitarian import HumanitarianProvider
from features.recommendations.providers.industrial import IndustrialProvider
from features.recommendations.providers.infrastructure import InfrastructureProvider
from features.recommendations.providers.natural_disaster import NaturalDisasterProvider
from features.recommendations.providers.public_health import PublicHealthProvider
from features.recommendations.providers.transportation import TransportationProvider
from features.recommendations.providers.weather import WeatherProvider
from features.recommendations.router import RecommendationRouter
from features.timeline import TimelineRepository, TimelineService
from features.watchlists.monitor import NewsMonitorCoordinator
from features.workflows import WorkflowRepository as OperationalWorkflowRepository
from features.workflows import WorkflowService as OperationalWorkflowService
from infrastructure.database import close_db, init_db
from infrastructure.llm.groq_provider import GroqProvider
from infrastructure.logger import setup_logging
from infrastructure.mcp.diagnostic import EchoTool
from infrastructure.mcp.executor import MCPExecutor
from infrastructure.mcp.registry import MCPRegistry
from infrastructure.mcp.tools import InventoryTool, MapsTool, NewsTool, WeatherTool
from infrastructure.slack_integration import close_slack, init_slack, slack_app

logger = logging.getLogger("crisispilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runtime bootstrap sequence.
    Handles startup and shutdown events for the application.
    """
    try:
        # Initialize logging foundation first
        setup_logging()

        # Load centralized configuration
        settings = get_settings()
        logger.info(f"Starting CrisisPilot in {settings.APP_ENV} mode")

        # 1. Initialize persistence layer
        await init_db()

        # 2. Initialize Slack Platform
        await init_slack()

        # 3. Initialize Core Runtime Services
        logger.info("Bootstrapping core runtime services...")

        notification_engine = NotificationEngine(slack_client=slack_app.client)
        await notification_engine.initialize()
        registry.register(NotificationEngine, notification_engine)

        # Guardrails (MetricsProvider)
        guardrail = UsageGuardrail()
        registry.register(UsageGuardrail, guardrail)

        # Intelligence & Recommendation Routing
        logger.info("Bootstrapping Incident Intelligence & Recommendation Router...")
        llm_provider = GroqProvider()
        await llm_provider.initialize()
        from core.llm.base import BaseLLMProvider
        registry.register(BaseLLMProvider, llm_provider)

        intelligence_service = IncidentIntelligenceService(llm_provider)
        registry.register(IncidentIntelligenceService, intelligence_service)

        router = RecommendationRouter()
        router.register(IncidentDomainEnum.CYBERSECURITY, CybersecurityProvider())
        router.register(IncidentDomainEnum.WEATHER, WeatherProvider())
        router.register(IncidentDomainEnum.NATURAL_DISASTER, NaturalDisasterProvider())
        router.register(IncidentDomainEnum.PUBLIC_HEALTH, PublicHealthProvider())
        router.register(IncidentDomainEnum.INFRASTRUCTURE, InfrastructureProvider())
        router.register(IncidentDomainEnum.TRANSPORTATION, TransportationProvider())
        router.register(IncidentDomainEnum.INDUSTRIAL, IndustrialProvider())
        router.register(IncidentDomainEnum.HUMANITARIAN, HumanitarianProvider())
        router.register(IncidentDomainEnum.ENVIRONMENTAL, EnvironmentalProvider())
        router.register(IncidentDomainEnum.GENERIC, GenericProvider())
        registry.register(RecommendationRouter, router)

        # Register Operations Domain Foundation
        logger.info("Bootstrapping Operations Domain...")
        operation_repository = OperationRepository()
        registry.register(OperationRepository, operation_repository)
        operation_service = OperationService(repository=operation_repository)
        registry.register(OperationService, operation_service)

        # Register Mission Management Foundation
        logger.info("Bootstrapping Mission Management...")
        mission_repository = MissionRepository()
        registry.register(MissionRepository, mission_repository)
        mission_service = MissionService(repository=mission_repository)
        registry.register(MissionService, mission_service)

        # Register Operational Workflow Foundation
        logger.info("Bootstrapping Operational Workflow Engine...")
        op_workflow_repository = OperationalWorkflowRepository()
        registry.register(OperationalWorkflowRepository, op_workflow_repository)
        op_workflow_service = OperationalWorkflowService(repository=op_workflow_repository)
        registry.register(OperationalWorkflowService, op_workflow_service)

        # Register Timeline Subsystem
        logger.info("Bootstrapping Timeline Subsystem...")
        timeline_repository = TimelineRepository()
        registry.register(TimelineRepository, timeline_repository)
        timeline_service = TimelineService(repository=timeline_repository)
        registry.register(TimelineService, timeline_service)

        # Register Evidence Subsystem
        logger.info("Bootstrapping Evidence Subsystem...")
        evidence_repository = EvidenceRepository()
        registry.register(EvidenceRepository, evidence_repository)
        evidence_service = EvidenceService(repository=evidence_repository)
        registry.register(EvidenceService, evidence_service)

        # Register Monitoring Subsystem
        logger.info("Bootstrapping Monitoring Subsystem...")
        monitoring_repository = MonitoringRepository()
        registry.register(MonitoringRepository, monitoring_repository)
        situation_evaluator = SituationEvaluator()
        registry.register(SituationEvaluator, situation_evaluator)
        notification_policy = NotificationPolicyEngine(notification_engine)
        registry.register(NotificationPolicyEngine, notification_policy)
        monitoring_service = MonitoringService(repository=monitoring_repository, evaluator=situation_evaluator, notification_policy=notification_policy)
        registry.register(MonitoringService, monitoring_service)

        # 4. Initialize Orchestration Foundation
        logger.info("Bootstrapping orchestration foundation...")
        agent_registry = AgentRegistry()
        await agent_registry.initialize()
        registry.register(AgentRegistry, agent_registry)

        supervisor_agent = SupervisorAgent(registry=agent_registry)
        await supervisor_agent.initialize()
        registry.register(SupervisorAgent, supervisor_agent)
        logger.info("Orchestration foundation successfully bootstrapped.")

        # 5. Initialize MCP Platform Foundation
        logger.info("Bootstrapping MCP platform foundation...")
        mcp_registry = MCPRegistry()
        await mcp_registry.initialize()

        # Register the diagnostic tool for pipeline validation
        diagnostic_tool = EchoTool()
        mcp_registry.register(diagnostic_tool)

        # Register Core MCP Tool Suite
        mcp_registry.register(WeatherTool())
        mcp_registry.register(NewsTool())
        mcp_registry.register(MapsTool())
        mcp_registry.register(InventoryTool())

        registry.register(MCPRegistry, mcp_registry)

        mcp_executor = MCPExecutor(registry=mcp_registry)
        await mcp_executor.initialize()
        registry.register(MCPExecutor, mcp_executor)
        logger.info("MCP platform foundation successfully bootstrapped.")

        # Load persisted Mini-Agents into Agent Registry
        logger.info("Loading persisted Mini-Agents...")
        from features.mini_agents.service import MiniAgentManagementService
        from infrastructure.database import get_db_session
        session_gen = get_db_session()
        session = await anext(session_gen)
        try:
            mini_agent_svc = MiniAgentManagementService(
                session=session,
                agent_registry=agent_registry,
                mcp_registry=mcp_registry
            )
            await mini_agent_svc.load_persisted_agents()
        finally:
            await session.close()

        # Register Mission Execution Subsystem
        logger.info("Bootstrapping Mission Execution Subsystem...")
        supervisor_agent = registry.get(SupervisorAgent) # Make sure this gets resolved correctly
        mission_engine = MissionExecutionEngine(supervisor=supervisor_agent)
        registry.register(MissionExecutionEngine, mission_engine)

        strategy_registry = StrategyRegistry()
        registry.register(StrategyRegistry, strategy_registry)

        mission_scheduler = MissionScheduler(engine=mission_engine, strategy_registry=strategy_registry)
        registry.register(MissionScheduler, mission_scheduler)

        state_manager = StateManager()
        await state_manager.initialize()
        registry.register(StateManager, state_manager)

        logger.info("Core runtime services successfully bootstrapped.")

        # 6. Start Background Tasks
        logger.info("Starting background services...")
        monitor_coordinator = NewsMonitorCoordinator()
        await monitor_coordinator.start()
        registry.register(NewsMonitorCoordinator, monitor_coordinator)

        digest_scheduler = SummaryDigestScheduler()
        await digest_scheduler.start()
        registry.register(SummaryDigestScheduler, digest_scheduler)

        from features.mission_execution.runner import MissionSchedulerBackgroundRunner
        mission_background_runner = MissionSchedulerBackgroundRunner(interval_seconds=30)
        await mission_background_runner.start()
        registry.register(MissionSchedulerBackgroundRunner, mission_background_runner)

    except Exception as e:
        logger.error(f"CRITICAL STARTUP ERROR: {e}")
        raise RuntimeError("Failed to bootstrap CrisisPilot") from e

    yield

    try:
        # Graceful shutdowns in reverse order
        logger.info("Initiating graceful shutdown sequence...")

        try:
            try:
                digest_scheduler = registry.get(SummaryDigestScheduler)
                await digest_scheduler.stop()
            except ServiceInitializationError:
                pass

            try:
                monitor_coordinator = registry.get(NewsMonitorCoordinator)
                await monitor_coordinator.stop()
            except ServiceInitializationError:
                pass

            try:
                from features.mission_execution.runner import (
                    MissionSchedulerBackgroundRunner,
                )
                mission_background_runner = registry.get(MissionSchedulerBackgroundRunner)
                await mission_background_runner.stop()
            except ServiceInitializationError:
                pass

            mcp_executor = registry.get(MCPExecutor)
            await mcp_executor.shutdown()

            mcp_registry = registry.get(MCPRegistry)
            await mcp_registry.shutdown()

            supervisor_agent = registry.get(SupervisorAgent)
            await supervisor_agent.shutdown()

            agent_registry = registry.get(AgentRegistry)
            await agent_registry.shutdown()

            notification_engine = registry.get(NotificationEngine)
            await notification_engine.shutdown()

            state_manager = registry.get(StateManager)
            await state_manager.shutdown()

            registry.clear()
        except ServiceInitializationError:
            logger.warning("Services were not fully initialized; skipping service teardown.")

        await close_slack()
        await close_db()
        logger.info("Shutting down CrisisPilot")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="CrisisPilot",
    description="Slack-native autonomous multi-agent operations platform",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(CrisisPilotError)
async def crisispilot_exception_handler(request: Request, exc: CrisisPilotError):
    """Centralized exception handler for all domain-specific errors."""
    logger.error(f"CrisisPilot Error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal operational error occurred.", "details": str(exc)},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API and runtime services are running."""
    services_health = registry.get_health()

    return {
        "status": "ok",
        "environment": get_settings().APP_ENV,
        "services": services_health
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
