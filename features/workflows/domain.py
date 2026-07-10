from enum import Enum


class WorkflowStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

class WorkflowStageType(str, Enum):
    """Library of standard stages that workflows may choose from."""
    INVESTIGATION = "INVESTIGATION"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    ANALYSIS = "ANALYSIS"
    RECOMMENDATION = "RECOMMENDATION"
    APPROVAL = "APPROVAL"
    ASSIGNMENT = "ASSIGNMENT"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    RESOLUTION = "RESOLUTION"
    REVIEW = "REVIEW"

class WorkflowPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
