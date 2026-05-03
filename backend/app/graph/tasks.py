from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import async_session
from app.graph.clients.extractor import get_extractor
from app.graph.exceptions import InvalidGraphOperationError, UngroundedExtractionError, UnknownUtteranceRefError
from app.graph.service import GraphService
from app.meeting.client import redis_client
from app.tasks import broker
from app.transcript.models import Utterance

logger = structlog.get_logger()


@broker.task(retry_on_error=True, max_retries=2)
async def build_graph(meeting_id: str, window_start: float | None, window_end: float | None) -> None:
    mid = UUID(meeting_id)
    async with async_session() as session:
        service = GraphService(session)
        utterances = await _load_window(session, mid, window_start, window_end)
        if not utterances:
            logger.info("No utterances in window, skipping", meeting_id=meeting_id)
            return

        prompt, short_refs = _format_window(mid, utterances)
        extractor = get_extractor()
        try:
            operations = await extractor.extract(prompt)
            if not operations:
                logger.info("Extractor returned no operations", meeting_id=meeting_id)
                return

            patch = await service.apply_operations(mid, operations, utterances, short_refs)
        except (UngroundedExtractionError, UnknownUtteranceRefError, InvalidGraphOperationError) as e:
            logger.warning(
                "Skipping window, LLM produced invalid operations", meeting_id=meeting_id, reason=str(e)
            )
            await session.rollback()
            return

        await redis_client.publish_graph_patch(mid, patch.model_dump_json())
        logger.info(
            "Applied patch",
            meeting_id=meeting_id,
            added_nodes=len(patch.added_nodes),
            added_edges=len(patch.added_edges),
            updated_nodes=len(patch.updated_nodes),
        )


@broker.task(retry_on_error=True, max_retries=1)
async def aggregate_window(meeting_id: str) -> None:
    logger.debug("aggregate_window scaffolded, no-op", meeting_id=meeting_id)


async def _load_window(
    session: AsyncSession,
    meeting_id: UUID,
    window_start: float | None,
    window_end: float | None,
) -> list[Utterance]:
    query = select(Utterance).where(Utterance.meeting_id == meeting_id).where(Utterance.text != "")
    if window_start is not None:
        query = query.where(Utterance.t_start >= window_start)
    if window_end is not None:
        query = query.where(Utterance.t_start < window_end)

    query = query.order_by(Utterance.t_start)
    return list((await session.exec(query)).all())


def _format_window(meeting_id: UUID, utterances: list[Utterance]) -> tuple[str, dict[str, UUID]]:
    short_refs: dict[str, UUID] = {"meeting": meeting_id}
    lines: list[str] = ["meeting_ref = meeting"]
    for idx, u in enumerate(utterances, start=1):
        token = f"u{idx:02d}"
        short_refs[token] = u.id
        lines.append(f"[{token}] participant={u.participant_id} t={u.t_start:.2f}-{u.t_end:.2f}: {u.text}")
    return "\n".join(lines), short_refs
