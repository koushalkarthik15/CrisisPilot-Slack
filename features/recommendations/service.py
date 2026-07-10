import logging
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from features.recommendations.intelligence import IncidentIntelligenceService
from features.recommendations.models import Recommendation
from features.recommendations.providers.domain import ProviderResult
from features.recommendations.repository import RecommendationRepository
from features.recommendations.router import RecommendationRouter
from features.recommendations.schemas import RecommendationCreate

logger = logging.getLogger("crisispilot.recommendations.service")


class RecommendationService:
    """
    Orchestrates the new domain-aware recommendation lifecycle.
    Classifies incidents using LLM, routes to a deterministic provider, and persists the results.
    """
    def __init__(self, repository: RecommendationRepository, intelligence_service: IncidentIntelligenceService, router: RecommendationRouter):
        self.repository = repository
        self.intelligence = intelligence_service
        self.router = router

    def _format_markdown_description(self, result: ProviderResult) -> str:
        """Formats the structured provider result into a rich markdown string for the database."""

        def format_list(items: List[str]) -> str:
            if not items:
                return "None"
            return "\n".join([f"- {item}" for item in items])

        return (
            f"{result.summary}\n\n"
            f"**Immediate Actions**\n{format_list(result.immediate_actions)}\n\n"
            f"**Short-Term Actions**\n{format_list(result.short_term_actions)}\n\n"
            f"**Long-Term Actions**\n{format_list(result.long_term_actions)}\n\n"
            f"**Escalation Guidance**\n{result.escalation_guidance}"
        )

    async def generate_recommendations(self, db: AsyncSession, context: Dict[str, Any], mcp_outputs: List[Dict[str, Any]]) -> List[Recommendation]:
        incident_id = context.get("incident_id") or context.get("id") if "incident_id" not in context and "operation_id" not in context else context.get("incident_id")
        operation_id = context.get("operation_id")
        title = context.get("title", "")
        description = context.get("description", "")

        if not incident_id and not operation_id:
            raise ValueError("context must contain an 'incident_id' or 'operation_id'.")

        logger.info("Classifying situation for recommendations...")

        # 1. Classify the incident using LLM
        classification = await self.intelligence.classify_incident(title, description)

        logger.info(
            f"Incident {incident_id} classified as {classification.domain.name} "
            f"({classification.threat_type}) with confidence {classification.confidence}"
        )

        # 2. Route to the appropriate provider
        provider = self.router.route(classification.domain, classification.confidence)
        logger.info(f"Routing to provider: {provider.__class__.__name__}")

        # 3. Ask provider for deterministic results
        results: List[ProviderResult] = provider.generate(classification, context)

        # 4. Persist as immutable recommendations
        created_recs = []
        for result in results:
            formatted_description = self._format_markdown_description(result)

            create_schema = RecommendationCreate(
                incident_id=incident_id,
                operation_id=operation_id,
                title=result.title,
                description=formatted_description,
                priority=result.priority,
                confidence=result.confidence,
                rationale=result.rationale
            )
            rec = await self.repository.create(db, obj_in=create_schema)
            created_recs.append(rec)
            logger.info(f"Generated recommendation {rec.id}: {rec.title} (Confidence: {rec.confidence})")

        return created_recs

    async def get_by_incident(self, db: AsyncSession, incident_id: str) -> List[Recommendation]:
        return await self.repository.get_by_incident_id(db, incident_id)
