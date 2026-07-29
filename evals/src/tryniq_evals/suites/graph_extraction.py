from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from langfuse import RunnerContext

from tryniq_evals.adapters.deepeval import build_deepeval_evaluator
from tryniq_evals.contracts import Cadence, SuiteDefinition, capture_task
from tryniq_evals.evaluators.graph import graph_scores
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, prompt_identity, run_metadata

DEFINITION = SuiteDefinition(
    suite="graph-extraction",
    version="1.0.0",
    dataset_name="tryniq/graph-extraction/1.0.0/smoke",
    concurrency=4,
    cadence=(Cadence.LOCAL, Cadence.PR, Cadence.NIGHTLY, Cadence.RELEASE),
    evaluators=("node_macro_f1", "grounding_validity", "schema_validity"),
    owner="ai-platform",
    judge_metrics=True,
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.db import async_session
        from app.graph.client import GraphExtractor
        from app.graph.dependencies import build_graph_service
        from app.graph.services.window import GraphWindowProcessor
        from app.graph.tasks import _format_window, _load_window

        value = item_input(item)
        meeting_id = UUID(value["meeting_id"])
        async with async_session() as session:
            graph = build_graph_service(session)
            utterances = await _load_window(
                session,
                meeting_id,
                value.get("window_start"),
                value.get("window_end"),
            )
            prompt, short_refs = _format_window(meeting_id, utterances)
            result = await GraphWindowProcessor(
                session,
                graph,
                GraphExtractor(),
            ).process(meeting_id, utterances, prompt, short_refs)
            durable = await graph.get_graph(meeting_id)
        return {
            **durable.model_dump(mode="json"),
            "window_status": result.status,
            "rolled_back": result.rolled_back,
        }

    return (await capture_task(invoke)).model_dump(mode="json")


def _graph_case(
    input: Any,
    actual: Any,
    expected: Any,
    metadata: dict[str, Any] | None,
) -> LLMTestCase:
    del metadata
    transcript = input.get("transcript", input) if isinstance(input, dict) else input
    return LLMTestCase(
        input=str(transcript),
        actual_output=json.dumps(actual, sort_keys=True),
        expected_output=json.dumps(expected, sort_keys=True),
    )


def _graph_fidelity_metric() -> GEval:
    from app.core.prompts import GRAPH_FIDELITY_JUDGE_CRITERIA

    return GEval(
        name="Graph fidelity",
        criteria=GRAPH_FIDELITY_JUDGE_CRITERIA,
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        model=os.environ["EVAL_JUDGE_MODEL"],
    )


graph_fidelity = build_deepeval_evaluator(
    name="graph_fidelity",
    metric_factory=_graph_fidelity_metric,
    test_case_factory=_graph_case,
    rubric_version="graph-fidelity/1.0.0",
    gated=False,
)


def experiment(context: RunnerContext) -> Any:
    from app.core.prompts import GRAPH_FIDELITY_JUDGE_PROMPT, GRAPH_PROMPT

    return context.run_experiment(
        name="Tryniq graph extraction",
        task=task,
        evaluators=[graph_scores, graph_fidelity, operational_evaluator],
        run_evaluators=[
            build_run_evaluator(
                primary_metrics=frozenset({"node_macro_f1", "grounding_validity"}),
                slice_keys=("source", "difficulty", "meeting_length", "adversarial_type"),
            )
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            judge=True,
            model_id="production",
            embedding_model_id="production",
            prompt_identities={
                "graph": prompt_identity(GRAPH_PROMPT),
                "graph_fidelity_judge": prompt_identity(GRAPH_FIDELITY_JUDGE_PROMPT),
            },
            rubric_versions={
                "node_matching": "1.0.0",
                "graph_fidelity": "1.0.0",
            },
            metric_versions={"langfuse": "4.14.0", "deepeval": "4.1.4"},
        ),
    )
