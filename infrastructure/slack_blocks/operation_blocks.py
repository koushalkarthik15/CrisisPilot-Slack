from typing import Any, Dict, List

from features.operations.models import Operation
from infrastructure.slack_blocks.shared_actions import build_quick_actions


def build_operation_list_blocks(operations: List[Operation]) -> List[Dict[str, Any]]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Active Operations 🌐"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Here are the currently active operations in CrisisPilot."}
        },
        {"type": "divider"}
    ]

    if not operations:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No active operations found."}
        })
        return blocks

    for op in operations:
        status_emoji = "🟢" if op.status.name == "ACTIVE" else "🟡" if op.status.name == "PAUSED" else "⚪"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{op.name}* {status_emoji}\n"
                        f"*ID:* `{op.id}` | *Category:* {op.category.name} | *Status:* {op.status.name}\n"
                        f"*Priority:* {op.priority.name}\n"
                        f"> {op.description[:150]}{'...' if len(op.description) > 150 else ''}"
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Dashboard 📊", "emoji": True},
                "value": op.id,
                "action_id": "op_view_dashboard"
            }
        })
        blocks.append({"type": "divider"})

    return blocks

def build_operation_detail_blocks(operation: Operation, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Builds a detailed dashboard for a single operation."""
    status_emoji = "🟢" if operation.status.name == "ACTIVE" else "⚪"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Operation Dashboard: {operation.name}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*ID:* `{operation.id}`"},
                {"type": "mrkdwn", "text": f"*Status:* {operation.status.name} {status_emoji}"},
                {"type": "mrkdwn", "text": f"*Category:* {operation.category.name}"},
                {"type": "mrkdwn", "text": f"*Priority:* {operation.priority.name}"},
                {"type": "mrkdwn", "text": f"*Started:* {operation.started_at.strftime('%Y-%m-%d %H:%M UTC') if operation.started_at else 'N/A'}"},
                {"type": "mrkdwn", "text": f"*Created By:* <@{operation.created_by}>"}
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Description:*\n> {operation.description}"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Operational Statistics* 📈"},
            "fields": [
                {"type": "mrkdwn", "text": f"🚨 *Active Incidents:* {stats.get('active_incidents', 0)}"},
                {"type": "mrkdwn", "text": f"🎯 *Active Missions:* {stats.get('active_missions', 0)}"},
                {"type": "mrkdwn", "text": f"⚙️ *Active Workflows:* {stats.get('active_workflows', 0)}"},
                {"type": "mrkdwn", "text": f"🕒 *Timeline Events:* {stats.get('timeline_events', 0)}"}
            ]
        },
        build_quick_actions(operation.id, "operation", entity_status=operation.status.name)
    ]

    return blocks
