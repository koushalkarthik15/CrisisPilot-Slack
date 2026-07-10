from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration management for CrisisPilot.
    Loads settings from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application settings
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Slack Configuration
    SLACK_BOT_TOKEN: str = Field(default="")
    SLACK_SIGNING_SECRET: str = Field(default="")
    SLACK_APP_TOKEN: str = Field(default="")

    OPENAI_API_KEY: str = Field(default="")
    NEWS_API_KEY: str = Field(default="")
    OPENWEATHER_API_KEY: str = Field(default="")

    # Watchlist Monitoring
    NEWS_POLLING_INTERVAL_SECONDS: int = Field(default=300)

    # Operational Summaries
    OPS_SUMMARY_ENABLED: bool = Field(default=True)
    OPS_SUMMARY_INTERVAL_SECONDS: int = Field(default=86400) # 24 hours
    OPS_SUMMARY_CHANNEL_ID: str = Field(default="YOUR_CHANNEL_ID_HERE")

    # LLM & Groq Configuration
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    LLM_PROVIDER: str = Field(default="groq")

    # LLM Usage Guardrails
    LLM_GUARDRAILS_ENABLED: bool = Field(default=True)

    # Hit-In-The-Loop Workflow
    HITL_WORKFLOW_ENABLED: bool = Field(default=True)
    RECOMMENDATION_CONFIDENCE_THRESHOLD: float = Field(default=0.60)
    LLM_MAX_REQUESTS_PER_DAY: int = Field(default=500)
    LLM_MAX_TOKENS_PER_DAY: int = Field(default=500000)
    LLM_MAX_REQUESTS_PER_MINUTE: int = Field(default=20)
    LLM_MAX_CONCURRENT_REQUESTS: int = Field(default=2)

    # Database Configuration
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./storage/crisispilot.db")


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached instance of the settings."""
    return Settings()
