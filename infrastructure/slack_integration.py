import asyncio
import logging
from typing import Awaitable, Callable

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_bolt.request.async_request import AsyncBoltRequest
from slack_bolt.response import BoltResponse

from app.slack_setup import register_slack_handlers
from core.config import get_settings

logger = logging.getLogger("crisispilot.slack")

settings = get_settings()

# Initialize AsyncApp with tokens
slack_app = AsyncApp(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
)

# Register all modular handlers
register_slack_handlers(slack_app)

# Socket Mode handler will be initialized at runtime
handler: AsyncSocketModeHandler | None = None


@slack_app.middleware
async def log_request(
    logger: logging.Logger,
    req: AsyncBoltRequest,
    resp: BoltResponse,
    next: Callable[[], Awaitable[BoltResponse]],
):
    """
    Basic middleware for structured logging of incoming requests.
    """
    logger.debug(f"Incoming Slack request: type={req.body.get('type')} payload={req.body}")
    try:
        response = await next()
        return response
    except Exception as e:
        logger.error(f"Error processing Slack request: {e}", exc_info=True)
        raise


async def init_slack() -> None:
    """Connects to Slack via Socket Mode in the background."""
    global handler
    
    if not settings.SLACK_BOT_TOKEN or not settings.SLACK_APP_TOKEN:
        logger.error("Missing Slack tokens. Cannot start Slack Socket Mode.")
        return

    logger.info("Connecting to Slack via Socket Mode...")
    
    # Initialize the handler here where the asyncio event loop is running
    handler = AsyncSocketModeHandler(slack_app, settings.SLACK_APP_TOKEN)
    
    # Start Socket Mode in the background so it doesn't block FastAPI startup
    asyncio.create_task(handler.start_async())
    logger.info("Slack Socket Mode connection initiated.")


async def close_slack() -> None:
    """Disconnects gracefully from Slack Socket Mode."""
    global handler
    if handler:
        logger.info("Disconnecting Slack Socket Mode...")
        await handler.close_async()
        logger.info("Slack Socket Mode disconnected.")
