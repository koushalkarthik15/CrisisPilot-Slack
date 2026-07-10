from typing import List, Dict, Any
from itertools import groupby
from features.timeline.models import TimelineEvent

def build_timeline_blocks(entity_id: str, events: List[TimelineEvent]) -> List[Dict[str, Any]]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Operational Timeline 🕒"}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"*Entity:* `{entity_id}`"}]
        },
        {"type": "divider"}
    ]
    
    if not events:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No timeline events recorded yet."}
        })
        return blocks
        
    # Group events by date
    # Events should be ordered descending (newest first) by the repository
    events_by_date = groupby(events, key=lambda e: e.timestamp.strftime("%Y-%m-%d"))
    
    for date_str, date_events in events_by_date:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{date_str}*"}
        })
        
        for event in date_events:
            time_str = event.timestamp.strftime("%H:%M UTC")
            severity_emoji = "🔴" if event.severity.name == "CRITICAL" else "🟠" if event.severity.name == "ERROR" else "🟡" if event.severity.name == "WARNING" else "🔵"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"`{time_str}` {severity_emoji} *{event.event_type.name}* (_{event.source.name}_)\n"
                            f"{event.description}"
                }
            })
            
        blocks.append({"type": "divider"})
        
    return blocks
