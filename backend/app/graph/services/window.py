from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

import structlog
from sqlmodel.ext.asyncio.session import AsyncSession

from app.graph.client import GraphExtractor
from app.graph.exceptions import (
    InvalidGraphOperationError,
    UngroundedExtractionError,
    UnknownUtteranceRefError,
)
from app.graph.schemas import GraphPatchEvent
from app.graph.services.graph import GraphService
from app.transcript.models import Utterance

logger = structlog.get_logger()


class GraphWindowStatus(StrEnum):
    APPLIED = "applied"
    EMPTY_WINDOW = "empty_window"
    EMPTY_EXTRACTION = "empty_extraction"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class GraphWindowResult:
    status: GraphWindowStatus
    patch: GraphPatchEvent | None = None
    operation_count: int = 0
    rejection_reason: str | None = None
    rolled_back: bool = False


class GraphWindowProcessor:
    """Callable production boundary shared by TaskIQ and evaluation suites."""

    def __init__(
        self,
        session: AsyncSession,
        graph_service: GraphService,
        extractor: GraphExtractor,
    ) -> None:
        self.session = session
        self.graph_service = graph_service
        self.extractor = extractor

    async def process(
        self,
        meeting_id: UUID,
        utterances: list[Utterance],
        prompt: str,
        short_refs: dict[str, UUID],
    ) -> GraphWindowResult:
        if not utterances:
            return GraphWindowResult(status=GraphWindowStatus.EMPTY_WINDOW)

        operations = await self.extractor.extract(prompt)
        if not operations:
            return GraphWindowResult(status=GraphWindowStatus.EMPTY_EXTRACTION)

        langfuse = self.extractor.ai_client.langfuse
        with langfuse.start_as_current_observation(
            name="graph.persist",
            as_type="span",
            input={"meeting_id": str(meeting_id), "operation_count": len(operations)},
        ) as observation:
            try:
                patch = await self.graph_service.apply_operations(
                    meeting_id,
                    operations,
                    utterances,
                    short_refs,
                )
            except (
                UngroundedExtractionError,
                UnknownUtteranceRefError,
                InvalidGraphOperationError,
            ) as exc:
                await self.session.rollback()
                observation.update(level="WARNING", status_message=str(exc))
                logger.warning(
                    "Skipping window, LLM produced invalid operations",
                    meeting_id=str(meeting_id),
                    reason=str(exc),
                )
                return GraphWindowResult(
                    status=GraphWindowStatus.REJECTED,
                    operation_count=len(operations),
                    rejection_reason=str(exc),
                    rolled_back=True,
                )
            observation.update(
                output={
                    "added_nodes": len(patch.added_nodes),
                    "added_edges": len(patch.added_edges),
                    "updated_nodes": len(patch.updated_nodes),
                }
            )
            return GraphWindowResult(
                status=GraphWindowStatus.APPLIED,
                patch=patch,
                operation_count=len(operations),
            )
