from enum import Enum

class TimelineEventType(str, Enum):
    LIFECYCLE_CHANGE = "LIFECYCLE_CHANGE"
    HUMAN_ACTION = "HUMAN_ACTION"
    AI_ACTION = "AI_ACTION"
    MISSION_EVENT = "MISSION_EVENT"
    WORKFLOW_EVENT = "WORKFLOW_EVENT"
    RECOMMENDATION_EVENT = "RECOMMENDATION_EVENT"
    STATUS_CHANGE = "STATUS_CHANGE"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    SYSTEM_EVENT = "SYSTEM_EVENT"

class TimelineEventSource(str, Enum):
    SUPERVISOR = "Supervisor"
    MISSION_ENGINE = "Mission Engine"
    WORKFLOW_ENGINE = "Workflow Engine"
    USER = "User"
    SCHEDULER = "Scheduler"
    SYSTEM = "System"
    
class TimelineEventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
