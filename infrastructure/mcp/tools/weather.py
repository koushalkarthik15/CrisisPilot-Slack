import logging
import aiohttp
from typing import Any, Dict
from core.config import get_settings
from infrastructure.mcp.base import BaseTool
from infrastructure.mcp.models import ToolRequest, ToolResponse

logger = logging.getLogger("crisispilot.mcp.tools.weather")

class OpenWeatherProvider:
    """Provider abstraction for OpenWeatherMap API."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    async def get_weather(self, location: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY is not configured.")
            
        params = {
            "q": location,
            "appid": self.api_key,
            "units": "metric"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Weather API Error: {response.status} - {error_text}")
                return await response.json()

class WeatherTool(BaseTool):
    """
    MCP Tool for fetching weather information.
    """
    def __init__(self):
        self.settings = get_settings()
        self.provider = OpenWeatherProvider(api_key=self.settings.OPENWEATHER_API_KEY)

    @property
    def name(self) -> str:
        return "weather_tool"
        
    @property
    def description(self) -> str:
        return "Fetches current weather conditions for a specified location."
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, optionally followed by country code (e.g., 'London, UK' or 'Tokyo')."
                }
            },
            "required": ["location"]
        }

    async def execute(self, request: ToolRequest) -> ToolResponse:
        location = request.arguments.get("location")
        if not location:
            return ToolResponse(
                is_error=True,
                content="Missing required argument: 'location'."
            )
            
        try:
            data = await self.provider.get_weather(location)
            
            # Normalize response
            temp = data.get("main", {}).get("temp")
            condition = data.get("weather", [{}])[0].get("description", "Unknown")
            humidity = data.get("main", {}).get("humidity")
            wind_speed = data.get("wind", {}).get("speed")
            
            content = (
                f"Weather in {location}:\n"
                f"- Condition: {condition}\n"
                f"- Temperature: {temp}°C\n"
                f"- Humidity: {humidity}%\n"
                f"- Wind Speed: {wind_speed} m/s"
            )
            
            return ToolResponse(
                is_error=False,
                content=content,
                metadata={"raw_data": data}
            )
        except Exception as e:
            logger.error(f"Weather lookup failed for {location}: {e}", exc_info=True)
            return ToolResponse(
                is_error=True,
                content=f"Failed to fetch weather data: {e}"
            )
