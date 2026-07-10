import logging
from slack_bolt.async_app import AsyncApp
from infrastructure.database import get_db_session
from core.services import registry as service_registry
from core.state import StateManager
from infrastructure.slack_blocks import build_workflow_list_blocks, build_workflow_detail_blocks

logger = logging.getLogger("crisispilot.workflows.slack_handlers")

def register_operational_workflow_handlers(app: AsyncApp) -> None:
    
    @app.command("/workflows")
    @app.command("/list-workflows")
    async def list_workflows_command(ack, body, client):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            # Use repository to fetch recently created workflows
            from sqlalchemy.future import select
            from features.workflows.models import Workflow
            result = await session.execute(select(Workflow).order_by(Workflow.created_at.desc()).limit(20))
            workflows = list(result.scalars().all())
            
            blocks = build_workflow_list_blocks(workflows)
            await client.chat_postMessage(channel=channel_id, text="Active Operational Workflows", blocks=blocks)
            
            await session.close()
        except Exception as e:
            logger.error(f"Error listing workflows: {e}", exc_info=True)

    @app.command("/workflow")
    async def view_workflow_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        workflow_id = command.get("text", "").strip()
        
        if not workflow_id:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text="Please provide a workflow ID. Example: `/workflow WF-1234`")
            return
            
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            workflow = await state_manager.operational_workflow_service.get_workflow(session, workflow_id)
            if not workflow:
                await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Workflow `{workflow_id}` not found.")
                await session.close()
                return
                
            blocks = build_workflow_detail_blocks(workflow)
            await client.chat_postMessage(channel=channel_id, text=f"Workflow Dashboard: {workflow.name}", blocks=blocks)
            
            await session.close()
        except Exception as e:
            logger.error(f"Error viewing workflow {workflow_id}: {e}", exc_info=True)

    @app.action("workflow_view_details")
    async def handle_workflow_view_details(ack, body, client):
        await ack()
        workflow_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            workflow = await state_manager.operational_workflow_service.get_workflow(session, workflow_id)
            if workflow:
                blocks = build_workflow_detail_blocks(workflow)
                await client.chat_postMessage(channel=channel_id, text=f"Workflow Dashboard: {workflow.name}", blocks=blocks)
                
            await session.close()
        except Exception as e:
            logger.error(f"Error showing workflow details: {e}", exc_info=True)

    @app.action("workflow_advance")
    async def handle_workflow_advance_action(ack, body, client):
        await ack()
        val = body["actions"][0]["value"]
        workflow_id = val.split("_")[1]
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            # Post loading message
            loading_msg = await client.chat_postMessage(channel=channel_id, text=f"➡️ Advancing workflow `{workflow_id}`...")
            ts = loading_msg.get("ts")
            
            workflow = await state_manager.advance_operational_workflow_stage(session, workflow_id)
            await session.commit()
            
            blocks = build_workflow_detail_blocks(workflow)
            await client.chat_update(channel=channel_id, ts=ts, text=f"Workflow Advanced: {workflow.name}", blocks=blocks)
            
            await session.close()
        except Exception as e:
            logger.error(f"Error advancing workflow {workflow_id}: {e}", exc_info=True)
            await client.chat_postMessage(channel=channel_id, text=f"❌ Failed to advance workflow `{workflow_id}`: {str(e)}")

    @app.action("mission_create_workflow")
    async def handle_mission_create_workflow_action(ack, body, client):
        await ack()
        val = body["actions"][0]["value"]
        parts = val.split("_")
        mission_id = parts[1]
        operation_id = parts[2] if len(parts) > 2 else ""
        channel_id = body["channel"]["id"]
        
        try:
            from features.workflows.domain import WorkflowPriority
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "create_workflow_modal",
                    "private_metadata": f"{channel_id}|{mission_id}|{operation_id}",
                    "title": {"type": "plain_text", "text": "Create Workflow"},
                    "submit": {"type": "plain_text", "text": "Create"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "name_block",
                            "element": {"type": "plain_text_input", "action_id": "name_input"},
                            "label": {"type": "plain_text", "text": "Workflow Name"}
                        },
                        {
                            "type": "input",
                            "block_id": "desc_block",
                            "optional": True,
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "desc_input"},
                            "label": {"type": "plain_text", "text": "Description"}
                        },
                        {
                            "type": "input",
                            "block_id": "priority_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select priority"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": p.name}, "value": p.name}
                                    for p in WorkflowPriority
                                ],
                                "action_id": "priority_input"
                            },
                            "label": {"type": "plain_text", "text": "Priority"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening create workflow modal: {e}", exc_info=True)

    @app.command("/create-workflow")
    async def create_workflow_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        operation_id = command.get("text", "").strip()
        
        try:
            from features.workflows.domain import WorkflowPriority
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "create_workflow_modal",
                    "private_metadata": f"{channel_id}||{operation_id}",
                    "title": {"type": "plain_text", "text": "Create Workflow"},
                    "submit": {"type": "plain_text", "text": "Create"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "name_block",
                            "element": {"type": "plain_text_input", "action_id": "name_input"},
                            "label": {"type": "plain_text", "text": "Workflow Name"}
                        },
                        {
                            "type": "input",
                            "block_id": "desc_block",
                            "optional": True,
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "desc_input"},
                            "label": {"type": "plain_text", "text": "Description"}
                        },
                        {
                            "type": "input",
                            "block_id": "priority_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select priority"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": p.name}, "value": p.name}
                                    for p in WorkflowPriority
                                ],
                                "action_id": "priority_input"
                            },
                            "label": {"type": "plain_text", "text": "Priority"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening create workflow modal from command: {e}", exc_info=True)

    @app.view("create_workflow_modal")
    async def handle_create_workflow_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        channel_id = meta[0]
        mission_id = meta[1]
        operation_id = meta[2] if meta[2] else None
        user_id = body["user"]["id"]
        
        name = values["name_block"]["name_input"]["value"]
        desc = values["desc_block"]["desc_input"]["value"]
        priority = values["priority_block"]["priority_input"]["selected_option"]["value"]
        
        await ack()
        
        try:
            from features.workflows.schemas import WorkflowCreate
            from features.workflows.domain import WorkflowPriority, WorkflowStageType
            
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            # Use standard response stages for manual workflow creation
            stages = [WorkflowStageType.INVESTIGATION, WorkflowStageType.EVIDENCE_COLLECTION, WorkflowStageType.REVIEW]
            
            wf_in = WorkflowCreate(
                name=name,
                description=desc,
                priority=WorkflowPriority[priority],
                stages=stages,
                operation_id=operation_id
            )
            
            workflow = await state_manager.create_operational_workflow(session, wf_in, user_id)
            await session.commit()
            
            blocks = build_workflow_detail_blocks(workflow)
            await client.chat_postMessage(channel=channel_id, text=f"Workflow Created: {workflow.name}", blocks=blocks)
            await session.close()
        except Exception as e:
            logger.error(f"Error creating workflow: {e}", exc_info=True)
