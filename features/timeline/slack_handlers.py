import logging
from slack_bolt.async_app import AsyncApp
from infrastructure.database import get_db_session
from core.services import registry as service_registry
from core.state import StateManager
from infrastructure.slack_blocks import build_timeline_blocks

logger = logging.getLogger("crisispilot.timeline.slack_handlers")

def register_timeline_handlers(app: AsyncApp) -> None:
    
    @app.command("/timeline")
    @app.command("/operation-timeline")
    @app.command("/incident-timeline")
    async def view_timeline_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        entity_id = command.get("text", "").strip()
        cmd_name = command.get("command", "")
        
        if not entity_id:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Please provide an entity ID. Example: `{cmd_name} OP-1234`")
            return
            
        await _view_timeline(client, channel_id, user_id, entity_id)

    @app.action("global_view_timeline")
    async def handle_global_view_timeline(ack, body, client):
        await ack()
        val = body["actions"][0]["value"]
        entity_id = val.split("_")[1] # Value format: operation_OP-123
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]
        
        await _view_timeline(client, channel_id, user_id, entity_id)

    @app.action("timeline_view_history")
    async def handle_timeline_view_history(ack, body, client):
        await ack()
        entity_id = body["actions"][0]["value"] # Passes operation_id directly
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]
        
        await _view_timeline(client, channel_id, user_id, entity_id)

    async def _view_timeline(client, channel_id, user_id, entity_id):
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            # Since ID could be for any entity, we just use the timeline service to fetch by owner
            events = await state_manager.timeline_service.list_events_by_operation(session, entity_id)
            if not events:
                events = await state_manager.timeline_service.list_events_by_incident(session, entity_id)
            if not events:
                events = await state_manager.timeline_service.list_events_by_mission(session, entity_id)
            if not events:
                # One last try as workflow
                events = await state_manager.timeline_service.list_events_by_workflow(session, entity_id)
                
            blocks = build_timeline_blocks(entity_id, events)
            await client.chat_postMessage(channel=channel_id, text=f"Timeline: {entity_id}", blocks=blocks)
            
            await session.close()
        except Exception as e:
            logger.error(f"Error fetching timeline for {entity_id}: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Error fetching timeline: {e}")
