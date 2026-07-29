from __future__ import annotations

from typing import Any
from uuid import UUID

from deepeval.metrics import GEval, SummarizationMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams
from langfuse import RunnerContext

from tryniq_evals.adapters.deepeval import build_deepeval_evaluator
from tryniq_evals.contracts import Cadence, SuiteDefinition, capture_task
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, prompt_identity, run_metadata

DEFINITION = SuiteDefinition(
    suite="metadata-extraction",
    version="1.0.0",
    dataset_name="tryniq/metadata-extraction/1.0.0/smoke",
    concurrency=4,
    cadence=(Cadence.LOCAL, Cadence.PR, Cadence.NIGHTLY, Cadence.RELEASE),
    evaluators=("summary_factuality", "summary_coverage", "reference_validity"),
    owner="ai-platform",
    judge_metrics=True,
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.db import async_session
        from app.metadata.dependencies import build_metadata_service

        meeting_id = UUID(item_input(item)["meeting_id"])
        async with async_session() as session:
            service = build_metadata_service(session)
            extraction = await service.extract_metadata(meeting_id)
            durable = await service.get_meeting_metadata(meeting_id)
        return {
            **durable.model_dump(mode="json"),
            "retry_count": extraction.retry_count,
            "fallback_used": extraction.fallback_used,
        }

    return (await capture_task(invoke)).model_dump(mode="json")


def _summary_case(
    input: Any,
    actual: Any,
    expected: Any,
    metadata: dict[str, Any] | None,
) -> LLMTestCase:
    del metadata
    transcript = input.get("transcript", "") if isinstance(input, dict) else str(input)
    return LLMTestCase(
        input=transcript,
        actual_output=str((actual or {}).get("summary", "")),
        expected_output=str((expected or {}).get("summary", "")),
    )


def _summary_metric() -> SummarizationMetric:
    import os

    return SummarizationMetric(model=os.environ["EVAL_JUDGE_MODEL"], include_reason=True)


summary_quality = build_deepeval_evaluator(
    name="summary_quality",
    metric_factory=_summary_metric,
    test_case_factory=_summary_case,
    rubric_version="metadata-summary/1.0.0",
    gated=False,
)


def _metadata_judge_metric(name: str, criteria: str) -> GEval:
    import os

    return GEval(
        name=name,
        criteria=criteria,
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        model=os.environ["EVAL_JUDGE_MODEL"],
    )


def _metadata_relevance_metric() -> GEval:
    from app.core.prompts import METADATA_RELEVANCE_JUDGE_CRITERIA

    return _metadata_judge_metric("Metadata relevance", METADATA_RELEVANCE_JUDGE_CRITERIA)


def _metadata_unsupported_metric() -> GEval:
    from app.core.prompts import METADATA_UNSUPPORTED_JUDGE_CRITERIA

    return _metadata_judge_metric(
        "Metadata unsupported claims",
        METADATA_UNSUPPORTED_JUDGE_CRITERIA,
    )


metadata_relevance = build_deepeval_evaluator(
    name="metadata_relevance",
    metric_factory=_metadata_relevance_metric,
    test_case_factory=_summary_case,
    rubric_version="metadata-relevance/1.0.0",
    gated=False,
)
metadata_unsupported_claims = build_deepeval_evaluator(
    name="metadata_unsupported_claims",
    metric_factory=_metadata_unsupported_metric,
    test_case_factory=_summary_case,
    rubric_version="metadata-unsupported-claims/1.0.0",
    gated=False,
)


def experiment(context: RunnerContext) -> Any:
    from app.core.prompts import (
        METADATA_PROMPT,
        METADATA_RELEVANCE_JUDGE_PROMPT,
        METADATA_SUMMARY_JUDGE_PROMPT,
        METADATA_UNSUPPORTED_JUDGE_PROMPT,
    )

    return context.run_experiment(
        name="Tryniq metadata extraction",
        task=task,
        evaluators=[
            summary_quality,
            metadata_relevance,
            metadata_unsupported_claims,
            operational_evaluator,
        ],
        run_evaluators=[
            build_run_evaluator(
                primary_metrics=frozenset({"summary_quality"}),
                slice_keys=("source", "meeting_length", "signal"),
            )
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            judge=True,
            model_id="production",
            prompt_identities={
                "metadata": prompt_identity(METADATA_PROMPT),
                "summary_judge": prompt_identity(METADATA_SUMMARY_JUDGE_PROMPT),
                "relevance_judge": prompt_identity(METADATA_RELEVANCE_JUDGE_PROMPT),
                "unsupported_claims_judge": prompt_identity(
                    METADATA_UNSUPPORTED_JUDGE_PROMPT
                ),
            },
            rubric_versions={
                "summary_quality": "1.0.0",
                "metadata_relevance": "1.0.0",
                "metadata_unsupported_claims": "1.0.0",
            },
            metric_versions={"langfuse": "4.14.0", "deepeval": "4.1.4"},
        ),
    )
