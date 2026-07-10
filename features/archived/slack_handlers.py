import logging
from slack_bolt.async_app import AsyncApp
from infrastructure.database import get_db_session
from core.services import registry as service_registry
from core.state import StateManager

logger = logging.getLogger("crisispilot.archived.slack_handlers")

def register_archived_handlers(app: AsyncApp) -> None:
    @app.command("/list-archived")
    @app.command("/archived")
    async def list_archived_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        text = command.get("text", "").strip().lower()
        
        target = text if text in ["incidents", "operations", "missions"] else "all"
        
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)
            
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🗄️ Archived Entities"}
                },
                {"type": "divider"}
            ]
            
            found_any = False
            
            if target in ["all", "incidents"]:
                from sqlalchemy.future import select
                from features.incident_management.models import Incident
                from features.incident_management.domain import IncidentStatus
                
                result = await session.execute(
                    select(Incident)
                    .where(Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.ARCHIVED]))
                    .order_by(Incident.created_at.desc())
                    .limit(5)
                )
                incidents = result.scalars().all()
                if incidents:
                    found_any = True
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Incidents*"}})
                    for inc in incidents:
                        blocks.append({
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*{inc.title}*\nID: `{inc.id}` | Status: {inc.status.name}"},
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Details 🔍", "emoji": True},
                                "value": f"{inc.id}",
                                "action_id": "global_view_timeline" # Repurpose view timeline for viewing archived
                            }
                        })
            
            if target in ["all", "operations"]:
                from features.operations.models import Operation
                from features.operations.domain import OperationStatus
                from sqlalchemy.future import select
                
                result = await session.execute(
                    select(Operation)
                    .where(Operation.status.in_([OperationStatus.COMPLETED, OperationStatus.ARCHIVED]))
                    .order_by(Operation.created_at.desc())
                    .limit(5)
                )
                ops = result.scalars().all()
                if ops:
                    found_any = True
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Operations*"}})
                    for op in ops:
                        blocks.append({
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*{op.name}*\nID: `{op.id}` | Status: {op.status.name}"},
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Details 🔍", "emoji": True},
                                "value": f"{op.id}", # Needs to be just ID because op_view_dashboard expects ID
                                "action_id": "op_view_dashboard"
                            }
                        })
                        
            if target in ["all", "missions"]:
                from features.missions.models import Mission
                from features.missions.domain import MissionStatus
                from sqlalchemy.future import select
                
                result = await session.execute(
                    select(Mission)
                    .where(Mission.status.in_([MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED]))
                    .order_by(Mission.created_at.desc())
                    .limit(5)
                )
                missions = result.scalars().all()
                if missions:
                    found_any = True
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Missions*"}})
                    for m in missions:
                        blocks.append({
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*{m.name}*\nID: `{m.id}` | Status: {m.status.name}"},
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Details 🔍", "emoji": True},
                                "value": f"mission_{m.id}", # mission_view_details expects mission_id
                                "action_id": "mission_view_details"
                            }
                        })
            
            if not found_any:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "No archived entities found."}})
                
            await client.chat_postMessage(channel=channel_id, text="Archived Entities", blocks=blocks)
            
            await session.close()
        except Exception as e:
            logger.error(f"Error listing archived entities: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Error listing archived entities: {e}")
