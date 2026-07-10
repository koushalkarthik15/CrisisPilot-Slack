from typing import Any, Dict, List

from features.recommendations.domain import RecommendationPriority
from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.base import BaseRecommendationProvider
from features.recommendations.providers.domain import ProviderResult


class NaturalDisasterProvider(BaseRecommendationProvider):
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        return [
            ProviderResult(
                title=f"Natural Disaster Response: {classification.threat_type}",
                summary="Immediate disaster response and evacuation protocols.",
                priority=RecommendationPriority.CRITICAL,
                immediate_actions=[
                    "Issue immediate evacuation orders if applicable.",
                    "Activate regional shelters and safe zones.",
                    "Issue public alerts."
                ],
                short_term_actions=[
                    "Deploy emergency resources and rescue coordination teams.",
                    "Establish emergency communications channels."
                ],
                long_term_actions=[
                    "Conduct structural integrity assessments.",
                    "Begin disaster recovery and rebuilding."
                ],
                escalation_guidance="Engage local government and national guard if resources are overwhelmed.",
                rationale=[f"Disaster type: {classification.threat_type}"],
                confidence=classification.confidence
            )
        ]
