import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.notifications import NotificationEngine
from features.monitoring.domain import SituationState
from features.timeline.domain import (
    TimelineEventSeverity,
    TimelineEventSource,
    TimelineEventType,
)
from features.timeline.schemas import TimelineEventCreate

logger = logging.getLogger("crisispilot.monitoring.notification_policy")

class NotificationPolicyEngine:
    """
    Decides when notifications should be dispatched to avoid duplicates and alert fatigue.
    """

    def __init__(self, notification_engine: NotificationEngine):
        self.notification_engine = notification_engine

    async def evaluate_and_notify(self, db: AsyncSession, state_manager, profile, old_state: SituationState, new_state: SituationState, old_risk: float, new_risk: float):
        """
        Evaluates the changes in operational conditions and triggers notifications if necessary.
        """
        should_notify = False
        message = ""
        severity = TimelineEventSeverity.INFO

        # Rule 1: State changed
        if old_state != new_state:
            should_notify = True
            message = f"Situation State changed from {old_state.name} to {new_state.name}. Risk Score: {new_risk:.1f}."
            if new_state in [SituationState.WARNING, SituationState.CRITICAL]:
                severity = TimelineEventSeverity.WARNING

        # Rule 2: Risk score crossed threshold while remaining in same state
        # For simplicity, if it spikes by more than 15 points
        elif (new_risk - old_risk) >= 15.0:
            should_notify = True
            message = f"Risk Score spiked by {(new_risk - old_risk):.1f} points. Current Score: {new_risk:.1f}."
            severity = TimelineEventSeverity.WARNING

        if should_notify:
            # 1. Record Timeline Event
            tl_event = TimelineEventCreate(
                event_type=TimelineEventType.STATUS_CHANGE,
                source=TimelineEventSource.SYSTEM,
                severity=severity,
                description=message,
                operation_id=profile.operation_id
            )
            await state_manager.create_timeline_event(db, tl_event)

            # 2. Dispatch Notification
            if profile.notification_targets:
                for target in profile.notification_targets.split(","):
                    target = target.strip()
                    if target:
                        try:
                            await self.notification_engine.dispatch_message(
                                channel_id=target,
                                text=f"*Monitoring Update for {profile.name}*\n{message}"
                            )
                            logger.info(f"NotificationPolicy: Sent alert to {target} for profile {profile.id}")
                        except Exception as e:
                            logger.error(f"NotificationPolicy: Failed to send alert to {target}: {e}")
