from datetime import datetime, timezone
from typing import Any, Dict

from infrastructure.mcp.base import BaseTool
from infrastructure.mcp.models import ToolRequest, ToolResponse


class EchoTool(BaseTool):
    """
    Internal diagnostic tool used solely to verify the MCP framework pipeline.
    It returns the system time and echoes back the provided arguments.
    It is not a business capability and should only be used for health checks.
    """

    @property
    def name(self) -> str:
        return "diagnostic_echo"

    @property
    def description(self) -> str:
        return "Internal framework validation tool. Returns system time and echoes arguments."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to echo back."
                }
            },
            "required": ["message"]
        }

    async def execute(self, request: ToolRequest) -> ToolResponse:
        message = request.arguments.get("message", "No message provided.")
        current_time = datetime.now(timezone.utc).isoformat()

        content = f"Echo: {message} | Server Time: {current_time}"

        return ToolResponse(
            is_error=False,
            content=content,
            metadata={"processed_at": current_time}
        )
