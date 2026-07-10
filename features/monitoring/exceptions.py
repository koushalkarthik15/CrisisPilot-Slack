from core.errors import CrisisPilotError


class MonitoringProfileNotFoundError(CrisisPilotError):
    def __init__(self, profile_id: str):
        super().__init__(f"Monitoring Profile with id '{profile_id}' not found.")

class DuplicateMonitoringProfileNameError(CrisisPilotError):
    def __init__(self, name: str):
        super().__init__(f"A Monitoring Profile with name '{name}' already exists.")

class InvalidMonitoringStateTransitionError(CrisisPilotError):
    def __init__(self, current_state: str, attempted_state: str):
        super().__init__(f"Invalid monitoring state transition from {current_state} to {attempted_state}.")
