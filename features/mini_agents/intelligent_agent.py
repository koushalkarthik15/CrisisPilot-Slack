import logging

from core.llm.base import BaseLLMProvider
from core.orchestration.base import BaseMiniAgent
from core.orchestration.models import AgentRequest, AgentResponse, ToolInvocation
from core.services import registry as service_registry
from features.mini_agents.exceptions import MiniAgentExecutionError
from features.mini_agents.reasoning import ToolSelectionService
from infrastructure.mcp.executor import MCPExecutor
from infrastructure.mcp.models import ToolRequest
from infrastructure.mcp.registry import MCPRegistry

logger = logging.getLogger("crisispilot.mini_agents.intelligent_agent")

class IntelligentMiniAgent(BaseMiniAgent):
    """
    A Mini-Agent that uses the LLM Provider and ToolSelectionService to intelligently
    select and execute MCP tools based on the user's prompt.
    """
    def __init__(self, name: str, description: str, system_prompt: str, allowed_tools: list[str]):
        super().__init__(name=name, description=description, system_prompt=system_prompt, allowed_tools=allowed_tools)
        self.tool_service = None

    async def initialize(self) -> None:
        await super().initialize()
        llm_provider = service_registry.get(BaseLLMProvider)
        mcp_registry = service_registry.get(MCPRegistry)
        self.tool_service = ToolSelectionService(llm_provider=llm_provider, mcp_registry=mcp_registry)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        logger.info(f"[{self.name}] Intelligent execution started for prompt: '{request.prompt}'")

        if not self.tool_service:
            raise MiniAgentExecutionError("IntelligentMiniAgent not properly initialized (ToolSelectionService missing).")

        # 1. Select Tool
        decision = await self.tool_service.select_tool(request.prompt, self.allowed_tools)

        # 2. If no tool selected
        if not decision.tool:
            return AgentResponse(
                content=f"I couldn't identify a tool to help with this request. Justification: {decision.justification}",
                confidence_score=decision.confidence
            )

        # 3. Execute Tool
        mcp_executor = service_registry.get(MCPExecutor)
        tool_req = ToolRequest(
            name=decision.tool,
            arguments=decision.arguments
        )

        tool_invocations = [ToolInvocation(tool_name=decision.tool, arguments=decision.arguments)]
        logger.debug(f"[{self.name}] Invoking MCP tool '{tool_req.name}'")

        tool_response = await mcp_executor.execute_tool(tool_req)

        # 4. Return formatted response
        if tool_response.is_error:
            logger.error(f"[{self.name}] Tool execution failed: {tool_response.content}")
            return AgentResponse(
                content=f"Tool Execution Failed: {tool_response.content}\nReasoning: {decision.justification}",
                confidence_score=0.2,
                tools_invoked=tool_invocations
            )

        return AgentResponse(
            content=f"Task Completed Successfully.\n\nJustification: {decision.justification}\n\nTool Output:\n{tool_response.content}",
            confidence_score=decision.confidence,
            tools_invoked=tool_invocations,
            metadata={"mcp_response": tool_response.metadata}
        )
