class MiniAgentFrameworkError(Exception):
    """Base exception for all Mini-Agent related errors."""
    pass

class MiniAgentExecutionError(MiniAgentFrameworkError):
    """Raised when a Mini-Agent fails to execute its assigned task."""
    pass

class MiniAgentConfigurationError(MiniAgentFrameworkError):
    """Raised when a Mini-Agent is improperly configured (e.g., invalid tools)."""
    pass

class AgentNotFoundError(MiniAgentFrameworkError):
    """Raised when a requested Mini-Agent does not exist in the registry."""
    pass
