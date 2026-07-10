import pytest
from pydantic import ValidationError
from typing import Dict, Any

from core.errors import ToolNotFoundError
from core.orchestration.models import ExecutionContext
from core.services import registry as service_registry
from core.state import StateManager
from infrastructure.mcp.registry import MCPRegistry
from infrastructure.mcp.executor import MCPExecutor
from infrastructure.mcp.models import ToolRequest
from infrastructure.mcp.tools.weather import WeatherTool
from infrastructure.mcp.tools.news import NewsTool
from infrastructure.mcp.tools.maps import MapsTool
from infrastructure.mcp.tools.inventory import InventoryTool
from infrastructure.mcp.diagnostic import EchoTool

@pytest.fixture
async def mcp_env():
    # Setup test environment with initialized registry and executor
    mcp_registry = MCPRegistry()
    await mcp_registry.initialize()
    
    # Register all tools
    mcp_registry.register(EchoTool())
    mcp_registry.register(WeatherTool())
    mcp_registry.register(NewsTool())
    mcp_registry.register(MapsTool())
    mcp_registry.register(InventoryTool())
    
    mcp_executor = MCPExecutor(registry=mcp_registry)
    await mcp_executor.initialize()
    
    # Mock StateManager for InventoryTool
    state_manager = StateManager()
    await state_manager.initialize()
    service_registry.register(StateManager, state_manager)
    
    yield {"registry": mcp_registry, "executor": mcp_executor}
    
    await mcp_executor.shutdown()
    await mcp_registry.shutdown()
    await state_manager.shutdown()
    service_registry.clear()

@pytest.mark.asyncio
async def test_mcp_registry_initialization(mcp_env):
    """Verify Tool Registry integrity."""
    registry = mcp_env["registry"]
    tools = registry.list_tools() if hasattr(registry, "list_tools") else []
    # Actually registry.list_tools is not implemented, we can check get_mcp_capabilities
    capabilities = registry.get_mcp_capabilities()
    assert len(capabilities) == 5
    names = [cap.name for cap in capabilities]
    assert "weather_tool" in names
    assert "news_tool" in names
    assert "maps_tool" in names
    assert "inventory_tool" in names

@pytest.mark.asyncio
async def test_supervisor_invocation_pipeline(mcp_env):
    """Verify Supervisor Agent invocation through MCP pipeline using diagnostic EchoTool."""
    executor = mcp_env["executor"]
    req = ToolRequest(name="diagnostic_echo", arguments={"message": "Pipeline Test"})
    res = await executor.execute_tool(req)
    
    assert not res.is_error
    assert "Echo: Pipeline Test" in res.content
    assert "processed_at" in res.metadata

@pytest.mark.asyncio
async def test_maps_tool_live_integration(mcp_env):
    """Validate Maps Tool end-to-end against live Nominatim API."""
    executor = mcp_env["executor"]
    req = ToolRequest(name="maps_tool", arguments={"location": "Paris, France"})
    res = await executor.execute_tool(req)
    
    assert not res.is_error
    assert "Paris" in res.content
    assert res.metadata["lat"] != "0"

@pytest.mark.asyncio
async def test_weather_tool_live_integration(mcp_env):
    """Validate Weather Tool live execution."""
    executor = mcp_env["executor"]
    req = ToolRequest(name="weather_tool", arguments={"location": "London"})
    res = await executor.execute_tool(req)
    
    # Since API keys might be missing in CI, we check that it either succeeds or handles the API error cleanly
    assert res is not None
    if res.is_error:
        assert "API" in res.content or "fetch weather" in res.content
    else:
        assert "Temperature" in res.content

@pytest.mark.asyncio
async def test_news_tool_live_integration(mcp_env):
    """Validate News Tool live execution."""
    executor = mcp_env["executor"]
    req = ToolRequest(name="news_tool", arguments={"query": "technology", "limit": 1})
    res = await executor.execute_tool(req)
    
    # Check graceful error handling if API key is invalid/missing, else success
    assert res is not None
    if res.is_error:
        assert "API" in res.content or "fetch news" in res.content
    else:
        assert "Recent news" in res.content

@pytest.mark.asyncio
async def test_inventory_tool_pending_validation(mcp_env):
    """Verify Inventory Tool successfully queries State Manager (pending real business schema)."""
    executor = mcp_env["executor"]
    req = ToolRequest(name="inventory_tool", arguments={"resource_type": "water", "location": "Hub A"})
    res = await executor.execute_tool(req)
    
    assert not res.is_error
    assert "water" in res.content
    assert res.metadata["quantity"] == 500

@pytest.mark.asyncio
async def test_invalid_tool_handling(mcp_env):
    """Verify missing tools are caught correctly by the pipeline."""
    executor = mcp_env["executor"]
    req = ToolRequest(name="non_existent_tool", arguments={})
    res = await executor.execute_tool(req)
    
    assert res.is_error
    assert "ToolNotFoundError" in res.metadata.get("error", "")
