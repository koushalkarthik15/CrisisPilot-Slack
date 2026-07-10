from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class UsageMetrics(BaseModel):
    """Tracks token consumption for a single request."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

class LLMRequest(BaseModel):
    """Standardized request payload for the LLM Provider."""
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class LLMResponse(BaseModel):
    """Standardized response payload from the LLM Provider."""
    content: str
    usage: UsageMetrics = Field(default_factory=UsageMetrics)
    metadata: Dict[str, Any] = Field(default_factory=dict)
