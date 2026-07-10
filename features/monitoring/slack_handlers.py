import logging

from slack_bolt.async_app import AsyncApp

from core.services import registry as service_registry
from core.state import StateManager
from features.monitoring.domain import MonitoringCategory, MonitoringFrequency
from features.monitoring.schemas import MonitoringProfileCreate
from infrastructure.database import get_db_session
from infrastructure.slack_blocks.monitoring_blocks import (
    build_monitoring_dashboard_blocks,
    build_monitoring_list_blocks,
)

logger = logging.getLogger("crisispilot.monitoring.slack_handlers")

def register_monitoring_handlers(app: AsyncApp) -> None:

    @app.command("/monitoring")
    @app.command("/list-monitoring")
    async def list_monitoring_command(ack, body, client):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        logger.info(f"Received /monitoring command from {user_id}")

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)

            state_manager = service_registry.get(StateManager)
            profiles = await state_manager.monitoring_service.list_active_profiles(session)

            blocks = build_monitoring_list_blocks(profiles)
            await client.chat_postMessage(channel=channel_id, text="Active Monitoring Profiles", blocks=blocks)

            await session.close()
        except Exception as e:
            logger.error(f"Error listing monitoring profiles: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Error listing monitoring profiles: {e}")

    @app.command("/monitor")
    @app.command("/start-monitoring")
    async def start_monitoring_command(ack, body, client):
        await ack()
        try:
            channel_id = body.get("channel_id")
            await client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "create_monitoring_modal",
                    "private_metadata": channel_id,
                    "title": {"type": "plain_text", "text": "Start Monitoring"},
                    "submit": {"type": "plain_text", "text": "Start"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "name_block",
                            "element": {"type": "plain_text_input", "action_id": "name_input"},
                            "label": {"type": "plain_text", "text": "Monitoring Name"}
                        },
                        {
                            "type": "input",
                            "block_id": "region_block",
                            "element": {"type": "plain_text_input", "action_id": "region_input"},
                            "label": {"type": "plain_text", "text": "Region / Target"}
                        },
                        {
                            "type": "input",
                            "block_id": "category_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select threat type"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": cat.name}, "value": cat.name}
                                    for cat in MonitoringCategory
                                ],
                                "action_id": "category_input"
                            },
                            "label": {"type": "plain_text", "text": "Threat Type"}
                        },
                        {
                            "type": "input",
                            "block_id": "template_block",
                            "optional": True,
                            "element": {"type": "plain_text_input", "action_id": "template_input", "placeholder": {"type": "plain_text", "text": "e.g. Flood Response"}},
                            "label": {"type": "plain_text", "text": "Monitoring Template"}
                        },
                        {
                            "type": "input",
                            "block_id": "frequency_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select frequency"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": freq.name}, "value": freq.name}
                                    for freq in MonitoringFrequency
                                ],
                                "action_id": "frequency_input"
                            },
                            "label": {"type": "plain_text", "text": "Frequency"}
                        },
                        {
                            "type": "input",
                            "block_id": "custom_freq_block",
                            "optional": True,
                            "element": {"type": "plain_text_input", "action_id": "custom_freq_input", "placeholder": {"type": "plain_text", "text": "e.g. Every Tuesday at 9am"}},
                            "label": {"type": "plain_text", "text": "Custom Frequency (if CUSTOM selected)"}
                        },
                        {
                            "type": "input",
                            "block_id": "threshold_block",
                            "element": {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "Select risk threshold"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": "High (75)"}, "value": "75"},
                                    {"text": {"type": "plain_text", "text": "Mid (50)"}, "value": "50"},
                                    {"text": {"type": "plain_text", "text": "Low (25)"}, "value": "25"}
                                ],
                                "action_id": "threshold_input"
                            },
                            "label": {"type": "plain_text", "text": "Risk Threshold"}
                        },
                        {
                            "type": "input",
                            "block_id": "notifications_block",
                            "element": {"type": "plain_text_input", "action_id": "notifications_input", "initial_value": "#operations"},
                            "label": {"type": "plain_text", "text": "Notification Targets"}
                        },
                        {
                            "type": "input",
                            "block_id": "start_block",
                            "optional": True,
                            "element": {
                                "type": "checkboxes",
                                "options": [
                                    {
                                        "text": {"type": "plain_text", "text": "Start Immediately"},
                                        "value": "true"
                                    }
                                ],
                                "initial_options": [
                                    {
                                        "text": {"type": "plain_text", "text": "Start Immediately"},
                                        "value": "true"
                                    }
                                ],
                                "action_id": "start_input"
                            },
                            "label": {"type": "plain_text", "text": "Execution"}
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error opening create monitoring modal: {e}")

    @app.view("create_monitoring_modal")
    async def handle_create_monitoring_submission(ack, body, view, client):
        values = view["state"]["values"]
        channel_id = view["private_metadata"]
        user_id = body["user"]["id"]

        name = values["name_block"]["name_input"]["value"]
        region = values["region_block"]["region_input"]["value"]
        category_str = values["category_block"]["category_input"]["selected_option"]["value"]
        template_val = values["template_block"]["template_input"]["value"]
        frequency_str = values["frequency_block"]["frequency_input"]["selected_option"]["value"]
        custom_freq_val = values["custom_freq_block"]["custom_freq_input"]["value"] if "custom_freq_block" in values else None

        # Safely parse threshold from static select
        threshold_raw = values["threshold_block"]["threshold_input"]["selected_option"]["value"]
        threshold_val = float(threshold_raw)

        notifications_val = values["notifications_block"]["notifications_input"]["value"]

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            # Validate duplicate name before acknowledging
            existing = await state_manager.monitoring_service.repository.get_by_name(session, name)
            if existing:
                await ack(response_action="errors", errors={"name_block": "A Monitoring Profile with this name already exists. Please choose a different name."})
                await session.close()
                return

            await ack()

            profile_in = MonitoringProfileCreate(
                name=name,
                region=region,
                monitoring_category=MonitoringCategory[category_str],
                frequency=MonitoringFrequency[frequency_str],
                custom_frequency=custom_freq_val,
                risk_threshold=threshold_val,
                notification_targets=notifications_val,
                workflow_template=template_val,
                description=f"Automated monitoring for {region} ({category_str})"
            )

            profile = await state_manager.monitoring_service.create_monitoring_profile(session, state_manager, profile_in, created_by=user_id)

            # Fetch missions to show in the start message
            missions = await state_manager.mission_service.repository.list_by_operation(session, profile.operation_id)
            await session.commit()

            from infrastructure.slack_blocks.monitoring_blocks import (
                build_monitoring_started_blocks,
            )
            blocks = build_monitoring_started_blocks(profile, missions)

            await client.chat_postMessage(
                channel=channel_id,
                text=f"Monitoring Profile started: {profile.name}",
                blocks=blocks
            )

            await session.close()
        except Exception as e:
            logger.error(f"Error submitting monitoring modal: {e}", exc_info=True)

    @app.action("monitoring_view_dashboard")
    async def handle_monitoring_view_dashboard(ack, body, client):
        await ack()
        profile_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            profile = await state_manager.monitoring_service.get_profile(session, profile_id)
            if profile:
                blocks = build_monitoring_dashboard_blocks(profile)
                await client.chat_postMessage(channel=channel_id, text=f"Monitoring Dashboard: {profile.name}", blocks=blocks)

            await session.close()
        except Exception as e:
            logger.error(f"Error showing monitoring dashboard: {e}", exc_info=True)

    @app.command("/stop-monitoring")
    async def stop_monitoring_command(ack, body, client, command):
        await ack()
        channel_id = body.get("channel_id")
        user_id = body.get("user_id")
        profile_id = command.get("text", "").strip()

        if not profile_id:
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text="Please provide a monitoring profile ID. Example: `/stop-monitoring MP-1234`")
            return

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            from features.monitoring.domain import MonitoringStatus
            await state_manager.monitoring_service.transition_status(session, profile_id, MonitoringStatus.STOPPED)
            await session.commit()

            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Monitoring profile {profile_id} stopped.")
            await session.close()
        except Exception as e:
            logger.error(f"Error stopping monitoring profile {profile_id}: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Failed to stop monitoring profile: {e}")

    @app.action("stop_monitoring_action")
    async def handle_stop_monitoring_action(ack, body, client):
        await ack()
        profile_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            from features.monitoring.domain import MonitoringStatus
            await state_manager.monitoring_service.transition_status(session, profile_id, MonitoringStatus.STOPPED)
            await session.commit()

            await client.chat_postEphemeral(channel=channel_id, user=user_id, text="Monitoring profile stopped.")

            # Refresh Dashboard
            profile = await state_manager.monitoring_service.get_profile(session, profile_id)
            blocks = build_monitoring_dashboard_blocks(profile)
            await client.chat_update(channel=channel_id, ts=body["message"]["ts"], text="Monitoring Dashboard", blocks=blocks)

            await session.close()
        except Exception as e:
            logger.error(f"Error stopping monitoring profile {profile_id}: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Failed to stop monitoring profile: {e}")

    @app.action("force_scan_action")
    async def handle_force_scan_action(ack, body, client):
        await ack()
        profile_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]

        await client.chat_postEphemeral(channel=channel_id, user=user_id, text="Triggering simulated critical scan for demo purposes...")

        try:
            session_gen = get_db_session()
            session = await anext(session_gen)
            state_manager = service_registry.get(StateManager)

            # Reset risk score so the threshold is crossed again for the demo
            profile = await state_manager.monitoring_service.repository.get(session, profile_id)
            if profile:
                from features.monitoring.schemas import MonitoringProfileUpdate
                update_data = MonitoringProfileUpdate(current_risk_score=0.0)

                # Guarantee the channel we are in is a notification target so we can see the results
                targets = profile.notification_targets or ""
                if channel_id not in targets:
                    update_data.notification_targets = f"{targets},{channel_id}" if targets else channel_id

                await state_manager.monitoring_service.repository.update(
                    session, profile_id, update_data
                )

            # Simulate critical observations to trigger the risk threshold
            simulated_observations = [
                {"type": "WEATHER_ALERT", "severity": 100.0, "detail": "Major flooding detected in primary region. Evacuation recommended."},
                {"type": "NEWS_REPORT", "severity": 90.0, "detail": "Local infrastructure taking heavy damage from rising water levels."}
            ]

            profile = await state_manager.monitoring_service.process_scan_results(
                session, state_manager, profile_id, simulated_observations
            )
            await session.commit()

            # Refresh Dashboard
            from infrastructure.slack_blocks.monitoring_blocks import (
                build_monitoring_dashboard_blocks,
            )
            blocks = build_monitoring_dashboard_blocks(profile)
            await client.chat_update(channel=channel_id, ts=body["message"]["ts"], text="Monitoring Dashboard", blocks=blocks)

            await session.close()
        except Exception as e:
            logger.error(f"Error simulating scan for profile {profile_id}: {e}", exc_info=True)
            await client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"Failed to simulate scan: {e}")
