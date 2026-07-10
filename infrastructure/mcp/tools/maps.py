import logging
import aiohttp
from abc import ABC, abstractmethod
from typing import Any, Dict
from infrastructure.mcp.base import BaseTool
from infrastructure.mcp.models import ToolRequest, ToolResponse

logger = logging.getLogger("crisispilot.mcp.tools.maps")

class MapProvider(ABC):
    """Abstract provider for Map services, allowing Mapbox or Google to be swapped in later."""
    @abstractmethod
    async def geocode(self, location: str) -> Dict[str, Any]:
        pass

class NominatimProvider(MapProvider):
    """Implementation of MapProvider using OpenStreetMap Nominatim."""
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"

    async def geocode(self, location: str) -> Dict[str, Any]:
        params = {
            "q": location,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "CrisisPilot/0.1.0"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Nominatim API Error: {response.status} - {error_text}")
                data = await response.json()
                if not data:
                    return {}
                return data[0]

class MapsTool(BaseTool):
    """
    MCP Tool for geocoding and map information.
    """
    def __init__(self):
        self.provider = NominatimProvider()

    @property
    def name(self) -> str:
        return "maps_tool"
        
    @property
    def description(self) -> str:
        return "Provides geographic coordinates (latitude and longitude) and standardized names for a given location."
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Name of the location to geocode."
                }
            },
            "required": ["location"]
        }

    async def execute(self, request: ToolRequest) -> ToolResponse:
        location = request.arguments.get("location")
        if not location:
            return ToolResponse(is_error=True, content="Missing required argument: 'location'.")
            
        try:
            data = await self.provider.geocode(location)
            
            if not data:
                return ToolResponse(is_error=False, content=f"Location '{location}' not found.")
                
            display_name = data.get("display_name", "Unknown")
            lat = data.get("lat", "0")
            lon = data.get("lon", "0")
            
            content = (
                f"Geocoding result for '{location}':\n"
                f"- Standard Name: {display_name}\n"
                f"- Latitude: {lat}\n"
                f"- Longitude: {lon}"
            )
            
            return ToolResponse(
                is_error=False,
                content=content,
                metadata={"lat": lat, "lon": lon}
            )
        except Exception as e:
            logger.error(f"Geocoding failed for {location}: {e}", exc_info=True)
            return ToolResponse(
                is_error=True,
                content=f"Failed to geocode location: {e}"
            )
