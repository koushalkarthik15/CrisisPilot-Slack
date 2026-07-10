import logging
from abc import ABC, abstractmethod

from core.errors import OrchestrationError
from core.orchestration.models import AgentRequest, AgentResponse

logger = logging.getLogger("crisispilot.orchestration")


class BaseAgent(ABC):
    """
    Abstract Base Class for all intelligent agents in CrisisPilot.
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Executes the agent's primary logic based on the input request.
        Must be implemented by all subclasses.
        """
        pass

    async def _safe_execute(self, request: AgentRequest) -> AgentResponse:
        """
        Wrapper around execute to provide standardized logging and error propagation.
        """
        logger.debug(f"Agent '{self.name}' execution started for event {request.context.event_id}")
        try:
            response = await self.execute(request)
            logger.debug(f"Agent '{self.name}' execution completed successfully.")
            return response
        except Exception as e:
            logger.error(f"Agent '{self.name}' execution failed: {e}", exc_info=True)
            raise OrchestrationError(f"Agent '{self.name}' failed to execute: {e}") from e

class BaseMiniAgent(BaseAgent, ABC):
    """
    Abstract Base Class specifically for Mini-Agents.
    Mini-Agents extend standard agents by incorporating LLM configuration, 
    system prompts, and allowed MCP tools.
    """
    def __init__(self, name: str, description: str, system_prompt: str, allowed_tools: list[str]):
        super().__init__(name=name, description=description)
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools
        self._initialized = False

    async def initialize(self) -> None:
        """Bootstraps the Mini-Agent (e.g., verifying tools or loading models)."""
        logger.info(f"Initializing Mini-Agent: {self.name}")
        self._initialized = True

    async def shutdown(self) -> None:
        """Cleans up Mini-Agent resources."""
        logger.info(f"Shutting down Mini-Agent: {self.name}")
        self._initialized = False

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Executes the Mini-Agent logic. 
        In Milestone 4.2+, this will wrap the LLM call.
        """
        pass
