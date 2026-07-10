import logging
from typing import Any, Dict

from core.services import registry
from core.state import StateManager
from infrastructure.mcp.base import BaseTool
from infrastructure.mcp.models import ToolRequest, ToolResponse

logger = logging.getLogger("crisispilot.mcp.tools.inventory")

class InventoryTool(BaseTool):
    """
    Internal MCP tool for checking crisis inventory levels directly from the 
    application's persistence layer via the State Manager.
    """

    @property
    def name(self) -> str:
        return "inventory_tool"

    @property
    def description(self) -> str:
        return "Checks current internal inventory levels for crisis resources (e.g., medical supplies, food, water) at a specified hub."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "resource_type": {
                    "type": "string",
                    "description": "Type of resource to check (e.g., 'water', 'medical', 'blankets')."
                },
                "location": {
                    "type": "string",
                    "description": "Name of the distribution hub or shelter to check."
                }
            },
            "required": ["resource_type", "location"]
        }

    async def execute(self, request: ToolRequest) -> ToolResponse:
        resource_type = request.arguments.get("resource_type")
        location = request.arguments.get("location")

        if not resource_type or not location:
            return ToolResponse(is_error=True, content="Missing required arguments: 'resource_type' and 'location'.")

        try:
            # Delegate to the State Manager as per architectural constraints
            state_manager = registry.get(StateManager)
            data = await state_manager.check_inventory(resource_type, location)

            content = (
                f"Inventory check for '{resource_type}' at '{location}':\n"
                f"- Status: {data.get('status')}\n"
                f"- Estimated Quantity: {data.get('quantity')} units\n"
            )

            return ToolResponse(
                is_error=False,
                content=content,
                metadata=data
            )
        except Exception as e:
            logger.error(f"Inventory check failed for {resource_type} at {location}: {e}", exc_info=True)
            return ToolResponse(
                is_error=True,
                content=f"Failed to check inventory: {e}"
            )
