from enum import Enum

from pydantic import BaseModel


class DecisionAction(str, Enum):
    APPROVE = "Approve"
    REJECT = "Reject"
    REQUEST_CHANGES = "Request Changes"
    ESCALATE = "Escalate"
    AUTO_APPROVE = "Auto Approve"
    ASSIGN = "Assign"
    START_EXECUTION = "Start Execution"
    COMPLETE_EXECUTION = "Complete Execution"
    RESOLVE_INCIDENT = "Resolve Incident"
    ARCHIVE_INCIDENT = "Archive Incident"
    MERGE_INCIDENT = "Merge Incident"
    MARK_DUPLICATE = "Mark Duplicate"
    DELETE_INCIDENT = "Delete Incident"
    REOPEN_INCIDENT = "Reopen Incident"

class DecisionStatus(str, Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"

class WorkflowEventPayload(BaseModel):
    recommendation_id: str
    action: DecisionAction
    reviewer_id: str
    status: DecisionStatus
    comments: str | None = None
