from typing import List, Dict, Any
from features.analytics.schemas import OperationalSummary

def format_operational_summary_blocks(summary: OperationalSummary) -> List[Dict[str, Any]]:
    """Transforms OperationalSummary into a rich Slack Block Kit array."""
    
    blocks = []
    
    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "📊 CrisisPilot Operational Summary",
            "emoji": True
        }
    })
    blocks.append({"type": "divider"})
    
    # Incidents
    severity_text = " | ".join([f"{k}: {v}" for k, v in summary.incidents.severity_distribution.items()])
    if not severity_text:
        severity_text = "No incidents recorded"
        
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*🚨 Incident Metrics*\n"
                    f"• *Active Incidents:* {summary.incidents.total_active}\n"
                    f"• *Created Today:* {summary.incidents.newly_created_today}\n"
                    f"• *Resolved:* {summary.incidents.total_resolved}\n"
                    f"• *Severity Dist:* {severity_text}"
        }
    })
    
    # Operations
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*⚙️ Operation Metrics*\n"
                    f"• *Active Operations:* {summary.operations.total_active}\n"
                    f"• *Completed:* {summary.operations.completed}"
        }
    })
    
    # Missions
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*🎯 Mission Metrics*\n"
                    f"• *Active Missions:* {summary.missions.total_active}\n"
                    f"• *Completed:* {summary.missions.completed}\n"
                    f"• *Failed:* {summary.missions.failed}"
        }
    })
    
    # Recommendations
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*🤖 HITL Recommendations*\n"
                    f"• *Pending Review:* {summary.recommendations.total_pending}\n"
                    f"• *Approved:* {summary.recommendations.total_approved}\n"
                    f"• *Rejected:* {summary.recommendations.total_rejected}\n"
                    f"• *Approval Rate:* {summary.recommendations.approval_rate_percent}%"
        }
    })
    
    # Intelligence
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*🌍 Intelligence & Monitoring*\n"
                    f"• *Active Watchlists:* {summary.watchlists.total_enabled}\n"
                    f"• *News Articles Deduplicated:* {summary.watchlists.articles_processed}\n"
                    f"• *Mini-Agents Enabled:* {summary.mini_agents.total_enabled} (of {summary.mini_agents.total_registered})\n"
                    f"• *MCP Executions:* {summary.mcp['status']}"
        }
    })
    
    # LLM Usage
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*🧠 LLM Provider Usage (Today)*\n"
                    f"• *Requests:* {summary.llm.requests_today} / {summary.llm.max_requests_per_day}\n"
                    f"• *Tokens Consumed:* {summary.llm.tokens_today} / {summary.llm.max_tokens_per_day}\n"
                    f"• *Active Concurrent:* {summary.llm.concurrent_requests}"
        }
    })
    
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "Data aggregated securely from internal SQLite operational repositories."
            }
        ]
    })
    
    return blocks
