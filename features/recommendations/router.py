import logging
from typing import Dict

from core.config import get_settings
from features.recommendations.intelligence import IncidentDomainEnum
from features.recommendations.providers.base import BaseRecommendationProvider

logger = logging.getLogger("crisispilot.recommendations.router")

class RecommendationRouter:
    """
    Routes an IncidentClassification to the correct deterministic provider.
    Maintains a registry of domain -> Provider class.
    """
    def __init__(self):
        self._providers: Dict[IncidentDomainEnum, BaseRecommendationProvider] = {}
        self.settings = get_settings()

    def register(self, domain: IncidentDomainEnum, provider: BaseRecommendationProvider) -> None:
        self._providers[domain] = provider
        logger.info(f"Registered Recommendation Provider for domain: {domain.name}")

    def route(self, domain: IncidentDomainEnum, confidence: float) -> BaseRecommendationProvider:
        """
        Returns the appropriate provider based on domain and confidence.
        Falls back to GENERIC if confidence is too low or domain is unregistered.
        """
        threshold = self.settings.RECOMMENDATION_CONFIDENCE_THRESHOLD

        if confidence < threshold:
            logger.warning(f"Confidence {confidence} below threshold {threshold}. Routing to GENERIC provider.")
            return self._providers.get(IncidentDomainEnum.GENERIC)

        provider = self._providers.get(domain)
        if not provider:
            logger.warning(f"No provider registered for {domain.name}. Falling back to GENERIC.")
            return self._providers.get(IncidentDomainEnum.GENERIC)

        return provider
