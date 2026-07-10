from core.errors import CrisisPilotError

class OperationNotFoundError(CrisisPilotError):
    """Raised when an operation cannot be found."""
    def __init__(self, operation_id: str):
        super().__init__(f"Operation with ID {operation_id} not found.")

class InvalidOperationStateTransitionError(CrisisPilotError):
    """Raised when an invalid operation state transition is attempted."""
    def __init__(self, current_status: str, target_status: str):
        super().__init__(f"Invalid transition from {current_status} to {target_status}")

class DuplicateOperationNameError(CrisisPilotError):
    """Raised when attempting to create an operation with a name that already exists."""
    def __init__(self, name: str):
        super().__init__(f"An active operation with name '{name}' already exists.")
