import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from core.errors import ToolExecutionError
from infrastructure.mcp.models import ToolRequest, ToolResponse

logger = logging.getLogger("crisispilot.mcp")


class BaseTool(ABC):
    """
    Abstract Base Class for all CrisisPilot tools.
    This abstraction ensures the rest of the application remains agnostic
    to the specific underlying MCP SDK implementation.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """A detailed description of what the tool does and when to use it."""
        pass
        
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """
        JSON Schema defining the tool's expected arguments.
        Example:
        {
            "type": "object",
            "properties": {
                "arg1": {"type": "string", "description": "..."}
            },
            "required": ["arg1"]
        }
        """
        pass

    @abstractmethod
    async def execute(self, request: ToolRequest) -> ToolResponse:
        """
        The core execution logic of the tool.
        Must be implemented by subclasses.
        """
        pass

    async def _safe_execute(self, request: ToolRequest) -> ToolResponse:
        """
        Wrapper around execute to provide standardized logging and error propagation.
        """
        logger.debug(f"Executing tool '{self.name}' with arguments: {request.arguments}")
        try:
            response = await self.execute(request)
            logger.debug(f"Tool '{self.name}' execution completed.")
            return response
        except Exception as e:
            logger.error(f"Tool '{self.name}' execution failed: {e}", exc_info=True)
            return ToolResponse(
                is_error=True,
                content=f"Tool execution failed: {str(e)}",
                metadata={"error_type": type(e).__name__}
            )
