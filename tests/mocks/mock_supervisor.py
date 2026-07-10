class MockSupervisorAgent:
    """Mock Supervisor Agent for tests."""
    def __init__(self):
        self.evaluations = []

    async def evaluate_situation(self, text: str, context: dict = None):
        self.evaluations.append({
            "text": text,
            "context": context
        })
        return {
            "severity": "HIGH",
            "category": "TEST_CATEGORY",
            "summary": "Mocked evaluation summary",
            "recommended_actions": ["Mocked action"]
        }
