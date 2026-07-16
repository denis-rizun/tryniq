import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import config
from app.meeting.constants import (
    EVENT_CHANNEL,
    GLOBAL_LIFECYCLE_CHANNEL,
    GLOBAL_LIFECYCLE_EVENTS,
    PARTIAL_KEY,
    PARTIAL_TTL_SECONDS,
    LifecycleEvent,
    MeetingEventKind,
)
from app.meeting.schemas import MeetingEvent, MeetingLifecycleEvent, PartialTranscriptEvent, TranscriptSegmentEvent

logger = structlog.get_logger()


class RedisClient:
    def __init__(self) -> None:
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(config.redis.URL, decode_responses=False)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def publish_meeting_event(self, event: MeetingEvent) -> None:
        payload = event.model_dump_json()
        await self.client.publish(EVENT_CHANNEL.format(meeting_id=event.meeting_id), payload)
        if event.kind == MeetingEventKind.MEETING_LIFECYCLE and event.event in GLOBAL_LIFECYCLE_EVENTS:
            await self.client.publish(GLOBAL_LIFECYCLE_CHANNEL, payload)

    async def publish_meeting_lifecycle(self, meeting_id: UUID, event: LifecycleEvent) -> None:
        msg = MeetingLifecycleEvent(meeting_id=meeting_id, event=event, timestamp=datetime.now(UTC))
        await self.publish_meeting_event(msg)

    async def publish_partial_transcript(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        participant_id: UUID | None,
        text: str,
    ) -> None:
        event = PartialTranscriptEvent(
            meeting_id=meeting_id,
            stream_id=stream_id,
            participant_id=participant_id,
            text=text,
            timestamp=datetime.now(UTC),
        )
        payload = event.model_dump_json()
        await self.client.publish(EVENT_CHANNEL.format(meeting_id=meeting_id), payload)
        await self.client.set(PARTIAL_KEY.format(stream_id=stream_id), payload, ex=PARTIAL_TTL_SECONDS)

    async def publish_transcript_segment(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        participant_id: UUID | None,
        utterance_id: UUID,
        text: str,
        t_start: float,
        t_end: float,
        is_final: bool,
    ) -> None:
        event = TranscriptSegmentEvent(
            meeting_id=meeting_id,
            stream_id=stream_id,
            participant_id=participant_id,
            utterance_id=utterance_id,
            text=text,
            t_start=t_start,
            t_end=t_end,
            is_final=is_final,
            timestamp=datetime.now(UTC),
        )
        payload = event.model_dump_json()
        await self.client.publish(EVENT_CHANNEL.format(meeting_id=meeting_id), payload)
        await self.client.delete(PARTIAL_KEY.format(stream_id=stream_id))

    async def publish_graph_patch(self, meeting_id: UUID, payload: str) -> None:
        await self.client.publish(EVENT_CHANNEL.format(meeting_id=meeting_id), payload)

    async def get_partial_cache(self, stream_id: UUID) -> str | None:
        raw = await self.client.get(PARTIAL_KEY.format(stream_id=stream_id))
        return raw.decode() if isinstance(raw, bytes) else None

    async def subscribe(self, channel: str, idle_timeout_s: float) -> AsyncIterator[bytes | None]:
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=idle_timeout_s,
                    )
                except TimeoutError:
                    yield None
                    continue

                if message is None:
                    continue

                data = message.get("data")
                if data is None:
                    continue

                yield data if isinstance(data, bytes) else json.dumps(data).encode()
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except RedisError as exc:
                logger.debug("redis: pubsub cleanup failed", channel=channel, error=str(exc))


redis_client = RedisClient()
