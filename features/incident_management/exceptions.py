class IncidentManagementError(Exception):
    """Base exception for all Incident Management domain errors."""
    pass

class InvalidStateTransitionError(IncidentManagementError):
    """Raised when an incident attempts an illegal state transition."""
    def __init__(self, current_status: str, target_status: str):
        super().__init__(f"Invalid transition from {current_status} to {target_status}")

class IncidentNotFoundError(IncidentManagementError):
    """Raised when an incident cannot be found in the repository."""
    pass
