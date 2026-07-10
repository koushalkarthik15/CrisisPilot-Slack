from core.errors import CrisisPilotError


class WorkflowNotFoundError(CrisisPilotError):
    """Raised when a workflow cannot be found."""
    def __init__(self, workflow_id: str):
        super().__init__(f"Workflow with ID {workflow_id} not found.")

class InvalidWorkflowStateTransitionError(CrisisPilotError):
    """Raised when an invalid workflow state transition is attempted."""
    def __init__(self, current_status: str, target_status: str):
        super().__init__(f"Invalid transition from {current_status} to {target_status}")

class InvalidWorkflowOwnershipError(CrisisPilotError):
    """Raised when a workflow does not have a valid owner (Operation or Incident)."""
    def __init__(self):
        super().__init__("A workflow must belong to at least one owner (Operation or Incident).")

class WorkflowStageProgressionError(CrisisPilotError):
    """Raised when an invalid stage progression is attempted."""
    def __init__(self, detail: str):
        super().__init__(f"Workflow stage progression error: {detail}")
