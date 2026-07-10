from typing import Dict, Any, List
from features.recommendations.intelligence import IncidentClassification
from features.recommendations.providers.base import BaseRecommendationProvider
from features.recommendations.providers.domain import ProviderResult
from features.recommendations.domain import RecommendationPriority

class CybersecurityProvider(BaseRecommendationProvider):
    def generate(self, classification: IncidentClassification, incident_context: Dict[str, Any]) -> List[ProviderResult]:
        priority = RecommendationPriority.CRITICAL if classification.severity.value in ["high", "critical"] else RecommendationPriority.HIGH
        
        return [
            ProviderResult(
                title=f"Cybersecurity Response: {classification.threat_type}",
                summary=f"Automated playbook for handling {classification.threat_type} affecting {len(classification.affected_assets)} assets.",
                priority=priority,
                immediate_actions=[
                    "Isolate compromised hosts from the network immediately.",
                    "Rotate potentially compromised credentials."
                ],
                short_term_actions=[
                    "Enable enhanced logging and monitoring on perimeter defenses.",
                    "Notify SOC and incident response team."
                ],
                long_term_actions=[
                    "Patch affected systems with latest vendor updates.",
                    "Conduct post-incident forensic analysis."
                ],
                escalation_guidance="If lateral movement is detected, immediately escalate to CISO and activate full incident response plan.",
                rationale=[
                    f"Threat Type identified as {classification.threat_type}",
                    f"Severity assessed as {classification.severity.value}"
                ],
                confidence=classification.confidence
            )
        ]
