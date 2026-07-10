import logging
from features.mini_agents.models import MiniAgentModel
from features.mini_agents.intelligent_agent import IntelligentMiniAgent
from core.orchestration.base import BaseAgent

logger = logging.getLogger("crisispilot.mini_agents.factory")

class MiniAgentFactory:
    """
    Responsible for converting persisted MiniAgentModel instances into runtime BaseAgent implementations.
    """
    @staticmethod
    def create_agent(model: MiniAgentModel) -> BaseAgent:
        logger.debug(f"Factory constructing agent from model: {model.name}")
        
        # Currently, all dynamic agents map to the IntelligentMiniAgent.
        # The default global LLM provider is used (so model.llm_provider/model_name/temp are logged but ignored for instantiation in MS 4.5).
        # We pass the schema attributes to the agent instance.
        
        agent = IntelligentMiniAgent(
            name=model.name,
            description=model.description,
            system_prompt=model.system_prompt,
            allowed_tools=model.allowed_tools
        )
        return agent
