import logging

from slack_bolt.async_app import AsyncApp

from core.services import registry as service_registry
from core.state import StateManager
from infrastructure.database import get_db_session
from infrastructure.slack_blocks import build_evidence_blocks

logger = logging.getLogger("crisispilot.evidence.slack_handlers")

def register_evidence_handlers(app: AsyncApp) -> None:

    @app.command("/evidence")
    @app.command("/operation-evidence")
    async def view_evidence_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        entity_id = command.get("text", "").strip()
        cmd_name = command.get("command", "")

        if not entity_id:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Please provide an entity ID. Example: `{cmd_name} OP-1234`")
            return

        await _view_evidence(client, channel_id, user_id, entity_id)

    @app.action("global_view_evidence")
    async def handle_global_view_evidence(ack, body, client):
        await ack()
        val = body["actions"][0]["value"]
        entity_id = val.split("_")[1] # Value format: operation_OP-123
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]

        await _view_evidence(client, channel_id, user_id, entity_id)

    async def _view_evidence(client, channel_id, user_id, entity_id):
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            # Fetch by owner
            evidence_list = await state_manager.evidence_service.list_evidence_by_operation(session, entity_id)
            if not evidence_list:
                evidence_list = await state_manager.evidence_service.list_evidence_by_incident(session, entity_id)
            if not evidence_list:
                evidence_list = await state_manager.evidence_service.list_evidence_by_mission(session, entity_id)

            blocks = build_evidence_blocks(entity_id, evidence_list)
            await client.chat_postMessage(channel=channel_id, text=f"Evidence: {entity_id}", blocks=blocks)

            await session.close()
        except Exception as e:
            logger.error(f"Error fetching evidence for {entity_id}: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Error fetching evidence: {e}")

    @app.action("global_add_evidence")
    async def handle_global_add_evidence_action(ack, body, client):
        await ack()
        val = body["actions"][0]["value"]
        parts = val.split("_")
        entity_type = parts[0]
        entity_id = parts[1]

        # Depending on entity type, we assign it to the right metadata field
        mission_id = entity_id if entity_type == "mission" else ""
        operation_id = entity_id if entity_type == "operation" else ""
        incident_id = entity_id if entity_type == "incident" else ""
        channel_id = body["channel"]["id"]

        try:
            from features.evidence.domain import EvidenceType
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "add_evidence_modal",
                    "private_metadata": f"{channel_id}|{mission_id}|{operation_id}|{incident_id}",
                    "title": {"type": "plain_text", "text": "Add Evidence"},
                    "submit": {"type": "plain_text", "text": "Submit"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "title_block",
                            "element": {"type": "plain_text_input", "action_id": "title_input"},
                            "label": {"type": "plain_text", "text": "Title"}
                        },
                        {
                            "type": "input",
                            "block_id": "desc_block",
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "desc_input"},
                            "label": {"type": "plain_text", "text": "Description"}
                        },
                        {
                            "type": "input",
                            "block_id": "type_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select evidence type"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": e.name}, "value": e.name}
                                    for e in EvidenceType
                                ],
                                "action_id": "type_input"
                            },
                            "label": {"type": "plain_text", "text": "Type"}
                        },
                        {
                            "type": "input",
                            "block_id": "content_block",
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "content_input"},
                            "label": {"type": "plain_text", "text": "Content / URL / Data"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening add evidence modal: {e}", exc_info=True)

    @app.command("/add-evidence")
    async def add_evidence_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        mission_id = command.get("text", "").strip()

        if not mission_id:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text="Please provide a mission or operation ID. Example: `/add-evidence MS-123`")
            return

        try:
            from features.evidence.domain import EvidenceType
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "add_evidence_modal",
                    "private_metadata": f"{channel_id}|{mission_id}|",
                    "title": {"type": "plain_text", "text": "Add Evidence"},
                    "submit": {"type": "plain_text", "text": "Submit"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "title_block",
                            "element": {"type": "plain_text_input", "action_id": "title_input"},
                            "label": {"type": "plain_text", "text": "Title"}
                        },
                        {
                            "type": "input",
                            "block_id": "desc_block",
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "desc_input"},
                            "label": {"type": "plain_text", "text": "Description"}
                        },
                        {
                            "type": "input",
                            "block_id": "type_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select evidence type"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": e.name}, "value": e.name}
                                    for e in EvidenceType
                                ],
                                "action_id": "type_input"
                            },
                            "label": {"type": "plain_text", "text": "Type"}
                        },
                        {
                            "type": "input",
                            "block_id": "content_block",
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "content_input"},
                            "label": {"type": "plain_text", "text": "Content / URL / Data"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening add evidence modal from command: {e}", exc_info=True)

    @app.view("add_evidence_modal")
    async def handle_add_evidence_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        channel_id = meta[0]
        mission_id = meta[1] if len(meta) > 1 and meta[1] else None
        operation_id = meta[2] if len(meta) > 2 and meta[2] else None
        incident_id = meta[3] if len(meta) > 3 and meta[3] else None
        user_id = body["user"]["id"]

        title = values["title_block"]["title_input"]["value"]
        desc = values["desc_block"]["desc_input"]["value"]
        ev_type = values["type_block"]["type_input"]["selected_option"]["value"]
        content = values["content_block"]["content_input"]["value"]

        await ack()

        try:
            from features.evidence.domain import EvidenceType
            from features.evidence.schemas import EvidenceCreate

            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            ev_in = EvidenceCreate(
                title=title,
                description=desc,
                source="Manual Entry",
                evidence_type=EvidenceType[ev_type],
                content=content,
                confidence_score=1.0,
                mission_id=mission_id,
                operation_id=operation_id,
                incident_id=incident_id
            )

            evidence = await state_manager.create_evidence(session, ev_in, user_id)
            await session.commit()

            await client.chat_postMessage(channel=channel_id, text=f"Evidence added successfully: *{title}*")
            await session.close()
        except Exception as e:
            logger.error(f"Error saving evidence: {e}", exc_info=True)
