from typing import Any, Dict

from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    """Standardized input model for executing any MCP tool."""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    """Standardized output model for an MCP tool execution."""
    is_error: bool = False
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
