from __future__ import annotations

from typing import Any
from uuid import UUID

from langfuse import RunnerContext

from tryniq_evals.contracts import Cadence, SuiteDefinition, capture_task
from tryniq_evals.evaluators.end_to_end import end_to_end_scores
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.run_metadata import sha256_json
from tryniq_evals.suites.support import item_input, run_metadata

DEFINITION = SuiteDefinition(
    suite="meeting-end-to-end",
    version="1.0.0",
    dataset_name="tryniq/meeting-end-to-end/1.0.0/smoke",
    concurrency=1,
    cadence=(Cadence.NIGHTLY, Cadence.RELEASE),
    evaluators=("completion", "idempotency", "failure_rate"),
    owner="ai-platform",
    judge_metrics=True,
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.db import async_session
        from app.meeting.services.meeting import MeetingService
        from app.participant.service import ParticipantService
        from app.transcript.service import TranscriptService
        from app.upload.service import UploadService

        value = item_input(item)
        meeting_id = UUID(value["meeting_id"])
        async with async_session() as session:
            upload = UploadService(
                MeetingService(session),
                ParticipantService(session),
                TranscriptService(session),
            )
            await upload.process(meeting_id, value["source_key"])
            first = await _durable_signature(session, meeting_id)
            await upload.process(meeting_id, value["source_key"])
            second = await _durable_signature(session, meeting_id)
            meeting = await upload.meeting_service.retrieve(meeting_id)
        return {
            "meeting_id": str(meeting_id),
            "status": str(meeting.status),
            "idempotent": first == second,
            "first_state_sha256": sha256_json(first),
            "second_state_sha256": sha256_json(second),
        }

    return (await capture_task(invoke)).model_dump(mode="json")


async def _durable_signature(session: Any, meeting_id: UUID) -> dict[str, Any]:
    from app.participant.models import Participant
    from app.transcript.models import Utterance
    from sqlmodel import select

    participants = (
        await session.exec(
            select(Participant)
            .where(Participant.meeting_id == meeting_id)
            .order_by(Participant.stream_id)
        )
    ).all()
    utterances = (
        await session.exec(
            select(Utterance)
            .where(Utterance.meeting_id == meeting_id)
            .order_by(Utterance.stream_id, Utterance.t_start, Utterance.t_end)
        )
    ).all()
    return {
        "participants": [
            {"stream_id": str(row.stream_id), "name": row.name}
            for row in participants
        ],
        "utterances": [
            {
                "stream_id": str(row.stream_id),
                "t_start": row.t_start,
                "t_end": row.t_end,
                "text": row.text,
                "is_final": row.is_final,
            }
            for row in utterances
        ],
    }


def experiment(context: RunnerContext) -> Any:
    return context.run_experiment(
        name="Tryniq meeting end-to-end",
        task=task,
        evaluators=[end_to_end_scores, operational_evaluator],
        run_evaluators=[
            build_run_evaluator(primary_metrics=frozenset({"completion", "idempotency"}))
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            judge=True,
            model_id="production",
            embedding_model_id="production",
            metric_versions={"langfuse": "4.14.0", "deepeval": "4.1.4"},
        ),
    )
