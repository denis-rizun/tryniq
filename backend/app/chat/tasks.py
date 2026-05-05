from uuid import UUID

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.models import UtteranceEmbedding
from app.config import config
from app.db import async_session
from app.graph.clients.embeddings import get_embedding_client
from app.tasks import broker
from app.transcript.models import Utterance

logger = structlog.get_logger()


@broker.task(retry_on_error=True, max_retries=2)
async def embed_utterances(meeting_id: str) -> None:
    meeting_uuid = UUID(meeting_id)
    embedding_client = get_embedding_client()
    async with async_session() as session:
        pending = await _select_pending(session, meeting_uuid)
        if not pending:
            logger.debug("no utterances to embed", meeting_id=meeting_uuid)
            return

        texts = [u.text for u in pending]

        batch_size = config.chat.EMBED_BATCH_SIZE
        vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            vectors.extend(await embedding_client.embed_many(chunk))

        model = config.chat.EMBED_MODEL
        for utt, vec in zip(pending, vectors, strict=True):
            stmt = (
                pg_insert(UtteranceEmbedding)
                .values(
                    utterance_id=utt.id,
                    meeting_id=utt.meeting_id,
                    embedding=vec,
                    model=model,
                )
                .on_conflict_do_nothing(index_elements=["utterance_id"])
            )
            await session.exec(stmt)

        await session.commit()
        logger.info(
            "utterance embeddings persisted",
            meeting_id=meeting_uuid,
            count=len(pending),
            model=model,
        )


async def _select_pending(session: AsyncSession, meeting_id: UUID) -> list[Utterance]:
    existing_stmt = select(UtteranceEmbedding.utterance_id).where(col(UtteranceEmbedding.meeting_id) == meeting_id)
    existing = set((await session.exec(existing_stmt)).all())

    stmt = (
        select(Utterance)
        .where(col(Utterance.meeting_id) == meeting_id)
        .where(col(Utterance.text) != "")
        .where(col(Utterance.is_final).is_(True))
        .order_by(col(Utterance.t_start))
    )
    rows = (await session.exec(stmt)).all()
    return [u for u in rows if u.id not in existing]
