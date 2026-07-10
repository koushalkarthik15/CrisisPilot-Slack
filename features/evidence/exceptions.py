from core.errors import CrisisPilotError


class EvidenceNotFoundError(CrisisPilotError):
    """Raised when evidence cannot be found."""
    def __init__(self, evidence_id: str):
        super().__init__(f"Evidence with ID {evidence_id} not found.")

class InvalidEvidenceError(CrisisPilotError):
    """Raised when evidence violates business rules (e.g., missing ownership)."""
    def __init__(self, detail: str = "Evidence must belong to at least one entity."):
        super().__init__(detail)
