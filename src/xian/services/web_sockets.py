import json
import asyncio
import websockets

from loguru import logger


class WebSocketServer:
    def __init__(self, bds_instance):
        self.bds_instance = bds_instance
        self.subscribers = set()

    async def register(self, websocket):
        self.subscribers.add(websocket)
        logger.info(f"New subscriber connected: {websocket.remote_address}")

    async def unregister(self, websocket):
        self.subscribers.remove(websocket)
        logger.info(f"Subscriber disconnected: {websocket.remote_address}")

    async def notify_subscribers(self, key, value):
        if self.subscribers:
            message = json.dumps({'key': key, 'value': str(value)})
            tasks = [asyncio.create_task(ws.send(message)) for ws in self.subscribers]
            await asyncio.gather(*tasks)

    async def websocket_handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                key = data.get('key')
                if key:
                    history = await self.bds_instance.get_state_history(key)
                    await websocket.send(history)
        except websockets.exceptions.ConnectionClosedError:
            logger.info(f"Connection closed unexpectedly for subscriber: {websocket.remote_address}")
        except Exception as e:
            logger.exception(f"Unexpected error for subscriber {websocket.remote_address}: {e}")
        finally:
            await self.unregister(websocket)

    async def start(self):
        start_server = websockets.serve(
            self.websocket_handler,
            "localhost", 7654
        )
        await start_server
