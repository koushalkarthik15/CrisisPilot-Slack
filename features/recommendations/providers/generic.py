from typing import Dict, Any, List
from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.base import BaseRecommendationProvider
from features.recommendations.providers.domain import ProviderResult
from features.recommendations.domain import RecommendationPriority

class GenericProvider(BaseRecommendationProvider):
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        return [
            ProviderResult(
                title=f"General Incident Response: {classification.threat_type or 'Unknown'}",
                summary="Standard operating procedure for unspecified or unclassified incidents.",
                priority=RecommendationPriority.MEDIUM,
                immediate_actions=[
                    "Continue monitoring the situation.",
                    "Gather additional information to clarify the threat type."
                ],
                short_term_actions=[
                    "Notify on-call operators.",
                    "Establish a preliminary incident war room."
                ],
                long_term_actions=[
                    "Refine incident classification.",
                    "Update standard operating procedures."
                ],
                escalation_guidance="Escalate for human review to manually assess and classify the incident.",
                rationale=[
                    "Confidence was below threshold or domain is unclassified.",
                    f"Reported confidence: {classification.confidence}"
                ],
                confidence=classification.confidence
            )
        ]
