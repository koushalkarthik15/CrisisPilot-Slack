from core.errors import CrisisPilotError

class MissionExecutionError(CrisisPilotError):
    """Raised when mission execution fails generally."""
    pass

class UnsupportedExecutionStrategyError(MissionExecutionError):
    """Raised when a strategy is registered but not implemented."""
    def __init__(self, strategy: str):
        super().__init__(f"Execution strategy '{strategy}' is currently unsupported.")

class AgentResolutionError(MissionExecutionError):
    """Raised when an assigned Mini-Agent cannot be found or loaded."""
    def __init__(self, agent_name: str):
        super().__init__(f"Failed to resolve Mini-Agent: {agent_name}")
