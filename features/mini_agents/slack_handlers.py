import logging
from typing import Any, Dict, List

from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError

from core.orchestration.registry import AgentRegistry
from core.services import registry as service_registry
from features.mini_agents.exceptions import MiniAgentConfigurationError
from features.mini_agents.service import MiniAgentManagementService
from infrastructure.database import get_db_session
from infrastructure.mcp.registry import MCPRegistry

logger = logging.getLogger("crisispilot.mini_agents.slack_handlers")


def register_mini_agent_handlers(app: AsyncApp) -> None:
    """Registers Slack interactions for Mini-Agent Management."""

    async def _get_service() -> MiniAgentManagementService:
        # In a real app we'd yield safely, but since get_db_session yields,
        # we extract the session for the scope of the slack handler.
        # However, AsyncGenerator requires `anext`.
        session_gen = get_db_session()
        session = await anext(session_gen)
        return MiniAgentManagementService(
            session=session,
            agent_registry=service_registry.get(AgentRegistry),
            mcp_registry=service_registry.get(MCPRegistry)
        )

    def _build_tool_options(mcp_registry: MCPRegistry) -> List[Dict[str, Any]]:
        tools = mcp_registry.get_mcp_capabilities()
        options = []
        for t in tools:
            options.append({
                "text": {"type": "plain_text", "text": t.name, "emoji": True},
                "value": t.name
            })
        return options

    # ---------------------------------------------------------
    # /list-agents
    # ---------------------------------------------------------
    @app.command("/list-agents")
    async def list_agents(ack, respond, command):
        await ack()
        try:
            service = await _get_service()
            agents = await service.repository.get_all(enabled_only=False)
            await service.session.close()

            if not agents:
                await respond("No Mini-Agents currently exist. Use `/create-agent` to build one.")
                return

            blocks = [{"type": "header", "text": {"type": "plain_text", "text": "🤖 Registered Mini-Agents"}}]
            for agent in agents:
                status_emoji = "✅" if agent.is_enabled else "❌"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{status_emoji} {agent.name}*\n_{agent.description}_\n*Role:* {agent.role}\n*Tools:* {', '.join(agent.allowed_tools) if agent.allowed_tools else 'None'}"
                    }
                })
                blocks.append({"type": "divider"})

            await respond(blocks=blocks)
        except Exception as e:
            logger.error(f"Error in /list-agents: {e}", exc_info=True)
            await respond(f"Failed to list agents: {e}")

    # ---------------------------------------------------------
    # /create-agent
    # ---------------------------------------------------------
    @app.command("/create-agent")
    async def create_agent_command(ack, body, client):
        await ack()
        mcp_registry = service_registry.get(MCPRegistry)
        tool_options = _build_tool_options(mcp_registry)

        # Fallback if no tools exist (Slack requires at least 1 option for multi-select)
        if not tool_options:
            tool_options = [{"text": {"type": "plain_text", "text": "No tools available"}, "value": "none"}]

        modal_blocks = [
            {
                "type": "input",
                "block_id": "name_block",
                "element": {"type": "plain_text_input", "action_id": "name_input"},
                "label": {"type": "plain_text", "text": "Agent Name (Unique without spaces)"}
            },
            {
                "type": "input",
                "block_id": "desc_block",
                "element": {"type": "plain_text_input", "action_id": "desc_input"},
                "label": {"type": "plain_text", "text": "Description"}
            },
            {
                "type": "input",
                "block_id": "role_block",
                "element": {"type": "plain_text_input", "action_id": "role_input"},
                "label": {"type": "plain_text", "text": "Role (e.g. Weather Assistant)"}
            },
            {
                "type": "input",
                "block_id": "prompt_block",
                "element": {"type": "plain_text_input", "multiline": True, "action_id": "prompt_input"},
                "label": {"type": "plain_text", "text": "System Prompt"}
            },
            {
                "type": "input",
                "block_id": "tools_block",
                "element": {
                    "type": "multi_static_select",
                    "placeholder": {"type": "plain_text", "text": "Select tools"},
                    "options": tool_options,
                    "action_id": "tools_input"
                },
                "label": {"type": "plain_text", "text": "Allowed Tools"}
            }
        ]

        try:
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "create_agent_modal",
                    "title": {"type": "plain_text", "text": "Create Mini-Agent"},
                    "submit": {"type": "plain_text", "text": "Create"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": modal_blocks
                }
            )
        except SlackApiError as e:
            logger.error(f"Error opening modal: {e}")

    @app.view("create_agent_modal")
    async def handle_create_agent_submission(ack, body, client, view, logger):
        values = view["state"]["values"]

        name = values["name_block"]["name_input"]["value"]
        desc = values["desc_block"]["desc_input"]["value"]
        role = values["role_block"]["role_input"]["value"]
        prompt = values["prompt_block"]["prompt_input"]["value"]

        selected_options = values["tools_block"]["tools_input"].get("selected_options", [])
        allowed_tools = [opt["value"] for opt in selected_options if opt["value"] != "none"]

        data = {
            "name": name,
            "description": desc,
            "role": role,
            "system_prompt": prompt,
            "allowed_tools": allowed_tools,
            "is_enabled": True
        }

        try:
            service = await _get_service()
            await service.create_agent(data)
            await service.session.close()

            await ack()
            # Send DM confirming creation
            user_id = body["user"]["id"]
            await client.chat_postMessage(channel=user_id, text=f"✅ Mini-Agent `{name}` created successfully.")
        except MiniAgentConfigurationError as e:
            await ack(response_action="errors", errors={"name_block": str(e)})
            logger.error(f"Failed to create agent {name}: {e}")
        except Exception as e:
            await ack()
            logger.error(f"Unexpected error in create_agent: {e}")

    # ---------------------------------------------------------
    # /delete-agent
    # ---------------------------------------------------------
    @app.command("/delete-agent")
    async def delete_agent_command(ack, respond, command):
        await ack()
        agent_name = command.get("text", "").strip()
        if not agent_name:
            await respond("Please provide an agent name: `/delete-agent AgentName`")
            return

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Are you sure you want to delete the Mini-Agent `{agent_name}`?"}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Delete Agent"},
                        "style": "danger",
                        "value": agent_name,
                        "action_id": "confirm_delete_agent"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Cancel"},
                        "action_id": "cancel_delete_agent"
                    }
                ]
            }
        ]
        await respond(blocks=blocks)

    @app.action("confirm_delete_agent")
    async def handle_confirm_delete(ack, body, respond):
        await ack()
        agent_name = body["actions"][0]["value"]
        try:
            service = await _get_service()
            success = await service.delete_agent(agent_name)
            await service.session.close()

            if success:
                await respond(f"✅ Mini-Agent `{agent_name}` was successfully deleted.")
            else:
                await respond(f"⚠️ Mini-Agent `{agent_name}` could not be deleted.")
        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
            await respond(f"Failed to delete agent: {e}")

    @app.action("cancel_delete_agent")
    async def handle_cancel_delete(ack, respond):
        await ack()
        await respond("Deletion cancelled.")

    # ---------------------------------------------------------
    # /edit-agent
    # ---------------------------------------------------------
    @app.command("/edit-agent")
    async def edit_agent_command(ack, body, client, respond, command):
        await ack()
        agent_name = command.get("text", "").strip()
        if not agent_name:
            await respond("Please provide an agent name: `/edit-agent AgentName`")
            return

        service = await _get_service()
        agent = await service.repository.get_by_name(agent_name)
        await service.session.close()

        if not agent:
            await respond(f"Agent `{agent_name}` not found.")
            return

        mcp_registry = service_registry.get(MCPRegistry)
        tool_options = _build_tool_options(mcp_registry)

        if not tool_options:
            tool_options = [{"text": {"type": "plain_text", "text": "No tools available"}, "value": "none"}]

        # Match initial options
        initial_tools = []
        for opt in tool_options:
            if opt["value"] in agent.allowed_tools:
                initial_tools.append(opt)

        modal_blocks = [
            {
                "type": "input",
                "block_id": "desc_block",
                "element": {"type": "plain_text_input", "action_id": "desc_input", "initial_value": agent.description},
                "label": {"type": "plain_text", "text": "Description"}
            },
            {
                "type": "input",
                "block_id": "role_block",
                "element": {"type": "plain_text_input", "action_id": "role_input", "initial_value": agent.role or ""},
                "label": {"type": "plain_text", "text": "Role"}
            },
            {
                "type": "input",
                "block_id": "prompt_block",
                "element": {"type": "plain_text_input", "multiline": True, "action_id": "prompt_input", "initial_value": agent.system_prompt},
                "label": {"type": "plain_text", "text": "System Prompt"}
            },
            {
                "type": "input",
                "block_id": "tools_block",
                "element": {
                    "type": "multi_static_select",
                    "placeholder": {"type": "plain_text", "text": "Select tools"},
                    "options": tool_options,
                    "action_id": "tools_input",
                    **({"initial_options": initial_tools} if initial_tools else {})
                },
                "label": {"type": "plain_text", "text": "Allowed Tools"}
            }
        ]

        try:
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "edit_agent_modal",
                    "private_metadata": agent_name,  # Pass name through metadata
                    "title": {"type": "plain_text", "text": "Edit Mini-Agent"},
                    "submit": {"type": "plain_text", "text": "Save"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": modal_blocks
                }
            )
        except SlackApiError as e:
            logger.error(f"Error opening modal: {e}")


    @app.view("edit_agent_modal")
    async def handle_edit_agent_submission(ack, body, client, view, logger):
        agent_name = view["private_metadata"]
        values = view["state"]["values"]

        desc = values["desc_block"]["desc_input"]["value"]
        role = values["role_block"]["role_input"]["value"]
        prompt = values["prompt_block"]["prompt_input"]["value"]

        selected_options = values["tools_block"]["tools_input"].get("selected_options", [])
        allowed_tools = [opt["value"] for opt in selected_options if opt["value"] != "none"]

        update_data = {
            "description": desc,
            "role": role,
            "system_prompt": prompt,
            "allowed_tools": allowed_tools
        }

        try:
            service = await _get_service()
            await service.update_agent(agent_name, update_data)
            await service.session.close()

            await ack()
            user_id = body["user"]["id"]
            await client.chat_postMessage(channel=user_id, text=f"✅ Mini-Agent `{agent_name}` updated successfully.")
        except MiniAgentConfigurationError as e:
            await ack(response_action="errors", errors={"desc_block": str(e)})
        except Exception as e:
            await ack()
            logger.error(f"Unexpected error in edit_agent: {e}")
