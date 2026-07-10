from abc import ABC, abstractmethod
from typing import Any, Dict, List

from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.domain import ProviderResult


class BaseRecommendationProvider(ABC):
    """
    Abstract interface for deterministic recommendation providers.
    """

    @abstractmethod
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        """
        Given the incident classification and context, return a list of structured ProviderResults.
        """
        pass
