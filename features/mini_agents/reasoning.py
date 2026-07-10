import json
import logging
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

from core.llm.base import BaseLLMProvider
from core.llm.models import LLMRequest
from infrastructure.mcp.registry import MCPRegistry
from features.mini_agents.prompts import build_tool_selection_prompt
from features.mini_agents.exceptions import MiniAgentExecutionError

logger = logging.getLogger("crisispilot.mini_agents.reasoning")

class ToolDecision(BaseModel):
    """Structured decision output from the LLM."""
    tool: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    justification: str = ""

class ToolSelectionService:
    """
    Service responsible for orchestrating LLM-powered tool selection.
    Injects MCP Tool schemas, forces JSON output, and validates the result.
    """
    def __init__(self, llm_provider: BaseLLMProvider, mcp_registry: MCPRegistry):
        self.llm_provider = llm_provider
        self.mcp_registry = mcp_registry

    async def select_tool(self, prompt: str, allowed_tools: List[str]) -> ToolDecision:
        """Determines the appropriate tool to invoke based on user prompt and allowed capabilities."""
        
        # 1. Gather tool metadata
        all_capabilities = self.mcp_registry.get_mcp_capabilities()
        
        # 2. Filter by allowed_tools
        # Note: get_mcp_capabilities returns mcp.types.Tool which has name, description, inputSchema
        # Using model_dump() to serialize it to dict safely.
        filtered_schemas = []
        for cap in all_capabilities:
            if cap.name in allowed_tools:
                filtered_schemas.append(cap.model_dump())
                
        if not filtered_schemas:
            logger.warning("No tools available for selection after filtering.")
            return ToolDecision(tool=None, justification="No allowed tools available.", confidence=0.0)

        # 3. Build Prompt
        system_prompt = build_tool_selection_prompt(filtered_schemas)
        
        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # Low temp for deterministic tool selection
            response_format={"type": "json_object"}
        )
        
        # 4. Execute LLM Request
        logger.debug("Requesting tool selection from LLM Provider.")
        response = await self.llm_provider.generate(request)
        
        # 5. Parse and Validate Response
        try:
            decision_dict = json.parse(response.content) if hasattr(json, "parse") else json.loads(response.content)
            decision = ToolDecision(**decision_dict)
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON response: {response.content}")
            raise MiniAgentExecutionError(f"Invalid structured output from LLM: {e}")
            
        # 6. Validate MCP Registry presence and Permissions
        if decision.tool:
            if decision.tool not in allowed_tools:
                logger.error(f"LLM hallucinated or selected unauthorized tool: {decision.tool}")
                raise MiniAgentExecutionError(f"Selected tool '{decision.tool}' is not permitted.")
            
            try:
                # Double check it exists in registry just to be safe
                self.mcp_registry.get_tool(decision.tool)
            except Exception as e:
                logger.error(f"Selected tool '{decision.tool}' not found in MCP registry.")
                raise MiniAgentExecutionError(f"Selected tool '{decision.tool}' is invalid.")
                
        logger.info(f"Tool Selection Complete | Tool: {decision.tool} | Confidence: {decision.confidence} | Justification: {decision.justification}")
        return decision
