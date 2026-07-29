from __future__ import annotations

from typing import Any
from uuid import UUID

from langfuse import RunnerContext

from tryniq_evals.contracts import Cadence, SuiteDefinition, capture_task
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.retrieval import retrieval_scores
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, run_metadata

DEFINITION = SuiteDefinition(
    suite="related-meetings",
    version="1.0.0",
    dataset_name="tryniq/related-meetings/1.0.0/test",
    concurrency=8,
    cadence=(Cadence.NIGHTLY, Cadence.RELEASE),
    evaluators=("precision_at_5", "recall_at_5", "ndcg_at_5"),
    owner="ai-platform",
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.db import async_session
        from app.meeting.models import Meeting
        from app.metadata.services.related_finder import RelatedMeetingsFinder
        from sqlmodel import select

        meeting_id = UUID(item_input(item)["meeting_id"])
        async with async_session() as session:
            meeting = (await session.exec(select(Meeting).where(Meeting.id == meeting_id))).one()
            ranked = await RelatedMeetingsFinder(session).rank(meeting_id, meeting)
        return {
            "results": [
                {"id": str(candidate), "score": len(ranked) - index}
                for index, candidate in enumerate(ranked)
            ]
        }

    return (await capture_task(invoke)).model_dump(mode="json")


def experiment(context: RunnerContext) -> Any:
    return context.run_experiment(
        name="Tryniq related meetings",
        task=task,
        evaluators=[retrieval_scores, operational_evaluator],
        run_evaluators=[
            build_run_evaluator(primary_metrics=frozenset({"recall_at_5", "ndcg_at_5"}))
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            embedding_model_id="production",
            metric_versions={"langfuse": "4.14.0", "ranx": "0.3.21"},
        ),
    )
