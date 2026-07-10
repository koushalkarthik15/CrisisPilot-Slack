import logging
from typing import Any, Dict, List, Optional

from core.errors import NotificationError
from features.incident_management.models import Incident
from features.recommendations.models import Recommendation
from features.workflow.domain import WorkflowEventPayload

logger = logging.getLogger("crisispilot.notifications")


class NotificationEngine:
    """
    Centralized communication orchestrator.
    Responsible for rate-limiting, deduplication, formatting, and dispatching to Slack.
    """
    def __init__(self, slack_client: Any):
        # slack_client is typed as Any to prevent hard coupling in type signatures,
        # but expects slack_bolt.async_app.AsyncApp.client
        self.client = slack_client
        self._initialized = False

    async def initialize(self) -> None:
        logger.info("Initializing Notification Engine...")
        self._initialized = True
        logger.info("Notification Engine operational.")

    async def shutdown(self) -> None:
        logger.info("Shutting down Notification Engine...")
        self._initialized = False

    async def dispatch_message(self, channel_id: str, text: str, blocks: Optional[List[Dict]] = None) -> bool:
        """
        Foundation interface: Sends a message to Slack.
        In the future, this will implement deduplication and alert thresholds.
        """
        if not self._initialized:
            raise NotificationError("Notification Engine is not initialized.")

        try:
            logger.debug(f"Dispatching notification to {channel_id}")
            response = await self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                blocks=blocks
            )
            return response["ts"]
        except Exception as e:
            logger.error(f"Failed to dispatch notification to {channel_id}: {e}")
            raise NotificationError(f"Slack API error: {e}") from e

    async def publish_operational_summary(self, blocks: list, channel_id: str) -> str:
        """
        Publishes an operational summary dashboard.
        """
        try:
            response = await self.client.chat_postMessage(
                channel=channel_id,
                text="CrisisPilot Operational Summary",
                blocks=blocks
            )
            return response["ts"]
        except Exception as e:
            logger.error(f"Failed to publish operational summary: {e}")
            raise NotificationError(f"Slack API error: {e}") from e

    async def dispatch_threaded_message(self, channel_id: str, thread_ts: str, text: str, blocks: Optional[List[Dict]] = None) -> str:
        """Sends a message to a specific thread in Slack."""
        if not self._initialized:
            raise NotificationError("Notification Engine is not initialized.")

        try:
            response = await self.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=text,
                blocks=blocks
            )
            return response["ts"]
        except Exception as e:
            logger.error(f"Failed to dispatch threaded notification to {channel_id}: {e}")
            raise NotificationError(f"Slack API error: {e}") from e

    async def dispatch_direct_message(self, user_id: str, text: str, blocks: Optional[List[Dict]] = None) -> str:
        """Sends a direct message to a specific user in Slack."""
        if not self._initialized:
            raise NotificationError("Notification Engine is not initialized.")

        try:
            dm = await self.client.conversations_open(users=user_id)
            dm_channel = dm["channel"]["id"]
            response = await self.client.chat_postMessage(
                channel=dm_channel,
                text=text,
                blocks=blocks
            )
            return response["ts"]
        except Exception as e:
            logger.error(f"Failed to dispatch direct message to user {user_id}: {e}")
            raise NotificationError(f"Slack API error: {e}") from e

    async def update_message(self, channel_id: str, ts: str, text: str, blocks: Optional[List[Dict]] = None) -> None:
        """Updates an existing message in Slack."""
        if not self._initialized:
            raise NotificationError("Notification Engine is not initialized.")

        try:
            await self.client.chat_update(
                channel=channel_id,
                ts=ts,
                text=text,
                blocks=blocks
            )
        except Exception as e:
            logger.error(f"Failed to update message {ts} in {channel_id}: {e}")
            raise NotificationError(f"Slack API error: {e}") from e

    def build_incident_card_blocks(self, incident: Incident) -> List[Dict]:
        """Builds a rich Block Kit incident card."""
        severity_emoji = {
            "CRITICAL": "🚨",
            "HIGH": "🔴",
            "MEDIUM": "🟠",
            "LOW": "🟡"
        }.get(incident.severity.name, "ℹ️")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} Incident: {incident.title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Severity:* {incident.severity.name} | *Status:* {incident.status.name}\n\n{incident.description}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Incident ID: `{incident.id}` | Declared at: {incident.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            },
            {"type": "divider"}
        ]

        if incident.status.name not in ["RESOLVED", "ARCHIVED"]:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Assign 👤", "emoji": True},
                        "value": incident.id,
                        "action_id": "incident_assign"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Resolve ✅", "emoji": True},
                        "style": "primary",
                        "value": incident.id,
                        "action_id": "incident_resolve"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Archive 🗄️", "emoji": True},
                        "value": incident.id,
                        "action_id": "incident_archive"
                    },
                    {
                        "type": "overflow",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Mark Duplicate", "emoji": True},
                                "value": f"duplicate_{incident.id}"
                            },
                            {
                                "text": {"type": "plain_text", "text": "Link to Operation 🔗", "emoji": True},
                                "value": f"linkop_{incident.id}"
                            },
                            {
                                "text": {"type": "plain_text", "text": "Link to Mission 🎯", "emoji": True},
                                "value": f"linkmiss_{incident.id}"
                            },
                            {
                                "text": {"type": "plain_text", "text": "Merge Incident", "emoji": True},
                                "value": f"merge_{incident.id}"
                            },
                            {
                                "text": {"type": "plain_text", "text": "Delete Incident 🗑️", "emoji": True},
                                "value": f"delete_{incident.id}"
                            }
                        ],
                        "action_id": "incident_more_actions"
                    }
                ]
            })

        return blocks

    async def publish_incident_created(self, incident: Incident, channel_id: str) -> str:
        """Publishes a rich Block Kit incident card to the specified channel and returns the thread_ts."""
        blocks = self.build_incident_card_blocks(incident)

        return await self.dispatch_message(
            channel_id=channel_id,
            text=f"Incident Declared: {incident.title}",
            blocks=blocks
        )

    async def publish_recommendation(self, recommendation: Recommendation, channel_id: str, thread_ts: Optional[str] = None) -> str:
        """Publishes a recommendation inside an incident thread with Approve/Reject interactive buttons."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"💡 *Recommendation: {recommendation.title}*\n\n{recommendation.description}\n\n*Rationale:* {recommendation.rationale}\n*Confidence:* {recommendation.confidence * 100:.1f}%"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve & Assign", "emoji": True},
                        "style": "primary",
                        "value": recommendation.id,
                        "action_id": "workflow_approve_assign"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject", "emoji": True},
                        "style": "danger",
                        "value": recommendation.id,
                        "action_id": "workflow_reject"
                    }
                ]
            }
        ]

        if thread_ts:
            return await self.dispatch_threaded_message(
                channel_id=channel_id,
                thread_ts=thread_ts,
                text=f"Recommendation: {recommendation.title}",
                blocks=blocks
            )
        else:
            return await self.dispatch_message(
                channel_id=channel_id,
                text=f"Recommendation: {recommendation.title}",
                blocks=blocks
            )
    async def publish_workflow_event(self, event: WorkflowEventPayload) -> None:
        """
        Transport-independent hook to broadcast workflow decisions.
        In the future, this will map to specific Slack threads or other integrations.
        """
        if not self._initialized:
            raise NotificationError("Notification Engine is not initialized.")

        logger.info(
            f"Workflow Event: Recommendation {event.recommendation_id} "
            f"was {event.action.value} by {event.reviewer_id}. Status: {event.status.value}"
        )
        # Dispatch logic to specific transports (e.g. Slack) will live here later.
