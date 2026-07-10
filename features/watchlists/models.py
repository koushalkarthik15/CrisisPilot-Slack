import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from infrastructure.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, nullable=False, default="default")
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    keywords = Column(String, nullable=False) # Comma separated
    channel_id = Column(String, nullable=False)
    severity_threshold = Column(String, nullable=False, default="MEDIUM")
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class WatchlistArticle(Base):
    """
    Tracks articles processed by a watchlist to prevent duplicate incidents.
    """
    __tablename__ = "watchlist_articles"

    id = Column(String, primary_key=True, default=generate_uuid)
    watchlist_id = Column(String, nullable=False, index=True)
    article_url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
