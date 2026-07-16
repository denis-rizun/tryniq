import json
import time
from collections.abc import AsyncGenerator
from uuid import UUID

import structlog

from app.meeting.client import redis_client
from app.meeting.constants import EVENT_CHANNEL, HEARTBEAT_INTERVAL_SECONDS

logger = structlog.get_logger()


class StreamSubscriber:
    SSE_IDLE_TIMEOUT_SECONDS = 500

    def __init__(self, meeting_id: UUID) -> None:
        self.meeting_id = meeting_id

    async def stream(self) -> AsyncGenerator[bytes]:
        channel = EVENT_CHANNEL.format(meeting_id=self.meeting_id)
        last_activity = time.monotonic()
        try:
            async for payload in redis_client.subscribe(channel, HEARTBEAT_INTERVAL_SECONDS):
                if time.monotonic() - last_activity > self.SSE_IDLE_TIMEOUT_SECONDS:
                    logger.debug("sse idle timeout", meeting_id=self.meeting_id)
                    break

                if payload is None:
                    yield self._format(event_type="heartbeat", data=b"{}")
                    continue

                last_activity = time.monotonic()
                yield self._format(event_type=self._extract_kind(payload), data=payload)
        except GeneratorExit:
            logger.debug("sse client disconnected", meeting_id=self.meeting_id)

    @staticmethod
    def _format(event_type: str, data: bytes) -> bytes:
        return f"event: {event_type}\ndata: ".encode() + data + b"\n\n"

    @staticmethod
    def _extract_kind(payload: bytes) -> str:
        try:
            return json.loads(payload).get("kind", "message")
        except (json.JSONDecodeError, AttributeError):
            return "message"
