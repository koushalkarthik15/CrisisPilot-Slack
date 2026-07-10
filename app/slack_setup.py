import logging

from slack_bolt.async_app import AsyncApp

from features.analytics.slack_handlers import register_analytics_handlers
from features.archived.slack_handlers import register_archived_handlers
from features.evidence.slack_handlers import register_evidence_handlers
from features.incident_management.slack_handlers import register_incident_handlers
from features.mini_agents.slack_handlers import register_mini_agent_handlers
from features.missions.slack_handlers import register_mission_handlers
from features.monitoring.slack_handlers import register_monitoring_handlers
from features.operations.slack_handlers import register_operation_handlers
from features.timeline.slack_handlers import register_timeline_handlers
from features.workflow.slack_handlers import register_workflow_handlers
from features.workflows.slack_handlers import register_operational_workflow_handlers

logger = logging.getLogger("crisispilot.slack.handlers")


def register_slack_handlers(app: AsyncApp) -> None:
    """
    Modular registration of all Slack event and command handlers.
    In the future, this will import routers from feature modules.
    """

    @app.event("app_mention")
    async def handle_app_mention(event, say):
        """Foundation event handler verification."""
        logger.info(f"Received app_mention from {event.get('user')}")
        await say(f"CrisisPilot platform is operational. Acknowledged mention from <@{event.get('user')}>.")

    @app.command("/crisispilot-ping")
    async def handle_ping_command(ack, respond, command):
        """Foundation slash command framework verification."""
        await ack()
        logger.info(f"Received /crisispilot-ping command from {command.get('user_id')}")
        await respond("CrisisPilot platform is operational. The slash command framework is active.")

    # Register Mini-Agent Handlers
    register_mini_agent_handlers(app)

    # Register Incident & Workflow Handlers
    register_incident_handlers(app)
    register_workflow_handlers(app)

    # Register Analytics Handlers
    register_analytics_handlers(app)

    # Register Active Operations Handlers
    register_operation_handlers(app)
    register_mission_handlers(app)
    register_operational_workflow_handlers(app)
    register_timeline_handlers(app)
    register_evidence_handlers(app)
    register_monitoring_handlers(app)
    register_archived_handlers(app)

    @app.action("global_update_status")
    async def handle_global_update_status(ack, body, client):
        await ack()
        val = body["actions"][0]["value"]
        entity_type, entity_id = val.split("_", 1)
        channel_id = body["channel"]["id"]

        try:
            options = []
            if entity_type == "mission":
                from features.missions.domain import MissionStatus
                options = [{"text": {"type": "plain_text", "text": s.name}, "value": s.name} for s in MissionStatus]
            elif entity_type == "operation":
                from features.operations.domain import OperationStatus
                options = [{"text": {"type": "plain_text", "text": s.name}, "value": s.name} for s in OperationStatus]
            elif entity_type == "workflow":
                from features.workflows.domain import WorkflowStatus
                options = [{"text": {"type": "plain_text", "text": s.name}, "value": s.name} for s in WorkflowStatus]
            elif entity_type == "incident":
                from features.incident_management.domain import IncidentStatus
                options = [{"text": {"type": "plain_text", "text": s.name}, "value": s.name} for s in IncidentStatus]

            if not options:
                await client.chat_postEphemeral(channel=channel_id, user=body["user"]["id"], text=f"Status updates not supported for {entity_type}.")
                return

            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "global_update_status_modal",
                    "private_metadata": f"{channel_id}|{entity_type}|{entity_id}",
                    "title": {"type": "plain_text", "text": "Update Status"},
                    "submit": {"type": "plain_text", "text": "Update"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "status_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select new status"},
                                "options": options,
                                "action_id": "status_input"
                            },
                            "label": {"type": "plain_text", "text": "New Status"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening update status modal: {e}", exc_info=True)

    @app.view("global_update_status_modal")
    async def handle_global_update_status_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        channel_id = meta[0]
        entity_type = meta[1]
        entity_id = meta[2]

        status_str = values["status_block"]["status_input"]["selected_option"]["value"]

        await ack()

        try:
            from core.services import registry as service_registry
            from core.state import StateManager
            from infrastructure.database import get_db_session

            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            if entity_type == "mission":
                from features.missions.domain import MissionStatus
                from infrastructure.slack_blocks.mission_blocks import (
                    build_mission_detail_blocks,
                )
                new_status = MissionStatus[status_str]
                updated = await state_manager.transition_mission_status(session, entity_id, new_status)
                await session.commit()
                blocks = build_mission_detail_blocks(updated)
                await client.chat_postMessage(channel=channel_id, text=f"Mission status updated: {updated.name}", blocks=blocks)

            elif entity_type == "operation":
                from features.operations.domain import OperationStatus
                from infrastructure.slack_blocks.operation_blocks import (
                    build_operation_detail_blocks,
                )
                new_status = OperationStatus[status_str]
                updated = await state_manager.transition_operation_status(session, entity_id, new_status)
                await session.commit()
                blocks = build_operation_detail_blocks(updated)
                await client.chat_postMessage(channel=channel_id, text=f"Operation status updated: {updated.name}", blocks=blocks)

            elif entity_type == "workflow":
                from features.workflows.domain import WorkflowStatus
                from infrastructure.slack_blocks.workflow_blocks import (
                    build_workflow_detail_blocks,
                )
                new_status = WorkflowStatus[status_str]
                updated = await state_manager.transition_operational_workflow_status(session, entity_id, new_status)
                await session.commit()
                blocks = build_workflow_detail_blocks(updated)
                await client.chat_postMessage(channel=channel_id, text=f"Workflow status updated: {updated.name}", blocks=blocks)

            elif entity_type == "incident":
                from features.incident_management.domain import IncidentStatus
                new_status = IncidentStatus[status_str]
                user_id = body["user"]["id"]
                updated = await state_manager.transition_incident_status(session, entity_id, new_status, user_id)
                await session.commit()
                await client.chat_postMessage(channel=channel_id, text=f"Incident `{entity_id}` status updated to {new_status.name}")

            await session.close()
        except Exception as e:
            logger.error(f"Error updating status: {e}", exc_info=True)
            await client.chat_postMessage(channel=channel_id, text=f"Failed to update status: {e}")

    logger.info("Slack event and command handlers registered successfully.")
