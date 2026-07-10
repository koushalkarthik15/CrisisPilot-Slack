class RecommendationEngineError(Exception):
    """Base exception for all Recommendation Engine errors."""
    pass

class RecommendationNotFoundError(RecommendationEngineError):
    """Raised when a recommendation cannot be found in the repository."""
    pass

class RecommendationImmutableError(RecommendationEngineError):
    """Raised when attempting to modify an immutable field of a recommendation."""
    def __init__(self, field_name: str):
        super().__init__(f"Cannot modify immutable field '{field_name}'. Only status and review metadata may be updated.")
