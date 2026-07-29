from __future__ import annotations

from typing import Any

from langfuse.experiment import Evaluation

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


def citation_scores(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **_: Any,
) -> list[Evaluation]:
    del input, metadata
    outcome = TaskOutcome[Any].model_validate(output)
    if outcome.status == OutcomeStatus.SKIPPED:
        return []
    if outcome.status == OutcomeStatus.FAILED:
        return [
            Evaluation(
                name="citation_id_validity",
                value=0.0,
                comment=f"Zeroed because answer task failed: {outcome.failure.category}",
                metadata={"gated": True},
            )
        ]
    payload = outcome.payload or {}
    retrieved = {str(value) for value in payload.get("retrieved_utterance_ids", [])}
    citations = payload.get("citations", [])
    valid = sum(str(citation.get("utterance_id")) in retrieved for citation in citations)
    expected_ids = {
        str(value) for value in (expected_output or {}).get("citation_utterance_ids", [])
    }
    cited_ids = {str(citation.get("utterance_id")) for citation in citations}
    return [
        Evaluation(
            name="citation_id_validity",
            value=valid / len(citations) if citations else float(not expected_ids),
            metadata={"gated": True},
        ),
        Evaluation(
            name="citation_precision",
            value=len(cited_ids & expected_ids) / len(cited_ids)
            if cited_ids
            else float(not expected_ids),
        ),
        Evaluation(
            name="citation_recall",
            value=len(cited_ids & expected_ids) / len(expected_ids) if expected_ids else 1.0,
        ),
    ]
