import logging

from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError

from core.services import registry as service_registry
from core.notifications import NotificationEngine
from infrastructure.database import get_db_session

from features.incident_management.schemas import IncidentCreate
from features.incident_management.domain import IncidentSeverity
from features.incident_management.service import IncidentService
from features.incident_management.repository import IncidentRepository

from features.recommendations.service import RecommendationService
from features.recommendations.repository import RecommendationRepository
from features.recommendations.intelligence import IncidentIntelligenceService
from features.recommendations.router import RecommendationRouter

logger = logging.getLogger("crisispilot.incident_management.slack_handlers")


def register_incident_handlers(app: AsyncApp) -> None:
    """Registers Slack interactions for Incident Management."""

    @app.command("/declare-incident")
    async def declare_incident_command(ack, body, client):
        await ack()

        modal_blocks = [
            {
                "type": "input",
                "block_id": "title_block",
                "element": {"type": "plain_text_input", "action_id": "title_input"},
                "label": {"type": "plain_text", "text": "Incident Title"}
            },
            {
                "type": "input",
                "block_id": "severity_block",
                "element": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Select severity"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "CRITICAL 🚨"}, "value": "CRITICAL"},
                        {"text": {"type": "plain_text", "text": "HIGH 🔴"}, "value": "HIGH"},
                        {"text": {"type": "plain_text", "text": "MEDIUM 🟠"}, "value": "MEDIUM"},
                        {"text": {"type": "plain_text", "text": "LOW 🟡"}, "value": "LOW"}
                    ],
                    "action_id": "severity_input"
                },
                "label": {"type": "plain_text", "text": "Severity"}
            },
            {
                "type": "input",
                "block_id": "desc_block",
                "element": {"type": "plain_text_input", "multiline": True, "action_id": "desc_input"},
                "label": {"type": "plain_text", "text": "Description"}
            }
        ]

        try:
            # Store the originating channel in private_metadata so we know where to post the thread
            channel_id = body.get("channel_id")
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "declare_incident_modal",
                    "private_metadata": channel_id,
                    "title": {"type": "plain_text", "text": "Declare Incident"},
                    "submit": {"type": "plain_text", "text": "Declare"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": modal_blocks
                }
            )
        except SlackApiError as e:
            logger.error(f"Error opening modal: {e}")

    @app.view("declare_incident_modal")
    async def handle_declare_incident_submission(ack, body, view, logger):
        values = view["state"]["values"]
        channel_id = view["private_metadata"]
        
        title = values["title_block"]["title_input"]["value"]
        severity_str = values["severity_block"]["severity_input"]["selected_option"]["value"]
        desc = values["desc_block"]["desc_input"]["value"]

        try:
            # Inject Services
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            incident_service = IncidentService(repository=IncidentRepository())
            intelligence_svc = service_registry.get(IncidentIntelligenceService)
            router = service_registry.get(RecommendationRouter)
            recommendation_service = RecommendationService(
                repository=RecommendationRepository(),
                intelligence_service=intelligence_svc,
                router=router
            )
            notification_engine = service_registry.get(NotificationEngine)
            
            # 1. Create Incident
            create_data = IncidentCreate(
                title=title,
                description=desc,
                severity=IncidentSeverity[severity_str],
                channel_id=channel_id,
                created_by=body["user"]["id"]
            )
            incident = await incident_service.create_incident(session, create_data)
            await session.commit()
            await session.refresh(incident)
            
            await ack()

            # 2. Publish to Slack
            thread_ts = await notification_engine.publish_incident_created(incident, channel_id)
            
            from core.state import StateManager
            state_manager = service_registry.get(StateManager)
            await state_manager.update_incident_thread_ts(session, incident.id, thread_ts)
            
            # 3. Simulate automatic recommendations to populate the thread
            incident_context = {
                "id": incident.id,
                "title": incident.title,
                "severity": incident.severity.name,
                "description": incident.description
            }
            recs = await recommendation_service.generate_recommendations(session, incident_context, [])
            await session.commit()
            
            for rec in recs:
                await notification_engine.publish_recommendation(rec, channel_id, thread_ts)

            await session.close()
            
        except Exception as e:
            await ack()
            logger.error(f"Unexpected error in declare_incident: {e}", exc_info=True)

    @app.command("/list-incidents")
    async def list_incidents_command(ack, body, client):
        await ack()
        channel_id = body.get("channel_id")
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            incident_service = IncidentService(repository=IncidentRepository())
            
            # For MVP, get all incidents
            from sqlalchemy.future import select
            from features.incident_management.models import Incident
            result = await session.execute(select(Incident).order_by(Incident.created_at.desc()).limit(10))
            incidents = result.scalars().all()
            
            if not incidents:
                await client.chat_postMessage(channel=channel_id, text="No incidents found.")
                return
                
            blocks = [{"type": "header", "text": {"type": "plain_text", "text": "Recent Incidents"}}]
            for inc in incidents:
                assignee_text = f"Assigned to <@{inc.assigned_user_id}>" if inc.assigned_user_id else "Unassigned"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{inc.title}*\nID: `{inc.id}` | Status: {inc.status.name} | Severity: {inc.severity.name}\n{assignee_text} | Created: {inc.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
                    }
                })
                
                if inc.thread_ts:
                    try:
                        permalink_res = await client.chat_getPermalink(channel=inc.channel_id, message_ts=inc.thread_ts)
                        link = permalink_res.get("permalink")
                    except Exception:
                        link = f"https://slack.com/app_redirect?channel={inc.channel_id}&message_ts={inc.thread_ts}"
                        
                    blocks.append({
                        "type": "context",
                        "elements": [{"type": "mrkdwn", "text": f"<{link}|View Incident Thread 🧵>"}]
                    })
                    
                
                actions = []
                if inc.status.name not in ["RESOLVED", "ARCHIVED"]:
                    actions.extend([
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Assign 👤", "emoji": True},
                            "value": inc.id,
                            "action_id": "incident_assign"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Resolve ✅", "emoji": True},
                            "style": "primary",
                            "value": inc.id,
                            "action_id": "incident_resolve"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Archive 🗄️", "emoji": True},
                            "value": inc.id,
                            "action_id": "incident_archive"
                        }
                    ])
                    
                actions.extend([
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Timeline 🕒", "emoji": True},
                        "value": inc.id,
                        "action_id": "incident_view_timeline"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Evidence 📁", "emoji": True},
                        "value": inc.id,
                        "action_id": "incident_view_evidence"
                    }
                ])
                
                actions.append({
                    "type": "overflow",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Mark Duplicate", "emoji": True},
                            "value": f"duplicate_{inc.id}"
                        },
                        {
                            "text": {"type": "plain_text", "text": "Link to Operation 🔗", "emoji": True},
                            "value": f"linkop_{inc.id}"
                        },
                        {
                            "text": {"type": "plain_text", "text": "Link to Mission 🎯", "emoji": True},
                            "value": f"linkmiss_{inc.id}"
                        },
                        {
                            "text": {"type": "plain_text", "text": "Merge Incident", "emoji": True},
                            "value": f"merge_{inc.id}"
                        },
                        {
                            "text": {"type": "plain_text", "text": "Delete Incident 🗑️", "emoji": True},
                            "value": f"delete_{inc.id}"
                        }
                    ],
                    "action_id": "incident_more_actions"
                })
                
                blocks.append({
                    "type": "actions",
                    "elements": actions
                })
            
            await client.chat_postMessage(channel=channel_id, text="Incidents List", blocks=blocks)
            await session.close()
        except Exception as e:
            logger.error(f"Error listing incidents: {e}", exc_info=True)

    async def _handle_incident_action(ack, body, client, action_type: str):
        await ack()
        incident_id = body["actions"][0].get("value")
        if not incident_id:
            # Handle overflow menu values
            selected = body["actions"][0].get("selected_option", {}).get("value", "")
            if selected.startswith("duplicate_"):
                incident_id = selected.replace("duplicate_", "")
                action_type = "duplicate"
            elif selected.startswith("merge_"):
                incident_id = selected.replace("merge_", "")
                action_type = "merge"
            elif selected.startswith("delete_"):
                incident_id = selected.replace("delete_", "")
                action_type = "delete"
            elif selected.startswith("linkop_"):
                incident_id = selected.replace("linkop_", "")
                action_type = "link_operation"
            elif selected.startswith("linkmiss_"):
                incident_id = selected.replace("linkmiss_", "")
                action_type = "link_mission"
        
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        
        if action_type in ["link_operation", "link_mission"]:
            try:
                session_gen = get_db_session()
                session = await anext(session_gen)
                
                if action_type == "link_operation":
                    from features.operations.models import Operation
                    from sqlalchemy.future import select
                    from features.operations.domain import OperationStatus
                    result = await session.execute(select(Operation).filter(Operation.status == OperationStatus.ACTIVE))
                    operations = result.scalars().all()
                    
                    options = [{"text": {"type": "plain_text", "text": op.name[:75]}, "value": op.id} for op in operations]
                    if not options:
                        options = [{"text": {"type": "plain_text", "text": "No active operations found"}, "value": "none"}]
                        
                    await client.views_open(
                        trigger_id=body["trigger_id"],
                        view={
                            "type": "modal",
                            "callback_id": "link_operation_modal",
                            "private_metadata": f"{incident_id}|{channel_id}|{message_ts}",
                            "title": {"type": "plain_text", "text": "Link to Operation"},
                            "submit": {"type": "plain_text", "text": "Link"},
                            "close": {"type": "plain_text", "text": "Cancel"},
                            "blocks": [
                                {
                                    "type": "input",
                                    "block_id": "operation_block",
                                    "element": {
                                        "type": "static_select",
                                        "placeholder": {"type": "plain_text", "text": "Select an Operation"},
                                        "options": options,
                                        "action_id": "operation_input"
                                    },
                                    "label": {"type": "plain_text", "text": "Target Operation"}
                                }
                            ]
                        }
                    )
                else:
                    from features.missions.models import Mission
                    from sqlalchemy.future import select
                    from features.missions.domain import MissionStatus
                    result = await session.execute(
                        select(Mission).filter(
                            Mission.status.in_([
                                MissionStatus.CREATED, 
                                MissionStatus.SCHEDULED, 
                                MissionStatus.RUNNING, 
                                MissionStatus.PAUSED
                            ])
                        )
                    )
                    missions = result.scalars().all()
                    
                    options = [{"text": {"type": "plain_text", "text": m.name[:75]}, "value": m.id} for m in missions]
                    if not options:
                        options = [{"text": {"type": "plain_text", "text": "No active missions found"}, "value": "none"}]
                        
                    await client.views_open(
                        trigger_id=body["trigger_id"],
                        view={
                            "type": "modal",
                            "callback_id": "link_mission_modal",
                            "private_metadata": f"{incident_id}|{channel_id}|{message_ts}",
                            "title": {"type": "plain_text", "text": "Link to Mission"},
                            "submit": {"type": "plain_text", "text": "Link"},
                            "close": {"type": "plain_text", "text": "Cancel"},
                            "blocks": [
                                {
                                    "type": "input",
                                    "block_id": "mission_block",
                                    "element": {
                                        "type": "static_select",
                                        "placeholder": {"type": "plain_text", "text": "Select a Mission"},
                                        "options": options,
                                        "action_id": "mission_input"
                                    },
                                    "label": {"type": "plain_text", "text": "Target Mission"}
                                }
                            ]
                        }
                    )
                await session.close()
            except Exception as e:
                logger.error(f"Error opening link modal: {e}", exc_info=True)
            return
        
        from core.state import StateManager
        state_manager = StateManager()
        await state_manager.initialize()
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            if action_type == "archive":
                await state_manager.archive_incident(session, incident_id, user_id)
                text = f"🗄️ Incident archived by <@{user_id}>"
            elif action_type == "duplicate":
                # Mock parent_id for MVP
                await state_manager.mark_incident_duplicate(session, incident_id, "mock-parent-id", user_id)
                text = f"🔗 Incident marked as duplicate by <@{user_id}>"
            elif action_type == "merge":
                await state_manager.mark_incident_duplicate(session, incident_id, "mock-parent-id", user_id)
                text = f"🔗 Incident merged by <@{user_id}>"
            elif action_type == "delete":
                await state_manager.delete_incident(session, incident_id, user_id)
                text = f"🗑️ Incident deleted by <@{user_id}>"
            else:
                text = f"Action {action_type} performed by <@{user_id}>"
                
            await session.commit()
            await session.close()
            
            # Post thread update
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=text
            )
        except Exception as e:
            logger.error(f"Error handling incident action: {e}", exc_info=True)

    @app.action("incident_resolve")
    async def handle_incident_resolve(ack, body, client):
        await ack()
        incident_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        
        try:
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "resolve_incident_modal",
                    "private_metadata": f"{incident_id}|{channel_id}|{message_ts}",
                    "title": {"type": "plain_text", "text": "Resolve Incident"},
                    "submit": {"type": "plain_text", "text": "Resolve"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "notes_block",
                            "element": {
                                "type": "plain_text_input",
                                "multiline": True,
                                "action_id": "notes_input"
                            },
                            "label": {"type": "plain_text", "text": "Resolution Notes"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening resolve incident modal: {e}", exc_info=True)
            
    @app.view("resolve_incident_modal")
    async def handle_resolve_incident_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        incident_id = meta[0]
        channel_id = meta[1]
        message_ts = meta[2]
        notes = values["notes_block"]["notes_input"]["value"]
        
        await ack()
        
        user_id = body["user"]["id"]
        
        from core.state import StateManager
        state_manager = service_registry.get(StateManager)
        notification_engine = service_registry.get(NotificationEngine)
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            incident = await state_manager.resolve_incident(session, incident_id, user_id, comments=notes)
            await session.commit()
            
            # Also update the original incident message to remove the action buttons
            if incident and incident.thread_ts:
                updated_blocks = notification_engine.build_incident_card_blocks(incident)
                try:
                    await notification_engine.update_message(
                        channel_id=incident.channel_id,
                        ts=incident.thread_ts,
                        text=f"Incident Resolved: {incident.title}",
                        blocks=updated_blocks
                    )
                except Exception as e:
                    logger.error(f"Failed to update original incident message: {e}")
                    
            # Post thread update where they clicked it
            await notification_engine.dispatch_threaded_message(
                channel_id=channel_id,
                thread_ts=message_ts,
                text=f"✅ Incident resolved by <@{user_id}>\n*Notes:* {notes}"
            )
            
            # Post to main thread if different
            if incident and incident.thread_ts and incident.thread_ts != message_ts:
                await notification_engine.dispatch_threaded_message(
                    channel_id=incident.channel_id,
                    thread_ts=incident.thread_ts,
                    text=f"✅ Incident resolved by <@{user_id}>\n*Notes:* {notes}"
                )
                
            await session.close()
        except Exception as e:
            logger.error(f"Error handling resolve incident submission: {e}", exc_info=True)

    @app.action("incident_archive")
    async def handle_incident_archive(ack, body, client):
        await _handle_incident_action(ack, body, client, "archive")

    @app.action("incident_assign")
    async def handle_incident_assign(ack, body, client):
        await ack()
        incident_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        
        try:
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "assign_incident_modal",
                    "private_metadata": f"{incident_id}|{channel_id}|{message_ts}",
                    "title": {"type": "plain_text", "text": "Assign Incident"},
                    "submit": {"type": "plain_text", "text": "Assign"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "assignee_block",
                            "element": {
                                "type": "multi_users_select",
                                "placeholder": {"type": "plain_text", "text": "Select users"},
                                "action_id": "assignee_input"
                            },
                            "label": {"type": "plain_text", "text": "Assign To"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening assign incident modal: {e}", exc_info=True)
            
    @app.view("assign_incident_modal")
    async def handle_assign_incident_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        incident_id = meta[0]
        channel_id = meta[1]
        message_ts = meta[2]
        assignee_ids = values["assignee_block"]["assignee_input"]["selected_users"]
        
        await ack()
        
        user_id = body["user"]["id"]
        
        from core.state import StateManager
        state_manager = service_registry.get(StateManager)
        notification_engine = service_registry.get(NotificationEngine)
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            # Store comma separated users in db
            assigned_str = ",".join(assignee_ids)
            updated_incident = await state_manager.assign_incident(session, incident_id, user_id, assigned_str)
            
            await session.commit()
            
            assignee_text = ", ".join([f"<@{uid}>" for uid in assignee_ids])
            # Post thread update
            await notification_engine.dispatch_threaded_message(
                channel_id=channel_id,
                thread_ts=message_ts,
                text=f"👤 Incident assigned to {assignee_text} by <@{user_id}>"
            )
            
            # Send DM to each Assignee
            if updated_incident:
                link_text = ""
                if updated_incident.thread_ts:
                    try:
                        permalink_res = await client.chat_getPermalink(channel=updated_incident.channel_id, message_ts=updated_incident.thread_ts)
                        link = permalink_res.get("permalink")
                    except Exception:
                        link = f"https://slack.com/app_redirect?channel={updated_incident.channel_id}&message_ts={updated_incident.thread_ts}"
                    link_text = f" | <{link}|View Incident Thread 🧵>"
                    
                for uid in assignee_ids:
                    blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"🚨 You have been assigned to an Incident by <@{user_id}>.\n*Incident:* {updated_incident.title}\n*ID:* `{incident_id}`{link_text}"
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Start Execution", "emoji": True},
                                    "style": "primary",
                                    "value": incident_id,
                                    "action_id": "incident_start_execution"
                                },
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Mark Completed", "emoji": True},
                                    "value": incident_id,
                                    "action_id": "incident_resolve"
                                }
                            ]
                        }
                    ]
                    await notification_engine.dispatch_direct_message(uid, "You have been assigned to an incident.", blocks)
                        
            await session.close()
        except Exception as e:
            logger.error(f"Error handling assign incident submission: {e}", exc_info=True)

    @app.action("incident_start_execution")
    async def handle_incident_start_execution(ack, body, client):
        await ack()
        incident_id = body["actions"][0]["value"]
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        
        from core.state import StateManager
        from features.workflow.domain import DecisionAction
        from features.incident_management.domain import IncidentStatus
        state_manager = service_registry.get(StateManager)
        notification_engine = service_registry.get(NotificationEngine)
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            await state_manager.transition_incident_status(
                session, incident_id, IncidentStatus.IN_PROGRESS, user_id, DecisionAction.START_EXECUTION, comments="Started execution from DM"
            )
            await session.commit()
            
            original_blocks = body["message"].get("blocks", [])
            new_blocks = []
            for block in original_blocks:
                if block.get("type") == "actions":
                    new_blocks.append({
                        "type": "context",
                        "elements": [{"type": "mrkdwn", "text": f"▶️ Execution Started by <@{user_id}>"}]
                    })
                    new_blocks.append({
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Mark Completed", "emoji": True},
                                "value": incident_id,
                                "action_id": "incident_resolve"
                            }
                        ]
                    })
                else:
                    new_blocks.append(block)
                    
            await notification_engine.update_message(
                channel_id=channel_id,
                ts=message_ts,
                text="Execution Started",
                blocks=new_blocks
            )
            
            # Post to main thread if it exists
            incident = await state_manager.incident_service.get_incident(session, incident_id)
            if incident and incident.thread_ts and incident.thread_ts != message_ts:
                await notification_engine.dispatch_threaded_message(
                    channel_id=incident.channel_id,
                    thread_ts=incident.thread_ts,
                    text=f"▶️ Execution Started by <@{user_id}>"
                )
                
            await session.close()
            
        except Exception as e:
            logger.error(f"Error starting incident execution: {e}", exc_info=True)

    @app.view("link_operation_modal")
    async def handle_link_operation_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        incident_id = meta[0]
        channel_id = meta[1]
        message_ts = meta[2]
        operation_id = values["operation_block"]["operation_input"]["selected_option"]["value"]
        
        await ack()
        if operation_id == "none":
            return
            
        user_id = body["user"]["id"]
        from core.state import StateManager
        state_manager = service_registry.get(StateManager)
        notification_engine = service_registry.get(NotificationEngine)
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            # Update incident
            incident = await state_manager.incident_service.get_incident(session, incident_id)
            if incident:
                incident.operation_id = operation_id
                await session.commit()
                
                # Fetch operation name
                from features.operations.models import Operation
                from sqlalchemy.future import select
                op = await session.execute(select(Operation).filter(Operation.id == operation_id))
                operation = op.scalars().first()
                op_name = operation.name if operation else operation_id
                
                msg = f"🔗 Incident linked to Operation: *{op_name}* by <@{user_id}>"
                await notification_engine.dispatch_threaded_message(
                    channel_id=channel_id,
                    thread_ts=message_ts,
                    text=msg
                )
                
                if incident.thread_ts and incident.thread_ts != message_ts:
                    await notification_engine.dispatch_threaded_message(
                        channel_id=incident.channel_id,
                        thread_ts=incident.thread_ts,
                        text=msg
                    )
            await session.close()
        except Exception as e:
            logger.error(f"Error linking operation: {e}", exc_info=True)

    @app.view("link_mission_modal")
    async def handle_link_mission_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        incident_id = meta[0]
        channel_id = meta[1]
        message_ts = meta[2]
        mission_id = values["mission_block"]["mission_input"]["selected_option"]["value"]
        
        await ack()
        if mission_id == "none":
            return
            
        user_id = body["user"]["id"]
        from core.state import StateManager
        state_manager = service_registry.get(StateManager)
        notification_engine = service_registry.get(NotificationEngine)
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            incident = await state_manager.incident_service.get_incident(session, incident_id)
            if incident:
                incident.mission_id = mission_id
                await session.commit()
                
                from features.missions.models import Mission
                from sqlalchemy.future import select
                m = await session.execute(select(Mission).filter(Mission.id == mission_id))
                mission = m.scalars().first()
                m_name = mission.name if mission else mission_id
                
                msg = f"🎯 Incident linked to Mission: *{m_name}* by <@{user_id}>"
                await notification_engine.dispatch_threaded_message(
                    channel_id=channel_id,
                    thread_ts=message_ts,
                    text=msg
                )
                
                if incident.thread_ts and incident.thread_ts != message_ts:
                    await notification_engine.dispatch_threaded_message(
                        channel_id=incident.channel_id,
                        thread_ts=incident.thread_ts,
                        text=msg
                    )
            await session.close()
        except Exception as e:
            logger.error(f"Error linking mission: {e}", exc_info=True)

    @app.action("incident_more_actions")
    async def handle_incident_more_actions(ack, body, client):
        await _handle_incident_action(ack, body, client, "overflow")
        
    @app.action("incident_view_timeline")
    async def handle_incident_view_timeline(ack, body, client):
        await ack()
        incident_id = body["actions"][0]["value"]
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            from core.state import StateManager
            state_manager = service_registry.get(StateManager)
            
            from sqlalchemy.future import select
            from features.timeline.models import TimelineEvent
            result = await session.execute(
                select(TimelineEvent)
                .filter(TimelineEvent.incident_id == incident_id)
                .order_by(TimelineEvent.created_at.desc())
            )
            events = list(result.scalars().all())
            
            from infrastructure.slack_blocks.timeline_blocks import build_timeline_blocks
            blocks = build_timeline_blocks(f"Incident: {incident_id}", events)
            
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "Incident Timeline"},
                    "close": {"type": "plain_text", "text": "Close"},
                    "blocks": blocks
                }
            )
            await session.close()
        except Exception as e:
            logger.error(f"Error viewing incident timeline: {e}", exc_info=True)
            
    @app.action("incident_view_evidence")
    async def handle_incident_view_evidence(ack, body, client):
        await ack()
        incident_id = body["actions"][0]["value"]
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            
            from sqlalchemy.future import select
            from features.evidence.models import Evidence
            result = await session.execute(
                select(Evidence)
                .filter(Evidence.incident_id == incident_id)
                .order_by(Evidence.created_at.desc())
            )
            evidence_list = list(result.scalars().all())
            
            from infrastructure.slack_blocks.evidence_blocks import build_evidence_list_blocks
            blocks = build_evidence_list_blocks(f"Incident: {incident_id}", evidence_list)
            
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "Incident Evidence"},
                    "close": {"type": "plain_text", "text": "Close"},
                    "blocks": blocks
                }
            )
            await session.close()
        except Exception as e:
            logger.error(f"Error viewing incident evidence: {e}", exc_info=True)
