from typing import Any, Dict, List

from features.recommendations.domain import RecommendationPriority
from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.base import BaseRecommendationProvider
from features.recommendations.providers.domain import ProviderResult


class EnvironmentalProvider(BaseRecommendationProvider):
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        return [
            ProviderResult(
                title=f"Environmental Alert: {classification.threat_type}",
                summary="Environmental containment and remediation plan.",
                priority=RecommendationPriority.HIGH,
                immediate_actions=[
                    "Conduct immediate environmental assessment.",
                    "Initiate hazard containment procedures."
                ],
                short_term_actions=[
                    "Notify environmental regulatory agencies.",
                    "Deploy cleanup teams to affected area."
                ],
                long_term_actions=[
                    "Conduct long-term ecological impact study.",
                    "Implement preventive measures to avoid recurrence."
                ],
                escalation_guidance="Escalate to federal EPA or equivalent if contamination spreads beyond containment lines.",
                rationale=[f"Environmental hazard: {classification.threat_type}"],
                confidence=classification.confidence
            )
        ]
