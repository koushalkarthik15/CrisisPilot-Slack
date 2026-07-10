from typing import List, Dict, Any
from features.evidence.models import Evidence

def build_evidence_blocks(entity_id: str, evidence_list: List[Evidence]) -> List[Dict[str, Any]]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Evidence Board 📁"}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"*Entity:* `{entity_id}`"}]
        },
        {"type": "divider"}
    ]
    
    if not evidence_list:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No evidence collected yet."}
        })
        return blocks
        
    for ev in evidence_list:
        icon = "📄"
        if ev.evidence_type.name == "IMAGE":
            icon = "🖼️"
        elif ev.evidence_type.name == "VIDEO":
            icon = "🎥"
        elif ev.evidence_type.name == "LINK":
            icon = "🔗"
        elif ev.evidence_type.name == "LOCATION":
            icon = "📍"
        elif ev.evidence_type.name == "COMMUNICATION":
            icon = "💬"
            
        fields = [
            {"type": "mrkdwn", "text": f"*Type:* {ev.evidence_type.name}"},
            {"type": "mrkdwn", "text": f"*Source:* {ev.source}"},
            {"type": "mrkdwn", "text": f"*Submitted By:* <@{ev.submitted_by}>" if ev.submitted_by else "System"}
        ]
        
        if ev.confidence_score is not None:
            fields.append({"type": "mrkdwn", "text": f"*Confidence:* {ev.confidence_score * 100:.1f}%"})
            
        collected_time = ev.collected_at.strftime('%Y-%m-%d %H:%M UTC') if ev.collected_at else "N/A"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{icon} *{ev.title}*\n"
                        f"*ID:* `{ev.id}` | *Collected:* {collected_time}\n"
                        f"> {ev.description or 'No description provided.'}"
            }
        })
        
        blocks.append({
            "type": "section",
            "fields": fields
        })
        
        if getattr(ev, "content", None):
            content_text = ev.content
            # Format as clickable if it's a raw URL
            if content_text.strip().startswith("http"):
                content_text = f"<{content_text.strip()}>"
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Data:*\n{content_text}"
                }
            })
        
        if getattr(ev, "evidence_metadata", None) and "url" in ev.evidence_metadata:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"<{ev.evidence_metadata['url']}|View Original Source>"}]
            })
            
        blocks.append({"type": "divider"})
        
    return blocks
