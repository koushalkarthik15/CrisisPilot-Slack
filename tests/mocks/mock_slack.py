class MockSlackClient:
    def __init__(self):
        self.messages_sent = []
        self.views_opened = []

    async def chat_postMessage(self, channel, text=None, blocks=None, thread_ts=None, **kwargs):
        message = {
            "channel": channel,
            "text": text,
            "blocks": blocks,
            "thread_ts": thread_ts,
            **kwargs
        }
        self.messages_sent.append(message)
        return {"ok": True, "ts": "mock-12345.678"}
        
    async def views_open(self, trigger_id, view, **kwargs):
        self.views_opened.append({
            "trigger_id": trigger_id,
            "view": view,
            **kwargs
        })
        return {"ok": True}

class MockSlackApp:
    def __init__(self):
        self.client = MockSlackClient()
