from typing import Any, Dict, List

from features.recommendations.domain import RecommendationPriority
from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.base import BaseRecommendationProvider
from features.recommendations.providers.domain import ProviderResult


class WeatherProvider(BaseRecommendationProvider):
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        return [
            ProviderResult(
                title=f"Severe Weather Advisory: {classification.threat_type}",
                summary=f"Operational protocol for {classification.threat_type}.",
                priority=RecommendationPriority.MEDIUM,
                immediate_actions=[
                    "Monitor real-time weather forecasts.",
                    "Deploy weather advisories to affected field teams."
                ],
                short_term_actions=[
                    "Suspend outdoor and high-risk work in affected zones.",
                    "Secure loose equipment."
                ],
                long_term_actions=[
                    "Assess facility resilience for recurring weather events."
                ],
                escalation_guidance="If weather escalates to property-threatening levels, trigger Natural Disaster protocol.",
                rationale=[f"Weather event: {classification.threat_type}"],
                confidence=classification.confidence
            )
        ]
