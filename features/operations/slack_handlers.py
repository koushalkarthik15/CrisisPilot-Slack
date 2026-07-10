import logging
from slack_bolt.async_app import AsyncApp
from infrastructure.database import get_db_session
from core.services import registry as service_registry
from core.state import StateManager
from infrastructure.slack_blocks import build_operation_list_blocks, build_operation_detail_blocks
from features.operations.schemas import OperationCreate
from features.operations.domain import OperationCategory

logger = logging.getLogger("crisispilot.operations.slack_handlers")

def register_operation_handlers(app: AsyncApp) -> None:
    
    @app.command("/operations")
    @app.command("/list-operations")
    async def list_operations_command(ack, body, client):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        logger.info(f"Received /operations command from {user_id}")
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            state_manager = service_registry.get(StateManager)
            # Just grab recent operations
            operations = await state_manager.operation_service.list_active_operations(session)
            
            blocks = build_operation_list_blocks(operations)
            await client.chat_postMessage(channel=channel_id, text="Active Operations", blocks=blocks)
            
            await session.close()
        except Exception as e:
            logger.error(f"Error listing operations: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Error listing operations: {e}")

    @app.command("/operation")
    async def view_operation_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        op_id = command.get("text", "").strip()
        
        if not op_id:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text="Please provide an operation ID. Example: `/operation OP-1234`")
            return
            
        logger.info(f"Received /operation command for {op_id} from {user_id}")
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            operation = await state_manager.operation_service.get_operation(session, op_id)
            if not operation:
                await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Operation `{op_id}` not found.")
                await session.close()
                return
                
            stats = {
                "active_incidents": 0, # Mocks for now
                "active_missions": 0,
                "active_workflows": 0,
                "timeline_events": 0
            }
            
            blocks = build_operation_detail_blocks(operation, stats)
            await client.chat_postMessage(channel=channel_id, text=f"Operation Dashboard: {operation.name}", blocks=blocks)
            
            await session.close()
        except Exception as e:
            logger.error(f"Error viewing operation {op_id}: {e}", exc_info=True)

    @app.command("/create-operation")
    async def create_operation_command(ack, body, client):
        await ack()
        try:
            channel_id = body.get("channel_id")
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "create_operation_modal",
                    "private_metadata": channel_id,
                    "title": {"type": "plain_text", "text": "Create Operation"},
                    "submit": {"type": "plain_text", "text": "Create"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "name_block",
                            "element": {"type": "plain_text_input", "action_id": "name_input"},
                            "label": {"type": "plain_text", "text": "Operation Name"}
                        },
                        {
                            "type": "input",
                            "block_id": "category_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select category"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": cat.name}, "value": cat.name}
                                    for cat in OperationCategory
                                ],
                                "action_id": "category_input"
                            },
                            "label": {"type": "plain_text", "text": "Category"}
                        },
                        {
                            "type": "input",
                            "block_id": "desc_block",
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "desc_input"},
                            "label": {"type": "plain_text", "text": "Description"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening create operation modal: {e}")

    @app.view("create_operation_modal")
    async def handle_create_operation_submission(ack, body, view, client):
        values = view["state"]["values"]
        channel_id = view["private_metadata"]
        user_id = body["user"]["id"]
        
        name = values["name_block"]["name_input"]["value"]
        category_str = values["category_block"]["category_input"]["selected_option"]["value"]
        desc = values["desc_block"]["desc_input"]["value"]

        await ack()

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            op_in = OperationCreate(
                name=name,
                description=desc,
                category=OperationCategory[category_str]
            )
            
            operation = await state_manager.create_operation(session, op_in, created_by=user_id)
            await session.commit()
            
            stats = {"active_incidents": 0, "active_missions": 0, "active_workflows": 0, "timeline_events": 0}
            blocks = build_operation_detail_blocks(operation, stats)
            
            await client.chat_postMessage(
                channel=channel_id,
                text=f"Operation created: {operation.name}",
                blocks=blocks
            )
            
            await session.close()
        except Exception as e:
            logger.error(f"Error submitting operation modal: {e}", exc_info=True)
            
    @app.action("op_view_dashboard")
    async def handle_op_view_dashboard(ack, body, client):
        await ack()
        op_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            operation = await state_manager.operation_service.get_operation(session, op_id)
            if operation:
                stats = {"active_incidents": 0, "active_missions": 0, "active_workflows": 0, "timeline_events": 0}
                blocks = build_operation_detail_blocks(operation, stats)
                await client.chat_postMessage(channel=channel_id, text=f"Operation Dashboard: {operation.name}", blocks=blocks)
                
            await session.close()
        except Exception as e:
            logger.error(f"Error showing operation dashboard: {e}", exc_info=True)
