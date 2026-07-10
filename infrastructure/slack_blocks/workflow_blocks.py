from typing import List, Dict, Any
from features.workflows.models import Workflow
from infrastructure.slack_blocks.shared_actions import build_quick_actions

def build_workflow_list_blocks(workflows: List[Workflow]) -> List[Dict[str, Any]]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Active Operational Workflows ⚙️"}
        },
        {"type": "divider"}
    ]
    
    if not workflows:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No active operational workflows found."}
        })
        return blocks
        
    for wf in workflows:
        status_emoji = "🟢" if wf.status.name == "RUNNING" else "⚪" if wf.status.name == "COMPLETED" else "🟡"
        stages = wf.stages if wf.stages else []
        total_stages = len(stages)
        current_stage = stages[wf.current_stage_index] if stages and wf.current_stage_index < total_stages else "N/A"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{wf.name}* {status_emoji}\n"
                        f"*ID:* `{wf.id}` | *Status:* {wf.status.name}\n"
                        f"*Progress:* Stage {wf.current_stage_index + 1} of {total_stages} ({current_stage})"
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Details 🔍", "emoji": True},
                "value": wf.id,
                "action_id": "workflow_view_details"
            }
        })
        blocks.append({"type": "divider"})
        
    return blocks

def build_workflow_detail_blocks(workflow: Workflow) -> List[Dict[str, Any]]:
    status_emoji = "🟢" if workflow.status.name == "RUNNING" else "⚪" if workflow.status.name == "COMPLETED" else "🔴" if workflow.status.name == "FAILED" else "🟡"
    
    stages = workflow.stages if workflow.stages else []
    total_stages = len(stages)
    current_stage = stages[workflow.current_stage_index] if stages and workflow.current_stage_index < total_stages else "N/A"
    progress_bar = "▓" * (workflow.current_stage_index + 1) + "░" * (total_stages - workflow.current_stage_index - 1)
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Workflow Dashboard: {workflow.name}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*ID:* `{workflow.id}`"},
                {"type": "mrkdwn", "text": f"*Status:* {workflow.status.name} {status_emoji}"},
                {"type": "mrkdwn", "text": f"*Current Stage:* {current_stage}"},
                {"type": "mrkdwn", "text": f"*Progress:* {workflow.current_stage_index}/{total_stages}"}
            ]
        }
    ]
    
    owner_str = []
    if workflow.operation_id:
        owner_str.append(f"*Operation:* `{workflow.operation_id}`")
    if workflow.incident_id:
        owner_str.append(f"*Incident:* `{workflow.incident_id}`")
    if getattr(workflow, "mission_id", None):
        owner_str.append(f"*Mission:* `{workflow.mission_id}`")
        
    if owner_str:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": " | ".join(owner_str)}]
        })
        
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*Workflow Progress:*\n`{progress_bar}`"}
    })
    
    blocks.append({"type": "divider"})
    blocks.append(build_quick_actions(workflow.id, "workflow", workflow.operation_id))
    
    return blocks
