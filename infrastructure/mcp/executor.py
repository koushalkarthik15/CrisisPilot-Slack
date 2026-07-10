import logging

from core.errors import ToolExecutionError
from infrastructure.mcp.models import ToolRequest, ToolResponse
from infrastructure.mcp.registry import MCPRegistry

logger = logging.getLogger("crisispilot.mcp.executor")


class MCPExecutor:
    """
    Execution pipeline for invoking tools securely.
    Acts as the boundary between the Supervisor Agent and the Tool logic.
    """
    def __init__(self, registry: MCPRegistry):
        self.registry = registry
        self._initialized = False

    async def initialize(self) -> None:
        logger.info("Initializing MCP Executor pipeline...")
        self._initialized = True
        logger.info("MCP Executor operational.")

    async def shutdown(self) -> None:
        logger.info("Shutting down MCP Executor...")
        self._initialized = False

    async def execute_tool(self, request: ToolRequest) -> ToolResponse:
        """
        Executes a requested tool using the `_safe_execute` boundary.
        """
        logger.debug(f"MCP Executor received request for tool: {request.name}")
        
        try:
            tool = self.registry.get_tool(request.name)
            # The tool itself handles safe execution and error wrapping
            return await tool._safe_execute(request)
        except Exception as e:
            logger.error(f"Execution pipeline failed for tool {request.name}: {e}", exc_info=True)
            return ToolResponse(
                is_error=True,
                content=f"MCP Pipeline Error: {str(e)}",
                metadata={"error": type(e).__name__}
            )
