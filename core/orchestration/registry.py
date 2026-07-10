import logging
from typing import Dict, List

from core.errors import OrchestrationError
from core.orchestration.base import BaseAgent

logger = logging.getLogger("crisispilot.orchestration.registry")


class AgentRegistry:
    """
    Manages the lifecycle and lookup of registered Mini-Agents.
    """
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Bootstraps the Agent Registry."""
        logger.info("Initializing Agent Registry...")
        self._initialized = True
        logger.info("Agent Registry operational.")

    async def shutdown(self) -> None:
        """Gracefully shuts down the Agent Registry."""
        logger.info("Shutting down Agent Registry...")
        self._agents.clear()
        self._initialized = False

    def register(self, agent: BaseAgent) -> None:
        """Registers a new Mini-Agent dynamically."""
        if not self._initialized:
            raise OrchestrationError("Cannot register agents before registry initialization.")
        
        if agent.name in self._agents:
            logger.warning(f"Overwriting existing agent registration: {agent.name}")
            
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")

    def deregister(self, name: str) -> None:
        """Removes a Mini-Agent from the registry dynamically."""
        if not self._initialized:
            raise OrchestrationError("Cannot deregister agents before registry initialization.")
            
        if name in self._agents:
            del self._agents[name]
            logger.info(f"Deregistered agent: {name}")
        else:
            logger.warning(f"Attempted to deregister non-existent agent: {name}")

    def get_agent(self, name: str) -> BaseAgent:
        """Retrieves an agent by name."""
        agent = self._agents.get(name)
        if not agent:
            raise OrchestrationError(f"Agent not found: {name}")
        return agent

    def list_agents(self) -> List[str]:
        """Lists all registered agent names."""
        return list(self._agents.keys())
