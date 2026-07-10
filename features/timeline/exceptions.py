from core.errors import CrisisPilotError

class InvalidTimelineEventError(CrisisPilotError):
    """Raised when a timeline event violates business rules (e.g., missing ownership)."""
    def __init__(self, detail: str = "A timeline event must belong to at least one entity."):
        super().__init__(detail)
