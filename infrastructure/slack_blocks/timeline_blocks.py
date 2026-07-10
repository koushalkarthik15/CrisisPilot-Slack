from itertools import groupby
from typing import Any, Dict, List

from features.timeline.models import TimelineEvent


def build_timeline_blocks(entity_id: str, events: List[TimelineEvent]) -> List[Dict[str, Any]]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Operational Timeline 🕒"}
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

    # Group events by date (assuming they are already sorted descending)
    events_by_date = groupby(events, key=lambda e: e.created_at.strftime("%Y-%m-%d"))

    for date_str, date_events in events_by_date:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{date_str}*"}
        })

        for event in date_events:
            time_str = event.created_at.strftime("%H:%M UTC")

            # Dynamic Emojis
            if event.source.name == "SYSTEM":
                source_emoji = "⚙️"
            elif event.source.name == "USER":
                source_emoji = "👤"
            elif event.source.name == "AGENT":
                source_emoji = "🤖"
            else:
                source_emoji = "🔹"

            severity_emoji = "🚨" if event.severity.name == "CRITICAL" else "🔴" if event.severity.name == "ERROR" else "🟠" if event.severity.name == "WARNING" else "🔵"

            # Format title nicely
            title_text = event.event_type.name.replace("_", " ").title()
            actor_text = f"by <@{event.actor_id}>" if event.actor_id else ""

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"`{time_str}` {severity_emoji} *{title_text}* {source_emoji} {actor_text}\n> {event.description}"
                }
            })

        blocks.append({"type": "divider"})

    return blocks
