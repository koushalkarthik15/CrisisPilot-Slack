from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from features.incident_management.domain import IncidentSeverity


class WatchlistBase(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: str
    channel_id: str
    severity_threshold: IncidentSeverity = IncidentSeverity.MEDIUM
    enabled: bool = True

class WatchlistCreate(WatchlistBase):
    org_id: str = "default"

class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    channel_id: Optional[str] = None
    severity_threshold: Optional[IncidentSeverity] = None
    enabled: Optional[bool] = None

class WatchlistResponse(WatchlistBase):
    id: str
    org_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WatchlistArticleCreate(BaseModel):
    watchlist_id: str
    article_url: str
    title: Optional[str] = None
