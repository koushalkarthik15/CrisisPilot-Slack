from enum import Enum
from typing import Dict, List, Set

class IncidentStatus(str, Enum):
    DRAFT = "Draft"
    CREATED = "Created"
    ACTIVE = "Active"
    IN_PROGRESS = "In Progress"
    UPDATED = "Updated"
    MONITORING = "Monitoring"
    RESOLVED = "Resolved"
    ARCHIVED = "Archived"
    DUPLICATE = "Duplicate"

class IncidentSeverity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

# Declarative Transition Map defining valid state transitions
ALLOWED_TRANSITIONS: Dict[IncidentStatus, Set[IncidentStatus]] = {
    IncidentStatus.DRAFT: {IncidentStatus.CREATED, IncidentStatus.ARCHIVED, IncidentStatus.DUPLICATE, IncidentStatus.RESOLVED, IncidentStatus.IN_PROGRESS},
    IncidentStatus.CREATED: {IncidentStatus.ACTIVE, IncidentStatus.ARCHIVED, IncidentStatus.DUPLICATE, IncidentStatus.RESOLVED, IncidentStatus.IN_PROGRESS},
    IncidentStatus.ACTIVE: {IncidentStatus.UPDATED, IncidentStatus.MONITORING, IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED, IncidentStatus.DUPLICATE, IncidentStatus.ARCHIVED},
    IncidentStatus.IN_PROGRESS: {IncidentStatus.UPDATED, IncidentStatus.MONITORING, IncidentStatus.RESOLVED, IncidentStatus.ARCHIVED},
    IncidentStatus.UPDATED: {IncidentStatus.ACTIVE, IncidentStatus.IN_PROGRESS, IncidentStatus.MONITORING, IncidentStatus.RESOLVED},
    IncidentStatus.MONITORING: {IncidentStatus.ACTIVE, IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED},
    IncidentStatus.RESOLVED: {IncidentStatus.ARCHIVED, IncidentStatus.ACTIVE, IncidentStatus.IN_PROGRESS},
    IncidentStatus.DUPLICATE: {IncidentStatus.ACTIVE},  # Can un-duplicate if mistake
    IncidentStatus.ARCHIVED: set(),  # Terminal state
}
