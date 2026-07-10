from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionContext(BaseModel):
    """
    Encapsulates the state of a request as it passes through the orchestration layer.
    """
    event_id: str
    channel_id: str
    user_id: Optional[str] = None
    raw_event: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    delegation_chain: List[str] = Field(default_factory=list, description="Tracks which agents this request has passed through")


class AgentRequest(BaseModel):
    """Standardized input for any agent."""
    context: ExecutionContext
    prompt: str
    history: List[Dict[str, str]] = Field(default_factory=list)
    available_tools: List[str] = Field(default_factory=list, description="Tools the agent is permitted to use")


class ToolInvocation(BaseModel):
    """Represents a request to execute an MCP tool."""
    tool_name: str
    arguments: Dict[str, Any]


class AgentResponse(BaseModel):
    """Standardized output from an agent execution."""
    content: str
    confidence_score: float = 1.0
    tools_invoked: List[ToolInvocation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
