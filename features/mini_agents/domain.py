from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "Idle"
    EXECUTING = "Executing"
    ERROR = "Error"
    OFFLINE = "Offline"

class AgentRole(str, Enum):
    DATA_GATHERING = "Data Gathering"
    ANALYSIS = "Analysis"
    COMMUNICATION = "Communication"
    UTILITY = "Utility"
