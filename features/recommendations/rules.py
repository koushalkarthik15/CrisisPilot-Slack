from typing import Any, Dict, List

from features.recommendations.domain import (
    RecommendationPriority,
    RecommendationRuleResult,
)


class DeterministicRuleEngine:
    """
    Evaluates incident context and MCP outputs to produce structured recommendations
    using deterministic rules (mocking future LLM capabilities).
    """
    def evaluate(self, incident_context: Dict[str, Any], mcp_outputs: List[Dict[str, Any]]) -> List[RecommendationRuleResult]:
        results = []
        severity = incident_context.get("severity", "Low").upper()

        # Rule 1: High severity incident triggers rapid evacuation recommendation
        if severity in ["HIGH", "CRITICAL"]:
            results.append(
                RecommendationRuleResult(
                    title="Initiate Emergency Evacuation",
                    description="Immediately clear the impacted zone and redirect to safe shelters.",
                    priority=RecommendationPriority.CRITICAL if severity == "CRITICAL" else RecommendationPriority.HIGH,
                    confidence=0.92,
                    rationale=[
                        f"Incident severity is reported as {severity}.",
                        "Standard operating procedure for high-severity events requires immediate evacuation."
                    ]
                )
            )

        # Rule 2: Based on MCP context (e.g., Weather tool indicating rain)
        weather_data = next((output for output in mcp_outputs if "Weather in" in output.get("content", "")), None)
        if weather_data and "Rain" in weather_data.get("content", ""):
             results.append(
                RecommendationRuleResult(
                    title="Deploy Flood Mitigation Barriers",
                    description="Send logistics teams with sandbags and barriers to vulnerable sectors.",
                    priority=RecommendationPriority.MEDIUM,
                    confidence=0.85,
                    rationale=[
                        "Weather forecast indicates incoming rain.",
                        "Vulnerable sectors are at risk of flooding during heavy precipitation."
                    ]
                )
            )

        # Fallback Rule: Generic resource check
        if not results:
             results.append(
                RecommendationRuleResult(
                    title="Conduct Initial Resource Assessment",
                    description="Deploy scout teams to evaluate immediate needs on the ground.",
                    priority=RecommendationPriority.LOW,
                    confidence=0.75,
                    rationale=[
                        "Insufficient data to trigger specific high-priority protocols.",
                        "Standard protocol requires baseline assessment."
                    ]
                )
            )

        return results
