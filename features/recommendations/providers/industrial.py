from typing import Any, Dict, List

from features.recommendations.domain import RecommendationPriority
from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.base import BaseRecommendationProvider
from features.recommendations.providers.domain import ProviderResult


class IndustrialProvider(BaseRecommendationProvider):
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        return [
            ProviderResult(
                title=f"Industrial Incident: {classification.threat_type}",
                summary="Hazard containment and site safety protocol.",
                priority=RecommendationPriority.HIGH,
                immediate_actions=[
                    "Execute emergency shutdown of affected systems.",
                    "Isolate hazardous areas immediately."
                ],
                short_term_actions=[
                    "Deploy HAZMAT response teams if applicable.",
                    "Perform headcount and evacuation of site."
                ],
                long_term_actions=[
                    "Conduct safety audit.",
                    "Implement new safety controls."
                ],
                escalation_guidance="Escalate to environmental regulators if contamination breaches site perimeter.",
                rationale=[f"Industrial threat: {classification.threat_type}"],
                confidence=classification.confidence
            )
        ]
