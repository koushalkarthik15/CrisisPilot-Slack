import logging
from typing import Any, Dict, List, Tuple

from features.monitoring.domain import SituationState

logger = logging.getLogger("crisispilot.monitoring.evaluator")

class SituationEvaluator:
    """
    Evaluates monitoring observations to determine risk score and situation state.
    Rule-based implementation.
    """

    def evaluate(self, observations: List[Dict[str, Any]], risk_threshold: float) -> Tuple[SituationState, float]:
        """
        Evaluate risk based on a list of mocked observations.
        Returns (SituationState, risk_score).
        """
        if not observations:
            return SituationState.NORMAL, 0.0

        # Simplified rule-based aggregation: average of mock severity scores (0-100)
        total_severity = 0.0
        max_severity = 0.0

        for obs in observations:
            sev = float(obs.get("severity", 0.0))
            total_severity += sev
            if sev > max_severity:
                max_severity = sev

        # Risk score is a weighted blend of average and max severity to highlight spikes
        avg_severity = total_severity / len(observations)
        risk_score = (avg_severity * 0.4) + (max_severity * 0.6)

        # Determine Situation State based on risk score thresholds
        state = SituationState.NORMAL
        if risk_score >= risk_threshold:
            state = SituationState.CRITICAL
        elif risk_score >= (risk_threshold * 0.8):
            state = SituationState.WARNING
        elif risk_score >= (risk_threshold * 0.5):
            state = SituationState.WATCH

        return state, risk_score
