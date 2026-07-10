import logging
from slack_bolt.async_app import AsyncApp
from infrastructure.database import get_db_session
from features.analytics.service import AnalyticsService
from features.analytics.formatter import format_operational_summary_blocks
from core.llm.guardrails import UsageGuardrail
from core.notifications import NotificationEngine
from core.services import registry

logger = logging.getLogger("crisispilot.analytics.slack_handlers")

def register_analytics_handlers(app: AsyncApp) -> None:
    @app.command("/ops-summary")
    async def handle_ops_summary(ack, body, client):
        await ack()
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            metrics_provider = registry.get(UsageGuardrail)
            svc = AnalyticsService(metrics_provider)
            summary = await svc.get_operational_summary(session)
            blocks = format_operational_summary_blocks(summary)
            
            await session.close()
            
            await client.chat_postEphemeral(
                channel=body["channel_id"],
                user=body["user_id"],
                text="CrisisPilot Operational Summary",
                blocks=blocks
            )
        except Exception as e:
            logger.error(f"Error fetching ops summary: {e}", exc_info=True)
            await client.chat_postEphemeral(
                channel=body["channel_id"],
                user=body["user_id"],
                text="Failed to generate operational summary."
            )

    @app.command("/daily-summary")
    async def handle_daily_summary(ack, body, client):
        await ack()
        try:
            notification_engine = registry.get(NotificationEngine)
            
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            metrics_provider = registry.get(UsageGuardrail)
            svc = AnalyticsService(metrics_provider)
            summary = await svc.get_operational_summary(session)
            blocks = format_operational_summary_blocks(summary)
            
            await session.close()
            
            # Send via Notification Engine directly to the channel
            channel_id = body["channel_id"]
            await notification_engine.publish_operational_summary(blocks, channel_id)
            
        except Exception as e:
            logger.error(f"Error broadcasting daily summary: {e}", exc_info=True)
            await client.chat_postEphemeral(
                channel=body["channel_id"],
                user=body["user_id"],
                text="Failed to broadcast daily summary."
            )
