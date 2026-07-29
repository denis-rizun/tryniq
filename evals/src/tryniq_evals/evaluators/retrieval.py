from __future__ import annotations

from typing import Any

from langfuse.experiment import Evaluation
from ranx import Qrels, Run, evaluate

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


def retrieval_scores(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **_: Any,
) -> list[Evaluation]:
    del input
    outcome = TaskOutcome[Any].model_validate(output)
    if outcome.status == OutcomeStatus.SKIPPED:
        return []
    if outcome.status == OutcomeStatus.FAILED:
        return [
            Evaluation(
                name=name,
                value=0.0,
                comment=f"Zeroed because retrieval failed: {outcome.failure.category}",
                metadata={"gated": True},
            )
            for name in ("hit_rate_at_5", "recall_at_5", "ndcg_at_5")
        ]

    expected = expected_output or {}
    query_id = str((metadata or {}).get("stable_id", "query"))
    relevance = expected.get("relevance", expected.get("relevant_ids", {}))
    if isinstance(relevance, list):
        relevance = {str(doc_id): 1 for doc_id in relevance}
    ranked = outcome.payload.get("results", outcome.payload)
    if isinstance(ranked, dict):
        run_scores = {str(doc_id): float(score) for doc_id, score in ranked.items()}
    else:
        run_scores = {
            str(row.get("id", row.get("document_id"))): float(row.get("score", len(ranked) - index))
            for index, row in enumerate(ranked)
        }
    qrels = Qrels({query_id: {str(doc_id): int(score) for doc_id, score in relevance.items()}})
    run = Run({query_id: run_scores})
    requested = [
        "precision@1",
        "precision@3",
        "precision@5",
        "recall@1",
        "recall@3",
        "recall@5",
        "hit_rate@1",
        "hit_rate@3",
        "hit_rate@5",
        "mrr",
        "map@5",
        "ndcg@5",
    ]
    result = evaluate(qrels, run, requested, make_comparable=True)
    return [
        Evaluation(
            name=name.replace("@", "_at_"),
            value=float(result[name]),
            metadata={"engine": "ranx", "gated": name in {"recall@5", "ndcg@5"}},
        )
        for name in requested
    ]
