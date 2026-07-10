import logging
from typing import Dict, List

from mcp.types import Tool as MCPTool

from core.errors import ToolNotFoundError
from infrastructure.mcp.base import BaseTool

logger = logging.getLogger("crisispilot.mcp.registry")


class MCPRegistry:
    """
    Central registry for all MCP tools available to the orchestration layer.
    Keeps track of registered BaseTool implementations and can generate
    standard MCP capability schemas.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initializes the Tool Registry."""
        logger.info("Initializing MCP Tool Registry...")
        self._initialized = True
        logger.info("MCP Tool Registry operational.")

    async def shutdown(self) -> None:
        """Gracefully shuts down the Tool Registry."""
        logger.info("Shutting down MCP Tool Registry...")
        self._tools.clear()
        self._initialized = False

    def register(self, tool: BaseTool) -> None:
        """Registers a new tool into the registry."""
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool registration: {tool.name}")

        self._tools[tool.name] = tool
        logger.info(f"Registered MCP tool: {tool.name}")

    def get_tool(self, name: str) -> BaseTool:
        """Retrieves a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ToolNotFoundError(f"Tool not found in MCP registry: {name}")
        return tool

    def get_mcp_capabilities(self) -> List[MCPTool]:
        """
        Returns the registered tools as standard MCP Tool objects.
        This allows interoperability with the official MCP SDK without leaking
        the SDK outside of this infrastructure module.
        """
        capabilities = []
        for tool in self._tools.values():
            mcp_tool = MCPTool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema
            )
            capabilities.append(mcp_tool)
        return capabilities
