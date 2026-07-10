import logging
import re
from core.orchestration.base import BaseMiniAgent
from core.orchestration.models import AgentRequest, AgentResponse, ToolInvocation
from core.services import registry as service_registry
from infrastructure.mcp.executor import MCPExecutor
from infrastructure.mcp.models import ToolRequest

logger = logging.getLogger("crisispilot.mini_agents.weather")

class WeatherMiniAgent(BaseMiniAgent):
    """
    Production Mini-Agent that retrieves weather information.
    Currently implemented deterministically (without an LLM) to satisfy Milestone 4.2.
    It parses a location from the prompt and invokes the MCP weather_tool.
    """
    def __init__(self):
        super().__init__(
            name="WeatherAgent",
            description="Agent responsible for retrieving weather forecasts and conditions.",
            system_prompt="You are a deterministic weather agent. Extract the location and call weather_tool.",
            allowed_tools=["weather_tool"]
        )

    async def execute(self, request: AgentRequest) -> AgentResponse:
        logger.info(f"[{self.name}] Executing task with prompt: '{request.prompt}'")
        
        # Validate allowed tools
        if "weather_tool" not in request.available_tools:
            logger.error("Configuration error: 'weather_tool' is not allowed for this agent.")
            return AgentResponse(
                content="Error: Missing permissions to execute weather lookup.",
                confidence_score=0.0
            )

        # Very basic deterministic extraction for demonstration:
        # e.g., "Weather in Seattle" -> "Seattle"
        match = re.search(r'(?i)weather in\s+([a-zA-Z\s,]+)', request.prompt)
        location = match.group(1).strip() if match else request.prompt.strip()
        
        logger.debug(f"[{self.name}] Extracted location: {location}")

        # Fetch MCPExecutor from the registry
        try:
            mcp_executor = service_registry.get(MCPExecutor)
        except Exception as e:
            logger.error(f"[{self.name}] Failed to get MCPExecutor from registry: {e}")
            return AgentResponse(
                content="Error: Internal execution pipeline unavailable.",
                confidence_score=0.0
            )

        # Formulate tool request
        tool_req = ToolRequest(
            name="weather_tool",
            arguments={"location": location}
        )
        
        tool_invocations = [ToolInvocation(tool_name="weather_tool", arguments={"location": location})]

        logger.debug(f"[{self.name}] Invoking MCP tool '{tool_req.name}'")
        tool_response = await mcp_executor.execute_tool(tool_req)

        if tool_response.is_error:
            logger.error(f"[{self.name}] Tool execution failed: {tool_response.content}")
            return AgentResponse(
                content=f"I couldn't fetch the weather for '{location}'. {tool_response.content}",
                confidence_score=0.2,
                tools_invoked=tool_invocations
            )

        return AgentResponse(
            content=f"Weather Data Retrieved successfully:\n\n{tool_response.content}",
            confidence_score=1.0,
            tools_invoked=tool_invocations,
            metadata={"mcp_response": tool_response.metadata}
        )
