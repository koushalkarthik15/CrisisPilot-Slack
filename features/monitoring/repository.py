import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from features.monitoring.domain import MonitoringStatus
from features.monitoring.models import MonitoringProfile
from features.monitoring.schemas import MonitoringProfileCreate, MonitoringProfileUpdate

logger = logging.getLogger("crisispilot.monitoring.repository")

class MonitoringRepository:
    """Persistence layer for Monitoring Profiles."""

    async def create(self, db: AsyncSession, profile_in: MonitoringProfileCreate, created_by: str) -> MonitoringProfile:
        profile = MonitoringProfile(
            name=profile_in.name,
            description=profile_in.description,
            monitoring_category=profile_in.monitoring_category,
            target_type=profile_in.target_type,
            region=profile_in.region,
            priority=profile_in.priority,
            frequency=profile_in.frequency,
            risk_threshold=profile_in.risk_threshold,
            workflow_template=profile_in.workflow_template,
            notification_targets=profile_in.notification_targets,
            created_by=created_by,
            status=MonitoringStatus.PLANNED
        )
        db.add(profile)
        await db.flush()
        await db.refresh(profile)
        logger.info(f"Created monitoring profile {profile.id} ({profile.name})")
        return profile

    async def get(self, db: AsyncSession, profile_id: str) -> Optional[MonitoringProfile]:
        result = await db.execute(select(MonitoringProfile).where(MonitoringProfile.id == profile_id))
        return result.scalars().first()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[MonitoringProfile]:
        result = await db.execute(select(MonitoringProfile).where(MonitoringProfile.name == name))
        return result.scalars().first()

    async def list_active(self, db: AsyncSession) -> List[MonitoringProfile]:
        result = await db.execute(
            select(MonitoringProfile)
            .where(MonitoringProfile.status.in_([MonitoringStatus.ACTIVE, MonitoringStatus.PLANNED, MonitoringStatus.PAUSED]))
            .order_by(MonitoringProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, profile_id: str, update_data: MonitoringProfileUpdate) -> Optional[MonitoringProfile]:
        profile = await self.get(db, profile_id)
        if not profile:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return profile

        for key, value in update_dict.items():
            setattr(profile, key, value)

        await db.flush()
        await db.refresh(profile)
        logger.info(f"Updated monitoring profile {profile_id}")
        return profile

    async def update_status(self, db: AsyncSession, profile_id: str, new_status: MonitoringStatus, **kwargs) -> Optional[MonitoringProfile]:
        profile = await self.get(db, profile_id)
        if not profile:
            return None

        profile.status = new_status
        for key, value in kwargs.items():
            setattr(profile, key, value)

        await db.flush()
        await db.refresh(profile)
        logger.info(f"Updated status for monitoring profile {profile_id} to {new_status}")
        return profile
