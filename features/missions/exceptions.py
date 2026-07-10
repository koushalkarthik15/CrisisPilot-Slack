from core.errors import CrisisPilotError


class MissionNotFoundError(CrisisPilotError):
    """Raised when a mission cannot be found."""
    def __init__(self, mission_id: str):
        super().__init__(f"Mission with ID {mission_id} not found.")

class InvalidMissionStateTransitionError(CrisisPilotError):
    """Raised when an invalid mission state transition is attempted."""
    def __init__(self, current_status: str, target_status: str):
        super().__init__(f"Invalid transition from {current_status} to {target_status}")

class InvalidMissionOwnershipError(CrisisPilotError):
    """Raised when a mission does not have a valid owner (Operation or Incident)."""
    def __init__(self):
        super().__init__("A mission must belong to at least one owner (Operation or Incident).")

class InvalidMissionAssignmentError(CrisisPilotError):
    """Raised when a mission has an invalid assignment."""
    def __init__(self, detail: str):
        super().__init__(f"Invalid mission assignment: {detail}")
