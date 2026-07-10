import logging

from slack_bolt.async_app import AsyncApp

from core.services import registry as service_registry
from core.notifications import NotificationEngine
from infrastructure.database import get_db_session

from features.workflow.domain import DecisionAction
from features.workflow.schemas import DecisionRequest
from features.workflow.service import WorkflowService
from features.workflow.repository import AuditRepository

from features.recommendations.repository import RecommendationRepository

logger = logging.getLogger("crisispilot.workflow.slack_handlers")


def register_workflow_handlers(app: AsyncApp) -> None:
    """Registers Slack interactions for Human-in-the-Loop workflows."""

    async def _process_decision(ack, body, client, action: DecisionAction, status_text: str):
        await ack()
        
        user_id = body["user"]["id"]
        recommendation_id = body["actions"][0]["value"]
        
        # Original message info for updating the UI
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        original_blocks = body["message"].get("blocks", [])
        
        try:
            # Inject Services
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            workflow_service = WorkflowService(
                audit_repository=AuditRepository(),
                recommendation_repository=RecommendationRepository(),
                notification_engine=service_registry.get(NotificationEngine)
            )
            
            # 1. Apply Decision
            req = DecisionRequest(
                recommendation_id=recommendation_id,
                reviewer_id=user_id,
                action=action,
                comments=f"Slack action invoked by {user_id}"
            )
            await workflow_service.apply_decision(session, req)
            await session.commit()
            await session.close()
            
            # 2. Update the original message to remove the buttons and show the result
            # Assuming the last block is the actions block. We replace it.
            new_blocks = []
            for block in original_blocks:
                if block.get("type") == "actions":
                    new_blocks.append({
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"{status_text} by <@{user_id}>"
                            }
                        ]
                    })
                    if action == DecisionAction.START_EXECUTION:
                        new_blocks.append({
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Mark Completed", "emoji": True},
                                    "value": recommendation_id,
                                    "action_id": "complete_execution"
                                }
                            ]
                        })
                else:
                    new_blocks.append(block)
                    
            await client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="Decision recorded.",
                blocks=new_blocks
            )
            
            # Post to main incident thread
            from core.state import StateManager
            state_manager = service_registry.get(StateManager)
            rec = await workflow_service.recommendation_repository.get(session, recommendation_id)
            if rec:
                incident = await state_manager.incident_service.get_incident(session, rec.incident_id)
                if incident and incident.thread_ts:
                    notification_engine = service_registry.get(NotificationEngine)
                    await notification_engine.dispatch_threaded_message(
                        channel_id=incident.channel_id,
                        thread_ts=incident.thread_ts,
                        text=f"{status_text} by <@{user_id}>"
                    )
            
        except Exception as e:
            logger.error(f"Error processing decision {action} for recommendation {recommendation_id}: {e}", exc_info=True)
            # Post ephemeral error
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"Failed to process your decision: {str(e)}"
            )

    @app.action("workflow_approve_assign")
    async def handle_workflow_approve_assign(ack, body, client):
        await ack()
        # Open a modal to select assignee, notes, and due date
        recommendation_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        
        try:
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "assign_recommendation_modal",
                    "private_metadata": f"{recommendation_id}|{channel_id}|{message_ts}",
                    "title": {"type": "plain_text", "text": "Assign Recommendation"},
                    "submit": {"type": "plain_text", "text": "Assign"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "assignee_block",
                            "element": {
                                "type": "users_select",
                                "placeholder": {"type": "plain_text", "text": "Select a user"},
                                "action_id": "assignee_input"
                            },
                            "label": {"type": "plain_text", "text": "Assign To"}
                        },
                        {
                            "type": "input",
                            "block_id": "notes_block",
                            "optional": True,
                            "element": {
                                "type": "plain_text_input",
                                "multiline": True,
                                "action_id": "notes_input"
                            },
                            "label": {"type": "plain_text", "text": "Execution Notes"}
                        },
                        {
                            "type": "input",
                            "block_id": "date_block",
                            "optional": True,
                            "element": {
                                "type": "datepicker",
                                "initial_date": "2026-07-10",
                                "placeholder": {"type": "plain_text", "text": "Select a date"},
                                "action_id": "date_input"
                            },
                            "label": {"type": "plain_text", "text": "Due Date"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening assign modal: {e}", exc_info=True)

    @app.view("assign_recommendation_modal")
    async def handle_assign_recommendation_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        recommendation_id = meta[0]
        channel_id = meta[1]
        message_ts = meta[2]
        
        assignee_id = values["assignee_block"]["assignee_input"]["selected_user"]
        notes = values["notes_block"]["notes_input"]["value"] or ""
        
        try:
            # We must run this async process in the background or await it
            # It's better to await since we have ack()
            # But we must ack first to close modal
            await ack()
            
            user_id = body["user"]["id"]
            
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            workflow_service = WorkflowService(
                audit_repository=AuditRepository(),
                recommendation_repository=RecommendationRepository(),
                notification_engine=service_registry.get(NotificationEngine)
            )
            
            # Apply Decision: ASSIGN
            req = DecisionRequest(
                recommendation_id=recommendation_id,
                reviewer_id=user_id,
                action=DecisionAction.ASSIGN,
                comments=f"Assigned to <@{assignee_id}>. Notes: {notes}"
            )
            await workflow_service.apply_decision(session, req)
            
            # Also update Recommendation entity with assigned_to (this could be done inside apply_decision, but we do it here for now)
            rec = await workflow_service.recommendation_repository.get(session, recommendation_id)
            incident_id = None
            if rec:
                from datetime import datetime, timezone
                rec.assigned_to = assignee_id
                rec.assigned_by = user_id
                rec.assigned_at = datetime.now(timezone.utc)
                rec.approved_by = user_id
                
                # Auto-declare Incident
                from features.incident_management.service import IncidentService
                from features.incident_management.repository import IncidentRepository
                from features.incident_management.schemas import IncidentCreate
                from features.incident_management.domain import IncidentSeverity
                
                incident_svc = IncidentService(repository=IncidentRepository())
                incident_data = IncidentCreate(
                    title=f"Escalation: {rec.title}",
                    description=rec.description,
                    channel_id=channel_id,
                    operation_id=rec.operation_id,
                    severity=IncidentSeverity.HIGH
                )
                incident = await incident_svc.create_incident(session, incident_data)
                incident_id = incident.id
                
                session.add(rec)
            
            await session.commit()
            await session.close()
            
            # Update the original message
            # Fetch message history to get original blocks (Slack view submission doesn't pass message blocks)
            try:
                history = await client.conversations_history(channel=channel_id, latest=message_ts, limit=1, inclusive=True)
            except Exception as e:
                # If bot is not in the channel, join it and retry
                try:
                    await client.conversations_join(channel=channel_id)
                    history = await client.conversations_history(channel=channel_id, latest=message_ts, limit=1, inclusive=True)
                except Exception as e_inner:
                    history = {}
                    logger.warning(f"Could not update original recommendation message even after attempting to join channel: {e_inner}")

            if history.get("messages"):
                original_blocks = history["messages"][0].get("blocks", [])
                new_blocks = []
                for block in original_blocks:
                    if block.get("type") == "actions":
                        text = f"✅ Approved and Assigned to <@{assignee_id}> by <@{user_id}>"
                        if incident_id:
                            text += f"\n🚨 *Incident `{incident_id}` officially declared.*"
                            
                        new_blocks.append({
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": text
                                }
                            ]
                        })
                    else:
                        new_blocks.append(block)
                        
                await client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text="Recommendation Assigned",
                    blocks=new_blocks
                )
                
            # DM Assignee
            dm = await client.conversations_open(users=assignee_id)
            dm_channel = dm["channel"]["id"]
            
            dm_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"You have been assigned a recommendation by <@{user_id}>.\n*Notes:* {notes}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Start Execution", "emoji": True},
                            "style": "primary",
                            "value": recommendation_id,
                            "action_id": "start_execution"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Mark Completed", "emoji": True},
                            "value": recommendation_id,
                            "action_id": "open_complete_modal"
                        }
                    ]
                }
            ]
            
            await client.chat_postMessage(
                channel=dm_channel,
                text="You have been assigned a recommendation.",
                blocks=dm_blocks
            )
            
            # Post threaded reply in DM
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=f"👤 Recommendation assigned to <@{assignee_id}> by <@{user_id}>"
            )
            
            # Post to main incident thread
            from core.state import StateManager
            state_manager = service_registry.get(StateManager)
            if rec:
                incident = await state_manager.incident_service.get_incident(session, rec.incident_id)
                if incident and incident.thread_ts:
                    notification_engine = service_registry.get(NotificationEngine)
                    await notification_engine.dispatch_threaded_message(
                        channel_id=incident.channel_id,
                        thread_ts=incident.thread_ts,
                        text=f"👤 Recommendation assigned to <@{assignee_id}> by <@{user_id}>\n*Notes:* {notes}"
                    )
            
        except Exception as e:
            logger.error(f"Error handling assign submission: {e}", exc_info=True)

    @app.action("workflow_reject")
    async def handle_workflow_reject(ack, body, client):
        await _process_decision(ack, body, client, DecisionAction.REJECT, "❌ Rejected")

    @app.action("start_execution")
    async def handle_start_execution(ack, body, client):
        await _process_decision(ack, body, client, DecisionAction.START_EXECUTION, "▶️ Execution Started")

    @app.action("open_complete_modal")
    async def handle_open_complete_modal(ack, body, client):
        await ack()
        recommendation_id = body["actions"][0]["value"]
        message_ts = body["message"]["ts"]
        channel_id = body["channel"]["id"]
        
        session_gen = get_db_session()
        session = await anext(session_gen)
        workflow_service = WorkflowService(
            audit_repository=AuditRepository(),
            recommendation_repository=RecommendationRepository(),
            notification_engine=service_registry.get(NotificationEngine)
        )
        rec = await workflow_service.recommendation_repository.get(session, recommendation_id)
        await session.close()
        
        if not rec:
            return
            
        modal_view = {
            "type": "modal",
            "callback_id": "complete_modal_submission",
            "private_metadata": f"{message_ts}|{channel_id}|{recommendation_id}",
            "title": {"type": "plain_text", "text": "Complete Mission"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Task:* {rec.title}\n*Operation:* `{rec.operation_id}`"
                    }
                },
                {
                    "type": "input",
                    "block_id": "notes_input",
                    "element": {
                        "type": "plain_text_input",
                        "multiline": True,
                        "action_id": "notes",
                        "placeholder": {"type": "plain_text", "text": "Enter resolution notes..."}
                    },
                    "label": {"type": "plain_text", "text": "Resolution Notes"}
                }
            ]
        }
        
        await client.views_open(
            trigger_id=body["trigger_id"],
            view=modal_view
        )

    @app.view("complete_modal_submission")
    async def handle_complete_modal_submission(ack, body, client, view):
        await ack()
        
        user_id = body["user"]["id"]
        private_metadata = view["private_metadata"]
        message_ts, channel_id, recommendation_id = private_metadata.split("|")
        
        values = view["state"]["values"]
        notes = values["notes_input"]["notes"]["value"]
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            workflow_service = WorkflowService(
                audit_repository=AuditRepository(),
                recommendation_repository=RecommendationRepository(),
                notification_engine=service_registry.get(NotificationEngine)
            )
            
            req = DecisionRequest(
                recommendation_id=recommendation_id,
                reviewer_id=user_id,
                action=DecisionAction.COMPLETE_EXECUTION,
                comments=f"Execution completed. Notes: {notes}"
            )
            
            await workflow_service.apply_decision(session, req)
            await session.commit()
            await session.close()
            
            # Update DM Message
            new_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *Mission Completed* by <@{user_id}>\n*Resolution Notes:* {notes}"
                    }
                }
            ]
            await client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="Mission Completed",
                blocks=new_blocks
            )
            
        except Exception as e:
            logger.error(f"Error handling complete modal submission: {e}", exc_info=True)

    @app.action("complete_execution")
    async def handle_complete_execution(ack, body, client):
        await _process_decision(ack, body, client, DecisionAction.COMPLETE_EXECUTION, "✅ Execution Completed")

    @app.command("/pending-review")
    async def pending_review_command(ack, body, client):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            repo = RecommendationRepository()
            all_recs = await repo.get_all_pending(session)
            
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "⏳ Entities with Pending Reviews"}
                },
                {"type": "divider"}
            ]
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Debug Info: Found {len(all_recs)} pending recommendations in total."}
            })
            
            if not all_recs:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "No pending reviews found."}})
                await client.chat_postMessage(channel=channel_id, text="Pending Reviews", blocks=blocks)
                await session.close()
                return

            # Group recommendations
            incident_map = {}
            operation_map = {}
            orphaned = []
            
            for r in all_recs:
                if r.incident_id:
                    if r.incident_id not in incident_map:
                        incident_map[r.incident_id] = []
                    incident_map[r.incident_id].append(r)
                elif r.operation_id:
                    if r.operation_id not in operation_map:
                        operation_map[r.operation_id] = []
                    operation_map[r.operation_id].append(r)
                else:
                    orphaned.append(r)
            
            # Fetch Incident details
            if incident_map:
                from sqlalchemy.future import select
                from features.incident_management.models import Incident
                
                result = await session.execute(
                    select(Incident).where(Incident.id.in_(list(incident_map.keys())))
                )
                incidents = {inc.id: inc for inc in result.scalars().all()}
                
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Incidents*"}})
                
                for inc_id, recs in incident_map.items():
                    inc = incidents.get(inc_id)
                    title = f"*{inc.title}*" if inc else f"*Unknown/Deleted Incident*"
                    thread_ts = inc.thread_ts if inc else None
                    
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"{title}\nID: `{inc_id}` | Pending Reviews: {len(recs)}"},
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Thread 🧵", "emoji": True},
                            "url": thread_ts if thread_ts else "https://slack.com",
                            "action_id": f"jump_to_incident_{inc_id}"
                        }
                    })
                    # Show buttons for the recs
                    for r in recs:
                        blocks.append({
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"↳ _{r.title}_"},
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Approve & Assign", "emoji": True},
                                "value": r.id,
                                "action_id": "workflow_approve_assign"
                            }
                        })
            
            # Fetch Operation details
            if operation_map:
                from features.operations.models import Operation
                
                result = await session.execute(
                    select(Operation).where(Operation.id.in_(list(operation_map.keys())))
                )
                ops = {op.id: op for op in result.scalars().all()}
                
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Operations*"}})
                
                for op_id, recs in operation_map.items():
                    op = ops.get(op_id)
                    title = f"*{op.name}*" if op else f"*Unknown/Deleted Operation*"
                    
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"{title}\nID: `{op_id}` | Pending Reviews: {len(recs)}"},
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Dashboard 🔍", "emoji": True},
                            "value": f"operation_{op_id}",
                            "action_id": "op_view_dashboard"
                        }
                    })
                    for r in recs:
                        blocks.append({
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"↳ _{r.title}_"},
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Approve & Assign", "emoji": True},
                                "value": r.id,
                                "action_id": "workflow_approve_assign"
                            }
                        })
                        
            # Orphaned
            if orphaned:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Global / Orphaned Recommendations*"}})
                for r in orphaned:
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*{r.title}*\nID: `{r.id}`"},
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve & Assign", "emoji": True},
                            "value": r.id,
                            "action_id": "workflow_approve_assign"
                        }
                    })
                
            await client.chat_postMessage(channel=channel_id, text="Pending Reviews", blocks=blocks)
            
            await session.close()
        except Exception as e:
            logger.error(f"Error listing pending reviews: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Error listing pending reviews: {e}")
