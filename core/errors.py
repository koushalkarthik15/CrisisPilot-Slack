class CrisisPilotError(Exception):
    """Base exception for all CrisisPilot specific errors."""
    pass


class ServiceInitializationError(CrisisPilotError):
    """Raised when a core runtime service fails to initialize."""
    pass


class StateError(CrisisPilotError):
    """Raised when there is an invalid state transition or state lookup failure."""
    pass


class NotificationError(CrisisPilotError):
    """Raised when the Notification Engine fails to dispatch a message."""
    pass


class OrchestrationError(CrisisPilotError):
    """Raised during AI agent routing, execution, or registry lookup failures."""
    pass


class MCPError(CrisisPilotError):
    """Base exception for all MCP framework errors."""
    pass


class ToolNotFoundError(MCPError):
    """Raised when an requested tool is not found in the Tool Registry."""
    pass


class ToolExecutionError(MCPError):
    """Raised when a tool fails during execution."""
    pass


