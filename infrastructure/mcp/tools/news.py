import logging
from typing import Any, Dict

import aiohttp

from core.config import get_settings
from infrastructure.mcp.base import BaseTool
from infrastructure.mcp.models import ToolRequest, ToolResponse

logger = logging.getLogger("crisispilot.mcp.tools.news")

class NewsAPIProvider:
    """Provider abstraction for NewsAPI."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/everything"

    async def fetch_news(self, query: str, limit: int = 5) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your-news-api-key":
            raise ValueError("NEWS_API_KEY is not configured or uses placeholder.")

        params = {
            "q": query,
            "apiKey": self.api_key,
            "pageSize": limit,
            "language": "en"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"News API Error: {response.status} - {error_text}")
                return await response.json()

class NewsTool(BaseTool):
    """
    MCP Tool for fetching recent news articles.
    """
    def __init__(self):
        self.settings = get_settings()
        self.provider = NewsAPIProvider(api_key=self.settings.NEWS_API_KEY)

    @property
    def name(self) -> str:
        return "news_tool"

    @property
    def description(self) -> str:
        return "Searches for recent news articles related to a specific topic or crisis."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic or keyword to search for in recent news."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles to return.",
                    "default": 3
                }
            },
            "required": ["query"]
        }

    async def execute(self, request: ToolRequest) -> ToolResponse:
        query = request.arguments.get("query")
        limit = request.arguments.get("limit", 3)
        if not query:
            return ToolResponse(is_error=True, content="Missing required argument: 'query'.")

        try:
            data = await self.provider.fetch_news(query, limit)
            articles = data.get("articles", [])

            if not articles:
                return ToolResponse(is_error=False, content=f"No recent news found for '{query}'.")

            content = f"Recent news for '{query}':\n"
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'No Title')
                source = article.get('source', {}).get('name', 'Unknown Source')
                url = article.get('url', '')
                content += f"{i}. [{source}] {title}\n   {url}\n"

            return ToolResponse(
                is_error=False,
                content=content,
                metadata={
                    "total_results": data.get("totalResults", 0),
                    "articles": articles
                }
            )
        except Exception as e:
            logger.error(f"News lookup failed for {query}: {e}", exc_info=True)
            return ToolResponse(
                is_error=True,
                content=f"Failed to fetch news data: {e}"
            )
