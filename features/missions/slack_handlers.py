import logging

from slack_bolt.async_app import AsyncApp

from core.notifications import NotificationEngine
from core.orchestration.registry import AgentRegistry
from core.services import registry as service_registry
from core.state import StateManager
from features.missions.domain import ExecutionStrategy, MissionPriority
from features.missions.schemas import MissionAssignment, MissionCreate
from infrastructure.database import get_db_session
from infrastructure.slack_blocks import (
    build_mission_detail_blocks,
    build_mission_list_blocks,
)

logger = logging.getLogger("crisispilot.missions.slack_handlers")

def register_mission_handlers(app: AsyncApp) -> None:

    @app.command("/missions")
    @app.command("/list-missions")
    async def list_missions_command(ack, body, client):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            # Use repository to fetch recently created missions
            from sqlalchemy.future import select

            from features.missions.models import Mission
            result = await session.execute(select(Mission).order_by(Mission.created_at.desc()).limit(20))
            missions = list(result.scalars().all())

            blocks = build_mission_list_blocks(missions)
            await client.chat_postMessage(channel=channel_id, text="Active Missions", blocks=blocks)

            await session.close()
        except Exception as e:
            logger.error(f"Error listing missions: {e}", exc_info=True)

    @app.command("/create-mission")
    async def create_mission_command(ack, body, client):
        await ack()
        try:
            channel_id = body.get("channel_id")
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "create_mission_modal",
                    "private_metadata": channel_id,
                    "title": {"type": "plain_text", "text": "Create Mission"},
                    "submit": {"type": "plain_text", "text": "Create"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "name_block",
                            "element": {"type": "plain_text_input", "action_id": "name_input"},
                            "label": {"type": "plain_text", "text": "Mission Name"}
                        },
                        {
                            "type": "input",
                            "block_id": "strategy_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select strategy"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": s.name}, "value": s.name}
                                    for s in ExecutionStrategy
                                ],
                                "action_id": "strategy_input"
                            },
                            "label": {"type": "plain_text", "text": "Execution Strategy"}
                        },
                        {
                            "type": "input",
                            "block_id": "priority_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select priority"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": p.name}, "value": p.name}
                                    for p in MissionPriority
                                ],
                                "action_id": "priority_input"
                            },
                            "label": {"type": "plain_text", "text": "Priority"}
                        },
                        {
                            "type": "input",
                            "block_id": "obj_block",
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "obj_input"},
                            "label": {"type": "plain_text", "text": "Objective"}
                        },
                        {
                            "type": "input",
                            "block_id": "op_block",
                            "optional": True,
                            "element": {"type": "plain_text_input", "action_id": "op_input"},
                            "label": {"type": "plain_text", "text": "Operation ID (Optional)"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening create mission modal: {e}")

    @app.view("create_mission_modal")
    async def handle_create_mission_submission(ack, body, view, client):
        values = view["state"]["values"]
        channel_id = view["private_metadata"]
        user_id = body["user"]["id"]

        name = values["name_block"]["name_input"]["value"]
        strategy_str = values["strategy_block"]["strategy_input"]["selected_option"]["value"]
        priority_str = values["priority_block"]["priority_input"]["selected_option"]["value"]
        obj = values["obj_block"]["obj_input"]["value"]
        op_id = values["op_block"]["op_input"]["value"]

        await ack()

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            m_in = MissionCreate(
                name=name,
                objective=obj,
                strategy=ExecutionStrategy[strategy_str],
                priority=MissionPriority[priority_str],
                operation_id=op_id if op_id else None
            )

            mission = await state_manager.mission_service.create_mission(session, m_in, created_by=user_id)
            await session.commit()

            blocks = build_mission_detail_blocks(mission, viewer_id=user_id)
            await client.chat_postMessage(channel=channel_id, text=f"Mission created: {mission.name}", blocks=blocks)

            await session.close()
        except Exception as e:
            logger.error(f"Error submitting mission modal: {e}", exc_info=True)

    @app.command("/assign-mission")
    async def assign_mission_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        mission_id = command.get("text", "").strip().strip("`")

        if not mission_id:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text="Please provide a mission ID. Example: `/assign-mission MS-123`")
            return

        message_ts = body.get("message", {}).get("ts", "")

        try:
            agent_registry = service_registry.get(AgentRegistry)
            agents = agent_registry.list_agents()
            agent_options = [{"text": {"type": "plain_text", "text": f"🤖 {a}"}, "value": a} for a in agents]

            if not agent_options:
                await client.chat_postEphemeral(channel=channel_id, user=user_id, text="No Mini-Agents available in the registry.")
                return

            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "assign_mission_modal",
                    "private_metadata": f"{channel_id}|{mission_id}|{message_ts}",
                    "title": {"type": "plain_text", "text": "Assign Mission"},
                    "submit": {"type": "plain_text", "text": "Assign"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "human_block",
                            "optional": True,
                            "element": {
                                "type": "multi_users_select",
                                "placeholder": {"type": "plain_text", "text": "Select Humans"},
                                "action_id": "human_input"
                            },
                            "label": {"type": "plain_text", "text": "Assign Human Operators"}
                        },
                        {
                            "type": "input",
                            "block_id": "agent_block",
                            "optional": True,
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select Agent"},
                                "options": agent_options,
                                "action_id": "agent_input"
                            },
                            "label": {"type": "plain_text", "text": "Assign Mini-Agent"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening assign mission modal: {e}")

    @app.view("assign_mission_modal")
    async def handle_assign_mission_submission(ack, body, view, client):
        values = view["state"]["values"]
        meta = view["private_metadata"].split("|")
        channel_id = meta[0]
        mission_id = meta[1]
        message_ts = meta[2] if len(meta) > 2 and meta[2] else None
        user_id = body["user"]["id"]

        human_ids = values.get("human_block", {}).get("human_input", {}).get("selected_users", [])
        agent_option = values.get("agent_block", {}).get("agent_input", {}).get("selected_option")
        agent_id = agent_option["value"] if agent_option else None

        await ack()

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            assignment = MissionAssignment(
                assigned_mini_agent_id=agent_id,
                assigned_human_ids=human_ids if human_ids else None
            )
            mission = await state_manager.assign_mission(session, mission_id, assignment)
            await session.commit()

            if mission:
                blocks = build_mission_detail_blocks(mission)
                if message_ts:
                    try:
                        await client.chat_update(channel=channel_id, ts=message_ts, text=f"Mission assigned: {mission.name}", blocks=blocks)
                    except Exception as e:
                        logger.warning(f"Could not update original message: {e}")
                else:
                    await client.chat_postMessage(channel=channel_id, text=f"Mission assigned: {mission.name}", blocks=blocks)

                # Notify assigned humans via DM
                if human_ids:
                    notification_engine = service_registry.get(NotificationEngine)
                    for uid in human_ids:
                        try:
                                dm_blocks = build_mission_detail_blocks(mission, viewer_id=uid)
                                await notification_engine.dispatch_direct_message(
                                    user_id=uid,
                                    text=f"🔔 You have been assigned to Mission: {mission.name}",
                                    blocks=dm_blocks
                                )
                        except Exception as dm_e:
                            logger.error(f"Failed to DM user {uid}: {dm_e}")
            else:
                await client.chat_postMessage(channel=channel_id, text="Mission not found.")

            await session.close()
        except Exception as e:
            logger.error(f"Error assigning mission: {e}", exc_info=True)

    @app.action("mission_assign")
    async def handle_mission_assign_action(ack, body, client):
        await ack()
        val = body["actions"][0]["value"]
        mission_id = val.split("_")[1]
        channel_id = body["channel"]["id"]
        message_ts = body.get("message", {}).get("ts", "")

        try:
            agent_registry = service_registry.get(AgentRegistry)
            agents = agent_registry.list_agents()
            agent_options = [{"text": {"type": "plain_text", "text": f"🤖 {a}"}, "value": a} for a in agents]

            blocks = [
                {
                    "type": "input",
                    "block_id": "human_block",
                    "optional": True,
                    "element": {
                        "type": "multi_users_select",
                        "placeholder": {"type": "plain_text", "text": "Select Humans"},
                        "action_id": "human_input"
                    },
                    "label": {"type": "plain_text", "text": "Assign Human Operators"}
                }
            ]

            if agent_options:
                blocks.append({
                    "type": "input",
                    "block_id": "agent_block",
                    "optional": True,
                    "element": {
                        "type": "static_select",
                        "placeholder": {"type": "plain_text", "text": "Select Agent"},
                        "options": agent_options,
                        "action_id": "agent_input"
                    },
                    "label": {"type": "plain_text", "text": "Assign Mini-Agent"}
                })

            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "assign_mission_modal",
                    "private_metadata": f"{channel_id}|{mission_id}",
                    "title": {"type": "plain_text", "text": "Assign Mission"},
                    "submit": {"type": "plain_text", "text": "Assign"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": blocks
                }
            )
        except Exception as e:
            logger.error(f"Error opening assign mission modal from action: {e}", exc_info=True)

    @app.action("op_create_mission")
    async def handle_op_create_mission(ack, body, client):
        # We extract op_id from value which is "operation_OP-123"
        await ack()
        val = body["actions"][0]["value"]
        op_id = val.split("_")[1]
        channel_id = body["channel"]["id"]

        try:
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "create_mission_modal",
                    "private_metadata": channel_id,
                    "title": {"type": "plain_text", "text": "Create Mission"},
                    "submit": {"type": "plain_text", "text": "Create"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "name_block",
                            "element": {"type": "plain_text_input", "action_id": "name_input"},
                            "label": {"type": "plain_text", "text": "Mission Name"}
                        },
                        {
                            "type": "input",
                            "block_id": "strategy_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select strategy"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": s.name}, "value": s.name}
                                    for s in ExecutionStrategy
                                ],
                                "action_id": "strategy_input"
                            },
                            "label": {"type": "plain_text", "text": "Execution Strategy"}
                        },
                        {
                            "type": "input",
                            "block_id": "priority_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select priority"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": p.name}, "value": p.name}
                                    for p in MissionPriority
                                ],
                                "action_id": "priority_input"
                            },
                            "label": {"type": "plain_text", "text": "Priority"}
                        },
                        {
                            "type": "input",
                            "block_id": "obj_block",
                            "element": {"type": "plain_text_input", "multiline": True, "action_id": "obj_input"},
                            "label": {"type": "plain_text", "text": "Objective"}
                        },
                        {
                            "type": "input",
                            "block_id": "op_block",
                            "element": {"type": "plain_text_input", "initial_value": op_id, "action_id": "op_input"},
                            "label": {"type": "plain_text", "text": "Operation ID"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening create mission modal from action: {e}", exc_info=True)

    @app.action("mission_view_details")
    async def handle_mission_view_details(ack, body, client):
        await ack()
        mission_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            mission = await state_manager.mission_service.get_mission(session, mission_id)
            if mission:
                user_id = body["user"]["id"]
                blocks = build_mission_detail_blocks(mission, viewer_id=user_id)
                await client.chat_postMessage(channel=channel_id, text=f"Mission Dashboard: {mission.name}", blocks=blocks)

            await session.close()
        except Exception as e:
            logger.error(f"Error showing mission details: {e}", exc_info=True)

    @app.command("/run-mission")
    async def run_mission_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        mission_id = command.get("text", "").strip()

        if not mission_id:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text="Please provide a mission ID. Example: `/run-mission MS-123`")
            return

        await _execute_mission(client, channel_id, mission_id)

    @app.action("mission_execute")
    async def handle_mission_execute_action(ack, body, client):
        await ack()
        channel_id = body["channel"]["id"]
        val = body["actions"][0]["value"]
        mission_id = val.split("_")[1]

        message_ts = body.get("message", {}).get("ts")

        await _execute_mission(client, channel_id, mission_id, original_ts=message_ts)

    async def _execute_mission(client, channel_id, mission_id, original_ts=None):
        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            # Post loading message
            loading_msg = await client.chat_postMessage(channel=channel_id, text=f"⚡ Executing mission `{mission_id}`...")
            ts = loading_msg.get("ts")

            mission = await state_manager.execute_mission_manually(session, mission_id)
            await session.commit()

            # Passing None for viewer_id because this is a general update, it will hide execute
            blocks = build_mission_detail_blocks(mission)

            # Update the loading message
            await client.chat_update(channel=channel_id, ts=ts, text=f"Mission execution completed: {mission.name}", blocks=blocks)

            if original_ts:
                try:
                    await client.chat_update(channel=channel_id, ts=original_ts, text=f"Mission Dashboard: {mission.name}", blocks=blocks)
                except Exception as update_err:
                    logger.warning(f"Could not update original mission message: {update_err}")

            await session.close()
        except Exception as e:
            logger.error(f"Error executing mission {mission_id}: {e}", exc_info=True)
            await client.chat_postMessage(channel=channel_id, text=f"❌ Failed to execute mission `{mission_id}`: {str(e)}")
