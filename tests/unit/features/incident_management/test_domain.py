from features.incident_management.domain import (
    ALLOWED_TRANSITIONS,
    IncidentSeverity,
    IncidentStatus,
)


def test_incident_status_enum():
    assert IncidentStatus.DRAFT.value == "Draft"
    assert IncidentStatus.ACTIVE.value == "Active"

def test_incident_severity_enum():
    assert IncidentSeverity.HIGH.value == "High"
    assert IncidentSeverity.CRITICAL.value == "Critical"

def test_allowed_transitions():
    assert IncidentStatus.CREATED in ALLOWED_TRANSITIONS[IncidentStatus.DRAFT]
    assert IncidentStatus.ACTIVE in ALLOWED_TRANSITIONS[IncidentStatus.CREATED]
    # ARCHIVED should be terminal
    assert len(ALLOWED_TRANSITIONS[IncidentStatus.ARCHIVED]) == 0
    # ACTIVE can go to RESOLVED
    assert IncidentStatus.RESOLVED in ALLOWED_TRANSITIONS[IncidentStatus.ACTIVE]
