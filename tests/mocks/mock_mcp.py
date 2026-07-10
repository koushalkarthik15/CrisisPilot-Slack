class MockMCPExecutor:
    """Mock implementation for MCP Execution."""
    def __init__(self):
        self.invocations = []
        
    async def execute(self, tool_name: str, arguments: dict):
        self.invocations.append({
            "tool_name": tool_name,
            "arguments": arguments
        })
        return {"status": "success", "data": "mocked_data"}
