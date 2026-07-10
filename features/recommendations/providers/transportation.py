from typing import Any, Dict, List

from features.recommendations.domain import RecommendationPriority
from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.base import BaseRecommendationProvider
from features.recommendations.providers.domain import ProviderResult


class TransportationProvider(BaseRecommendationProvider):
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        return [
            ProviderResult(
                title=f"Transportation Disruption: {classification.threat_type}",
                summary="Logistics and routing contingency plan.",
                priority=RecommendationPriority.MEDIUM,
                immediate_actions=[
                    "Implement immediate route diversion.",
                    "Broadcast passenger notifications."
                ],
                short_term_actions=[
                    "Coordinate alternative logistics.",
                    "Engage traffic management authorities."
                ],
                long_term_actions=[
                    "Review transportation resilience."
                ],
                escalation_guidance="If supply chain is severed, alert federal transportation agencies.",
                rationale=[f"Transportation event: {classification.threat_type}"],
                confidence=classification.confidence
            )
        ]
