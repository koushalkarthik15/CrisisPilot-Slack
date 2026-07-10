import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from features.watchlists.models import Watchlist, WatchlistArticle
from features.watchlists.schemas import WatchlistCreate, WatchlistArticleCreate
from features.watchlists.repository import WatchlistRepository, WatchlistArticleRepository
from infrastructure.mcp.executor import MCPExecutor
from infrastructure.mcp.models import ToolRequest
from features.incident_management.schemas import IncidentCreate
from features.incident_management.service import IncidentService
from features.recommendations.service import RecommendationService
from core.notifications import NotificationEngine
from core.services import registry

logger = logging.getLogger("crisispilot.watchlists.service")

class WatchlistService:
    def __init__(self, repository: WatchlistRepository):
        self.repository = repository

    async def create_watchlist(self, db: AsyncSession, obj_in: WatchlistCreate) -> Watchlist:
        logger.info(f"Creating Watchlist: {obj_in.name}")
        return await self.repository.create(db, obj_in)

    async def get_enabled_watchlists(self, db: AsyncSession) -> List[Watchlist]:
        return await self.repository.get_enabled_watchlists(db)


class WatchlistMonitoringService:
    """
    Business logic for polling news, deduplicating, and orchestrating incident creation.
    """
    def __init__(
        self,
        watchlist_repo: WatchlistRepository,
        article_repo: WatchlistArticleRepository,
        incident_service: IncidentService,
        recommendation_service: RecommendationService
    ):
        self.watchlist_repo = watchlist_repo
        self.article_repo = article_repo
        self.incident_service = incident_service
        self.recommendation_service = recommendation_service
        self.notification_engine = registry.get(NotificationEngine)
        self.mcp_executor = registry.get(MCPExecutor)

    async def _process_watchlist(self, db: AsyncSession, watchlist: Watchlist):
        logger.debug(f"Processing watchlist: {watchlist.name}")
        
        # 1. Fetch news via MCP
        request = ToolRequest(
            name="news_tool",
            arguments={"query": watchlist.keywords, "limit": 5}
        )
        response = await self.mcp_executor.execute_tool(request)
        if response.is_error:
            logger.error(f"Failed to fetch news for watchlist '{watchlist.name}': {response.content}")
            return
            
        articles = response.metadata.get("articles", [])
        
        for article in articles:
            url = article.get("url")
            title = article.get("title", "No Title")
            if not url:
                continue
                
            # 2. Deduplicate
            exists = await self.article_repo.exists_by_watchlist_and_url(db, watchlist.id, url)
            if exists:
                continue
                
            logger.info(f"Watchlist '{watchlist.name}' detected new article: {title}")
            
            # 3. Create Incident
            description = f"Automated incident from Watchlist '{watchlist.name}'.\n\nArticle: {title}\nSource: {article.get('source', {}).get('name', 'Unknown')}\nURL: {url}"
            incident_data = IncidentCreate(
                title=f"[Automated] {title[:80]}...",
                description=description,
                severity=watchlist.severity_threshold,
                channel_id=watchlist.channel_id,
                created_by="system-monitor"
            )
            incident = await self.incident_service.create_incident(db, incident_data)
            await db.flush() # Flush to get incident ID
            
            # 4. Generate Recommendations
            incident_context = {
                "id": incident.id,
                "title": incident.title,
                "severity": incident.severity.name,
                "description": incident.description
            }
            recs = await self.recommendation_service.generate_recommendations(db, incident_context, [article])
            
            # 5. Persist the article to prevent duplicates
            await self.article_repo.create(db, WatchlistArticleCreate(
                watchlist_id=watchlist.id,
                article_url=url,
                title=title
            ))
            
            await db.commit()
            await db.refresh(incident)
            
            # 6. Publish to Slack
            try:
                thread_ts = await self.notification_engine.publish_incident_created(incident, watchlist.channel_id)
                for rec in recs:
                    await self.notification_engine.publish_recommendation(rec, watchlist.channel_id, thread_ts)
            except Exception as e:
                logger.error(f"Failed to publish automated incident to Slack: {e}")


    async def run_monitoring_cycle(self, db: AsyncSession):
        logger.info("Starting Watchlist Monitoring Cycle...")
        watchlists = await self.watchlist_repo.get_enabled_watchlists(db)
        
        for watchlist in watchlists:
            try:
                await self._process_watchlist(db, watchlist)
            except Exception as e:
                logger.error(f"Error processing watchlist {watchlist.id}: {e}", exc_info=True)
                
        logger.info("Watchlist Monitoring Cycle completed.")
