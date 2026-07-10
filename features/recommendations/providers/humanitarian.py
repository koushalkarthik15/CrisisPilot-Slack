from typing import Any, Dict, List

from features.recommendations.domain import RecommendationPriority
from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.base import BaseRecommendationProvider
from features.recommendations.providers.domain import ProviderResult


class HumanitarianProvider(BaseRecommendationProvider):
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        return [
            ProviderResult(
                title=f"Humanitarian Crisis: {classification.threat_type}",
                summary="Resource distribution and aid coordination.",
                priority=RecommendationPriority.HIGH,
                immediate_actions=[
                    "Coordinate with active NGOs in the sector.",
                    "Prioritize emergency resource distribution (water, food)."
                ],
                short_term_actions=[
                    "Establish temporary shelters.",
                    "Deploy medical support teams."
                ],
                long_term_actions=[
                    "Develop sustainable supply chain for aid.",
                    "Facilitate repatriation or resettlement programs."
                ],
                escalation_guidance="Alert international humanitarian agencies if demand exceeds local NGO capacity.",
                rationale=[f"Humanitarian event: {classification.threat_type}"],
                confidence=classification.confidence
            )
        ]
