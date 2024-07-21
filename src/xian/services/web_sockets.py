import json
import asyncio
import websockets


class WebSocketServer:
    def __init__(self, bds_instance):
        self.bds_instance = bds_instance
        self.subscribers = set()

    async def register(self, websocket):
        self.subscribers.add(websocket)

    async def unregister(self, websocket):
        self.subscribers.remove(websocket)

    async def notify_subscribers(self, key, value):
        if self.subscribers:
            message = json.dumps({'key': key, 'value': value}, cls=self.bds_instance.CustomEncoder)
            await asyncio.wait([ws.send(message) for ws in self.subscribers])

    async def websocket_handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                key = data.get('key')
                if key:
                    history = await self.bds_instance.get_state_history(key)
                    await websocket.send(history)
        finally:
            await self.unregister(websocket)

    async def start(self):
        start_server = websockets.serve(
            self.websocket_handler,
            "localhost", 7654
        )
        await start_server
