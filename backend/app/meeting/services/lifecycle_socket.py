import asyncio
import json

from fastapi import WebSocket

from app.core.decorators import suppress_ws_disconnect
from app.meeting.client import redis_client
from app.meeting.constants import GLOBAL_LIFECYCLE_CHANNEL, HEARTBEAT_INTERVAL_SECONDS


class GlobalLifecycleSocket:
    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self._disconnected = asyncio.Event()

    @suppress_ws_disconnect
    async def serve(self) -> None:
        await self.ws.accept()
        receive_task = asyncio.create_task(self._drain())
        try:
            async for payload in redis_client.subscribe(GLOBAL_LIFECYCLE_CHANNEL, HEARTBEAT_INTERVAL_SECONDS):
                if self._disconnected.is_set():
                    return

                try:
                    if payload is None:
                        await self.ws.send_text(json.dumps({"kind": "ping"}))
                    else:
                        await self.ws.send_text(payload.decode())
                except RuntimeError:
                    return
        finally:
            receive_task.cancel()

    @suppress_ws_disconnect
    async def _drain(self) -> None:
        while True:
            frame = await self.ws.receive()
            if frame.get("type") == "websocket.disconnect":
                self._disconnected.set()
                return
