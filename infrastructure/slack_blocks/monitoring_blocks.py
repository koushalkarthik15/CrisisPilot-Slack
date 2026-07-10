from typing import List, Dict, Any
from features.monitoring.models import MonitoringProfile
from infrastructure.slack_blocks.shared_actions import build_quick_actions

def build_monitoring_list_blocks(profiles: List[MonitoringProfile]) -> List[Dict[str, Any]]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Active Monitoring Profiles 📡"}
        },
        {"type": "divider"}
    ]
    
    if not profiles:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No active monitoring profiles found."}
        })
        return blocks
        
    for profile in profiles:
        status_emoji = "🟢" if profile.status.name == "ACTIVE" else "⚪"
        risk_emoji = "🔴" if profile.current_situation_state.name == "CRITICAL" else "🟠" if profile.current_situation_state.name == "WARNING" else "🟢"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{profile.name}* {status_emoji}\n"
                        f"*Target:* {profile.region} | *Category:* {profile.monitoring_category.name}\n"
                        f"*State:* {profile.current_situation_state.name} {risk_emoji} | *Risk:* {profile.current_risk_score:.1f}/{profile.risk_threshold:.1f}"
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Dashboard 📊", "emoji": True},
                "value": profile.id,
                "action_id": "monitoring_view_dashboard"
            }
        })
        blocks.append({"type": "divider"})
        
    return blocks

def build_monitoring_dashboard_blocks(profile: MonitoringProfile) -> List[Dict[str, Any]]:
    status_emoji = "🟢" if profile.status.name == "ACTIVE" else "⚪"
    risk_emoji = "🔴" if profile.current_situation_state.name == "CRITICAL" else "🟠" if profile.current_situation_state.name == "WARNING" else "🟢"
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Monitoring Dashboard: {profile.name}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*ID:* `{profile.id}`"},
                {"type": "mrkdwn", "text": f"*Status:* {profile.status.name} {status_emoji}"},
                {"type": "mrkdwn", "text": f"*Category:* {profile.monitoring_category.name}"},
                {"type": "mrkdwn", "text": f"*Target:* {profile.region}"},
                {"type": "mrkdwn", "text": f"*Frequency:* {profile.frequency.name}"},
                {"type": "mrkdwn", "text": f"*Risk Threshold:* {profile.risk_threshold:.1f}"}
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Current Situation State:* {profile.current_situation_state.name} {risk_emoji}\n"
                                             f"*Current Risk Score:* {profile.current_risk_score:.1f}"}
        }
    ]
    
    context_str = []
    if profile.operation_id:
        context_str.append(f"*Linked Operation:* `{profile.operation_id}`")
    if profile.last_scan_at:
        context_str.append(f"*Last Scan:* {profile.last_scan_at.strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        context_str.append(f"*Last Scan:* Pending")
        
    if context_str:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": " | ".join(context_str)}]
        })
        
    blocks.append({"type": "divider"})
    
    if profile.operation_id:
        blocks.append(build_quick_actions(profile.operation_id, "operation"))
        
    # Quick action for stop monitoring and force scan
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Stop Monitoring 🛑", "emoji": True},
                "value": profile.id,
                "action_id": "stop_monitoring_action",
                "style": "danger"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Force Scan (Demo) 🌩️", "emoji": True},
                "value": profile.id,
                "action_id": "force_scan_action"
            }
        ]
    })
    
    return blocks

def build_monitoring_started_blocks(profile: MonitoringProfile, missions: list) -> List[Dict[str, Any]]:
    # Build provisioned resources text
    provisioned_text = "✓ Operation created\n✓ Workflow created\n"
    for m in missions:
        provisioned_text += f"✓ {m.name}\n"
    provisioned_text += "✓ Scheduler registered"
    
    # Fake next scan for UI formatting (or just say 'Pending')
    next_scan_text = "Pending"
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "✅ Monitoring Started"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Monitoring:*\n{profile.name}"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Provisioned Resources*\n{provisioned_text}"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Next Scan:*\n{next_scan_text}"},
                {"type": "mrkdwn", "text": f"*Current State:*\n{profile.current_situation_state.name}"},
                {"type": "mrkdwn", "text": f"*Current Risk:*\n{profile.current_risk_score:.0f}"}
            ]
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Dashboard", "emoji": True},
                    "value": profile.id,
                    "action_id": "monitoring_view_dashboard"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Timeline", "emoji": True},
                    "value": profile.operation_id,
                    "action_id": "timeline_view_history"
                },
                {
                    "type": "button",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Force Scan (Demo)", "emoji": True},
                    "value": profile.id,
                    "action_id": "force_scan_action"
                }
            ]
        }
    ]
    return blocks
