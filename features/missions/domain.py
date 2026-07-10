from enum import Enum


class MissionStatus(str, Enum):
    CREATED = "CREATED"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ExecutionStrategy(str, Enum):
    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    THRESHOLD_DRIVEN = "THRESHOLD_DRIVEN"
    STATE_DRIVEN = "STATE_DRIVEN"
    CHAINED = "CHAINED"
    CONTINUOUS = "CONTINUOUS"

class MissionPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
