import json
import logging
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from core.llm.models import LLMRequest
from core.llm.base import BaseLLMProvider

logger = logging.getLogger("crisispilot.recommendations.intelligence")

class IncidentDomainEnum(str, Enum):
    CYBERSECURITY = "cybersecurity"
    WEATHER = "weather"
    NATURAL_DISASTER = "natural_disaster"
    PUBLIC_HEALTH = "public_health"
    INFRASTRUCTURE = "infrastructure"
    TRANSPORTATION = "transportation"
    INDUSTRIAL = "industrial"
    HUMANITARIAN = "humanitarian"
    ENVIRONMENTAL = "environmental"
    GENERIC = "generic"

class UrgencyEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentClassification(BaseModel):
    domain: IncidentDomainEnum = Field(description="The primary operational domain of the incident.")
    subcategory: str = Field(description="The specific subcategory (e.g. patch_management, hurricane).")
    incident_type: str = Field(description="The generic type of incident.")
    threat_type: str = Field(description="The specific threat or vector.")
    severity: UrgencyEnum = Field(description="Assessed severity.")
    urgency: UrgencyEnum = Field(description="Assessed urgency for response.")
    affected_assets: List[str] = Field(description="List of systems, areas, or populations affected.")
    keywords: List[str] = Field(description="Important keywords extracted from the incident.")
    recommended_provider: IncidentDomainEnum = Field(description="The deterministic provider that should handle this incident.")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0.")

class IncidentIntelligenceService:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider

    async def classify_incident(self, incident_title: str, incident_description: str) -> IncidentClassification:
        schema_json = IncidentClassification.model_json_schema()
        
        prompt = f"""
        Classify the following incident and output ONLY valid JSON matching the schema below.
        
        Incident Title: {incident_title}
        Incident Description: {incident_description}
        
        JSON Schema:
        {json.dumps(schema_json, indent=2)}
        """
        
        request = LLMRequest(
            prompt=prompt,
            response_format={"type": "json_object"},
            system_prompt="You are an expert incident classification system. Your only job is to output structured JSON matching the provided schema exactly. Do not include markdown formatting, backticks, or extra text. Output RAW JSON.",
            max_tokens=800
        )
        
        response = await self.llm_provider.generate(request)
        try:
            raw_text = response.content.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()
                
            parsed = json.loads(raw_text)
            return IncidentClassification(**parsed)
        except Exception as e:
            logger.error(f"Failed to parse LLM classification: {e}")
            logger.debug(f"Raw output: {response.content}")
            return IncidentClassification(
                domain=IncidentDomainEnum.GENERIC,
                subcategory="unknown",
                incident_type="unknown",
                threat_type="unknown",
                severity=UrgencyEnum.MEDIUM,
                urgency=UrgencyEnum.MEDIUM,
                affected_assets=[],
                keywords=[],
                recommended_provider=IncidentDomainEnum.GENERIC,
                confidence=0.0
            )
