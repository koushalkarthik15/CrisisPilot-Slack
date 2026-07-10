class WorkflowEngineError(Exception):
    """Base exception for all workflow logic errors."""
    pass

class InvalidDecisionTransitionError(WorkflowEngineError):
    """Raised when an illegal transition is attempted on a recommendation."""
    def __init__(self, action: str, current_status: str):
        super().__init__(f"Cannot apply action {action} to recommendation currently in status {current_status}")

class WorkflowPersistenceError(WorkflowEngineError):
    """Raised when failing to persist audit trails or recommendation statuses."""
    pass
