from typing import List, Dict, Any
from features.missions.models import Mission
from infrastructure.slack.block_builders.shared_actions import build_quick_actions

def _format_owners(mission: Mission) -> str:
    owners = []
    if mission.assigned_human_ids:
        for uid in mission.assigned_human_ids.split(","):
            if uid:
                owners.append(f"<@{uid}>")
    if mission.assigned_mini_agent_id:
        owners.append(f"🤖 {mission.assigned_mini_agent_id}")
    return ", ".join(owners) if owners else "Unassigned"

def build_mission_list_blocks(missions: List[Mission]) -> List[Dict[str, Any]]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Active Missions 🎯"}
        },
        {"type": "divider"}
    ]
    
    if not missions:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No active missions found."}
        })
        return blocks
        
    for m in missions:
        status_emoji = "🟢" if m.status.name == "RUNNING" else "⚪" if m.status.name == "COMPLETED" else "🟡"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{m.name}* {status_emoji}\n"
                        f"*ID:* `{m.id}` | *Status:* {m.status.name} | *Strategy:* {m.strategy.name}\n"
                        f"*Assigned To:* {_format_owners(m)}"
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Details 🔍", "emoji": True},
                "value": m.id,
                "action_id": "mission_view_details"
            }
        })
        blocks.append({"type": "divider"})
        
    return blocks

def build_mission_detail_blocks(mission: Mission, current_stage: str = "N/A") -> List[Dict[str, Any]]:
    """Builds a detailed dashboard for a single mission."""
    status_emoji = "🟢" if mission.status.name == "RUNNING" else "⚪" if mission.status.name == "COMPLETED" else "🔴" if mission.status.name == "FAILED" else "🟡"
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Mission Dashboard: {mission.name}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*ID:* `{mission.id}`"},
                {"type": "mrkdwn", "text": f"*Status:* {mission.status.name} {status_emoji}"},
                {"type": "mrkdwn", "text": f"*Strategy:* {mission.strategy.name}"},
                {"type": "mrkdwn", "text": f"*Priority:* {mission.priority.name}"},
                {"type": "mrkdwn", "text": f"*Assigned To:* {_format_owners(mission)}"},
                {"type": "mrkdwn", "text": f"*Current Stage:* {current_stage}"}
            ]
        }
    ]
    
    if mission.operation_id or mission.incident_id:
        context_str = []
        if mission.operation_id:
            context_str.append(f"*Operation:* `{mission.operation_id}`")
        if mission.incident_id:
            context_str.append(f"*Incident:* `{mission.incident_id}`")
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": " | ".join(context_str)}]
        })
        
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*Objective:*\n> {mission.objective}"}
    })
    
    if mission.last_execution_time:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Last Execution: {mission.last_execution_time.strftime('%Y-%m-%d %H:%M UTC')}"}]
        })
        
    blocks.append({"type": "divider"})
    blocks.append(build_quick_actions(mission.id, "mission", mission.operation_id))
    
    return blocks
