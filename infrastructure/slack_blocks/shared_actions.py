from typing import Optional


def build_quick_actions(entity_id: str, entity_type: str, operation_id: Optional[str] = None, viewer_id: Optional[str] = None, assigned_human_ids: Optional[list] = None, entity_status: Optional[str] = None) -> dict:
    """
    Builds context-appropriate quick actions.
    entity_type: 'operation', 'mission', 'workflow', 'incident'
    """
    elements = []

    # Common actions for all entities
    elements.append({
        "type": "button",
        "text": {"type": "plain_text", "text": "View Timeline 🕒", "emoji": True},
        "value": f"{entity_type}_{entity_id}",
        "action_id": "global_view_timeline"
    })

    elements.append({
        "type": "button",
        "text": {"type": "plain_text", "text": "View Evidence 📁", "emoji": True},
        "value": f"{entity_type}_{entity_id}",
        "action_id": "global_view_evidence"
    })

    elements.append({
        "type": "button",
        "text": {"type": "plain_text", "text": "Add Evidence ➕", "emoji": True},
        "value": f"{entity_type}_{entity_id}",
        "action_id": "global_add_evidence"
    })


    # Hide operational actions if the entity is in a terminal state
    terminal_states = {"COMPLETED", "RESOLVED", "ARCHIVED", "FAILED", "CANCELLED"}
    if entity_status and entity_status.upper() in terminal_states:
        return {
            "type": "actions",
            "elements": elements
        }

    elements.append({
        "type": "button",
        "text": {"type": "plain_text", "text": "Update Status 🔄", "emoji": True},
        "value": f"{entity_type}_{entity_id}",
        "action_id": "global_update_status"
    })

    if entity_type == "operation":
        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Create Mission 🎯", "emoji": True},
            "value": f"operation_{entity_id}",
            "action_id": "op_create_mission",
            "style": "primary"
        })
    elif entity_type == "mission":
        # Only show execute if we don't have a specific viewer_id OR if the viewer is assigned
        can_execute = True
        if viewer_id and assigned_human_ids is not None:
            if viewer_id not in assigned_human_ids:
                can_execute = False

        if can_execute:
            elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "Execute ⚡", "emoji": True},
                "value": f"mission_{entity_id}",
                "action_id": "mission_execute",
                "style": "primary"
            })
        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Assign 👥", "emoji": True},
            "value": f"mission_{entity_id}",
            "action_id": "mission_assign"
        })
        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Create Workflow ⚡", "emoji": True},
            "value": f"mission_{entity_id}_{operation_id or ''}",
            "action_id": "mission_create_workflow"
        })
    elif entity_type == "workflow":
        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Advance Stage ➡️", "emoji": True},
            "value": f"workflow_{entity_id}",
            "action_id": "workflow_advance",
            "style": "primary"
        })

    return {
        "type": "actions",
        "elements": elements
    }
