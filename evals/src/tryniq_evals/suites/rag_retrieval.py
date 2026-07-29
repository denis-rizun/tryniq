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
    suite="rag-retrieval",
    version="1.0.0",
    dataset_name="tryniq/rag-retrieval/1.0.0/smoke",
    concurrency=8,
    cadence=(Cadence.LOCAL, Cadence.PR, Cadence.NIGHTLY, Cadence.RELEASE),
    evaluators=("precision_at_k", "recall_at_k", "mrr", "map_at_5", "ndcg_at_5"),
    owner="ai-platform",
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.chat.constants import ChatScope
        from app.chat.services.retrieval import ChatRetriever
        from app.core.client import get_ai_client
        from app.db import async_session

        value = item_input(item)
        scope = ChatScope(value["scope"])
        meeting_id = UUID(value["meeting_id"]) if value.get("meeting_id") else None
        async with async_session() as session:
            context = await ChatRetriever(session, get_ai_client()).retrieve(
                value["query"],
                scope,
                meeting_id,
            )
        results = [
            {"id": str(hit.utterance_id), "score": hit.score, "kind": "utterance"}
            for hit in context.utterances
        ]
        results.extend(
            {"id": str(hit.node_id), "score": hit.score, "kind": "graph"}
            for hit in context.graph_nodes
        )
        return {"results": results}

    return (await capture_task(invoke)).model_dump(mode="json")


def experiment(context: RunnerContext) -> Any:
    from app.config import config

    return context.run_experiment(
        name="Tryniq RAG retrieval",
        task=task,
        evaluators=[retrieval_scores, operational_evaluator],
        run_evaluators=[
            build_run_evaluator(
                primary_metrics=frozenset({"recall_at_5", "ndcg_at_5"}),
                slice_keys=("scope", "query_type", "answerable", "meeting_length"),
            )
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            embedding_model_id="production",
            metric_versions={"langfuse": "4.14.0", "ranx": "0.3.21"},
            retrieval_configuration={
                "utterance_top_k": config.chat.UTTERANCE_TOP_K_ALL,
                "graph_top_k": config.chat.GRAPH_TOP_K_ALL,
            },
        ),
    )
