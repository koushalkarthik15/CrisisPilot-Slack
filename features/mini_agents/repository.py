from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from features.mini_agents.models import MiniAgentModel


class MiniAgentRepository:
    """
    Repository for managing persistent Mini-Agent configurations.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_name(self, name: str) -> Optional[MiniAgentModel]:
        stmt = select(MiniAgentModel).where(MiniAgentModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, enabled_only: bool = False) -> List[MiniAgentModel]:
        stmt = select(MiniAgentModel)
        if enabled_only:
            stmt = stmt.where(MiniAgentModel.is_enabled == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, agent: MiniAgentModel) -> MiniAgentModel:
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def update(self, name: str, update_data: dict) -> Optional[MiniAgentModel]:
        stmt = (
            update(MiniAgentModel)
            .where(MiniAgentModel.name == name)
            .values(**update_data)
            .returning(MiniAgentModel)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, name: str) -> bool:
        stmt = delete(MiniAgentModel).where(MiniAgentModel.name == name)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
