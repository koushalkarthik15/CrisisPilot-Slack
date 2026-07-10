import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.orchestration.registry import AgentRegistry
from infrastructure.mcp.registry import MCPRegistry
from features.mini_agents.models import MiniAgentModel
from features.mini_agents.repository import MiniAgentRepository
from features.mini_agents.factory import MiniAgentFactory
from features.mini_agents.exceptions import MiniAgentConfigurationError

logger = logging.getLogger("crisispilot.mini_agents.service")

class MiniAgentManagementService:
    """
    Coordinates CRUD operations on persisted agents and synchronizes them
    with the runtime AgentRegistry.
    """
    def __init__(
        self,
        session: AsyncSession,
        agent_registry: AgentRegistry,
        mcp_registry: MCPRegistry
    ):
        self.session = session
        self.repository = MiniAgentRepository(session)
        self.agent_registry = agent_registry
        self.mcp_registry = mcp_registry

    async def _validate_tools(self, tools: List[str]) -> None:
        """Validates that all provided tools exist in the MCP Registry."""
        for tool in tools:
            try:
                # Assuming get_tool raises an error if not found.
                self.mcp_registry.get_tool(tool)
            except Exception as e:
                raise MiniAgentConfigurationError(f"Tool validation failed for '{tool}': {str(e)}")

    async def load_persisted_agents(self) -> None:
        """Fetches all enabled agents from DB and registers them into memory."""
        logger.info("Loading persisted Mini-Agents into memory...")
        agents = await self.repository.get_all(enabled_only=True)
        
        for model in agents:
            try:
                # We skip re-validation of tools here assuming they were valid at creation.
                agent_instance = MiniAgentFactory.create_agent(model)
                await agent_instance.initialize()
                self.agent_registry.register(agent_instance)
            except Exception as e:
                logger.error(f"Failed to load agent {model.name}: {e}")

    async def create_agent(self, data: dict) -> MiniAgentModel:
        """Creates a new agent, validates it, saves to DB, and registers to memory."""
        name = data.get("name")
        if not name:
            raise MiniAgentConfigurationError("Agent must have a name.")
            
        existing = await self.repository.get_by_name(name)
        if existing:
            raise MiniAgentConfigurationError(f"Agent with name '{name}' already exists.")

        allowed_tools = data.get("allowed_tools", [])
        await self._validate_tools(allowed_tools)

        model = MiniAgentModel(**data)
        created_model = await self.repository.create(model)
        await self.session.commit()
        
        logger.info(f"Persisted new Mini-Agent: {name}")

        if created_model.is_enabled:
            agent_instance = MiniAgentFactory.create_agent(created_model)
            await agent_instance.initialize()
            self.agent_registry.register(agent_instance)
            
        return created_model

    async def update_agent(self, name: str, data: dict) -> Optional[MiniAgentModel]:
        """Updates an agent, saves to DB, deregisters old and registers new instance."""
        existing = await self.repository.get_by_name(name)
        if not existing:
            raise MiniAgentConfigurationError(f"Agent '{name}' not found.")

        if "allowed_tools" in data:
            await self._validate_tools(data["allowed_tools"])

        updated_model = await self.repository.update(name, data)
        await self.session.commit()
        
        logger.info(f"Updated persisted Mini-Agent: {name}")

        # Sync runtime memory
        self.agent_registry.deregister(name)
        
        if updated_model.is_enabled:
            agent_instance = MiniAgentFactory.create_agent(updated_model)
            await agent_instance.initialize()
            self.agent_registry.register(agent_instance)

        return updated_model

    async def delete_agent(self, name: str) -> bool:
        """Deletes an agent from DB and deregisters from memory."""
        existing = await self.repository.get_by_name(name)
        if not existing:
            raise MiniAgentConfigurationError(f"Agent '{name}' not found.")

        deleted = await self.repository.delete(name)
        await self.session.commit()
        
        if deleted:
            logger.info(f"Deleted persisted Mini-Agent: {name}")
            self.agent_registry.deregister(name)
            
        return deleted
