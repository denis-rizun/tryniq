from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.audio.exceptions import AudioTrackNotFoundError
from app.audio.schemas import AudioTrackResponse
from app.ingest.clients.minio import minio_client
from app.participant.models import Participant


def _slugify(name: str) -> str:
    cleaned = "".join(c if c.isalnum() else "_" for c in name).strip("_").lower()
    return cleaned or "speaker"


class AudioService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_tracks(self, meeting_id: UUID) -> list[AudioTrackResponse]:
        participants = (await self.session.exec(select(Participant).where(Participant.meeting_id == meeting_id))).all()

        tracks: list[AudioTrackResponse] = []
        for participant in participants:
            for part in (1, 2):
                key = minio_client.get_stream_object_key(meeting_id, participant.stream_id, part)
                if not await minio_client.object_exists(key):
                    continue

                tracks.append(
                    AudioTrackResponse(
                        stream_id=participant.stream_id,
                        participant_id=participant.id,
                        participant_name=participant.name,
                        is_local_user=participant.is_local_user,
                        part=part,
                        object_key=key,
                        filename=self._filename(participant.name, part),
                    )
                )
        return tracks

    async def get_track(self, meeting_id: UUID, stream_id: UUID, part: int) -> tuple[bytes, str]:
        key = minio_client.get_stream_object_key(meeting_id, stream_id, part)
        if not await minio_client.object_exists(key):
            raise AudioTrackNotFoundError()

        participant = (
            await self.session.exec(
                select(Participant)
                .where(Participant.meeting_id == meeting_id)
                .where(Participant.stream_id == stream_id)
            )
        ).one_or_none()
        name = participant.name if participant else str(stream_id)
        body = await minio_client.get_object(key)
        return body, self._filename(name, part)

    @staticmethod
    def _filename(name: str, part: int) -> str:
        slug = _slugify(name)
        suffix = "" if part == 1 else f"-part{part}"
        return f"{slug}{suffix}.wav"
