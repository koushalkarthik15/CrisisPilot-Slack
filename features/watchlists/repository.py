from typing import List

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from features.watchlists.models import Watchlist, WatchlistArticle
from features.watchlists.schemas import (
    WatchlistArticleCreate,
    WatchlistCreate,
    WatchlistUpdate,
)
from shared.repository import BaseRepository


class WatchlistRepository(BaseRepository[Watchlist, WatchlistCreate, WatchlistUpdate]):
    def __init__(self):
        super().__init__(Watchlist)

    async def get_enabled_watchlists(self, db: AsyncSession) -> List[Watchlist]:
        result = await db.execute(select(self.model).filter(self.model.enabled.is_(True)))
        return list(result.scalars().all())

class WatchlistArticleRepository(BaseRepository[WatchlistArticle, WatchlistArticleCreate, WatchlistArticleCreate]):
    def __init__(self):
        super().__init__(WatchlistArticle)

    async def exists_by_watchlist_and_url(self, db: AsyncSession, watchlist_id: str, article_url: str) -> bool:
        result = await db.execute(
            select(self.model)
            .filter(and_(self.model.watchlist_id == watchlist_id, self.model.article_url == article_url))
        )
        return result.scalars().first() is not None
