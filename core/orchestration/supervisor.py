import logging
from typing import Any

from core.errors import OrchestrationError
from core.orchestration.base import BaseAgent
from core.orchestration.models import AgentRequest, AgentResponse, ExecutionContext
from core.orchestration.registry import AgentRegistry
from core.services import registry as service_registry

logger = logging.getLogger("crisispilot.orchestration.supervisor")


class SupervisorAgent(BaseAgent):
    """
    The central intelligence node of CrisisPilot.
    Evaluates events and decides whether to handle them or delegate to Mini-Agents.
    """
    def __init__(self, registry: AgentRegistry):
        super().__init__(
            name="SupervisorAgent",
            description="Central orchestrator for incident evaluation and delegation."
        )
        self.registry = registry
        self._initialized = False

    async def initialize(self) -> None:
        logger.info("Initializing Supervisor Agent...")
        self._initialized = True
        logger.info("Supervisor Agent operational.")

    async def shutdown(self) -> None:
        logger.info("Shutting down Supervisor Agent...")
        self._initialized = False

    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Implementation of the BaseAgent execution contract.
        Currently stubbed to return static acknowledgment (no LLM call yet).
        """
        logger.info(f"Supervisor evaluating prompt: {request.prompt[:50]}...")

        # In the future, this will call the LLM to determine routing and action.
        return AgentResponse(
            content="[Orchestration Foundation] Supervisor acknowledges the request.",
            confidence_score=1.0
        )

    async def route_task(self, context: ExecutionContext, prompt: str) -> AgentResponse:
        """
        The primary entrypoint for the RTS to send events into the orchestration pipeline.
        Supervisor gathers context, tool outputs, and passes to State Manager to receive recommendations.
        """
        if not self._initialized:
            raise OrchestrationError("Supervisor Agent is not initialized.")

        logger.debug(f"Routing task for event {context.event_id}")
        request = AgentRequest(context=context, prompt=prompt)

        # In a full flow, safe_execute parses prompt -> calls MCP -> returns final response.
        # Here we simulate gathering context and getting recommendations directly,
        # adhering to the rule: "Gather incident context. Gather MCP tool outputs. Pass both to State Manager."

        # 1. Gather incident context
        from core.state import StateManager
        state_manager = service_registry.get(StateManager)
        # Using a dummy channel_id for testing unless provided in context
        channel_id = "C12345"
        # normally we'd pass db session here, but route_task isn't currently receiving one.
        # We will stub the execute() method instead, since route_task is just the wrapper.
        return await self._safe_execute(request)

    async def handle_workflow_decision(self, db, decision_request) -> Any:
        """
        Entrypoint for processing HITL workflow decisions from external interfaces (like Slack).
        The Supervisor simply passes this to the State Manager and returns the result, acting as a coordinator.
        """
        if not self._initialized:
            raise OrchestrationError("Supervisor Agent is not initialized.")

        logger.debug(f"Supervisor passing workflow decision {decision_request.action.value} for recommendation {decision_request.recommendation_id}")
        from core.state import StateManager
        state_manager = service_registry.get(StateManager)
        return await state_manager.process_recommendation_decision(db, decision_request)

    async def delegate_to_agent(self, agent_name: str, request: AgentRequest) -> AgentResponse:
        """
        Orchestrates delegation from the Supervisor to a specific Mini-Agent.
        Discovers the agent in the registry, updates the execution context tracking,
        and invokes the agent's safe execution pipeline.
        """
        if not self._initialized:
            raise OrchestrationError("Supervisor Agent is not initialized.")

        logger.info(f"Supervisor delegating task to Mini-Agent '{agent_name}'.")

        try:
            agent = self.registry.get_agent(agent_name)
        except OrchestrationError as e:
            logger.error(f"Delegation failed: {e}")
            raise OrchestrationError(f"Cannot delegate to unknown agent: {agent_name}") from e

        # Update delegation tracking
        if self.name not in request.context.delegation_chain:
            request.context.delegation_chain.append(self.name)
        request.context.delegation_chain.append(agent.name)

        # Inject agent's allowed tools if it is a BaseMiniAgent
        from core.orchestration.base import BaseMiniAgent
        if isinstance(agent, BaseMiniAgent):
            request.available_tools = agent.allowed_tools

        logger.debug(f"Delegation chain: {request.context.delegation_chain}")

        # Execute the agent
        return await agent._safe_execute(request)
