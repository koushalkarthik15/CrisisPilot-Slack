import logging
import sys
from core.config import get_settings


def setup_logging() -> None:
    """
    Configures structured logging for the application.
    """
    settings = get_settings()
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Basic configuration for structured logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Reduce noise from external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logger = logging.getLogger("crisispilot")
    logger.info(f"Logging initialized at level: {settings.LOG_LEVEL}")
