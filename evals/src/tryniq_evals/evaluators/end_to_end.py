from __future__ import annotations

from typing import Any

from langfuse.experiment import Evaluation

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


def end_to_end_scores(
    *,
    output: Any,
    **_: Any,
) -> list[Evaluation]:
    outcome = TaskOutcome[Any].model_validate(output)
    if outcome.status == OutcomeStatus.SKIPPED:
        return []
    if outcome.status == OutcomeStatus.FAILED:
        reason = f"Production workflow failed: {outcome.failure.category}"
        return [
            Evaluation(name="completion", value=0.0, comment=reason),
            Evaluation(name="idempotency", value=0.0, comment=reason),
        ]

    payload = outcome.payload or {}
    return [
        Evaluation(
            name="completion",
            value=float(str(payload.get("status")) == "final"),
            metadata={"gated": True},
        ),
        Evaluation(
            name="idempotency",
            value=float(bool(payload.get("idempotent"))),
            metadata={"gated": True},
        ),
    ]
