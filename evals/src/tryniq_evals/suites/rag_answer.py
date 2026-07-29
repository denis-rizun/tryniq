from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from langfuse import RunnerContext

from tryniq_evals.adapters.deepeval import build_deepeval_evaluator
from tryniq_evals.contracts import Cadence, SuiteDefinition, capture_task
from tryniq_evals.evaluators.citations import citation_scores
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, prompt_identity, run_metadata

DEFINITION = SuiteDefinition(
    suite="rag-answer",
    version="1.0.0",
    dataset_name="tryniq/rag-answer/1.0.0/smoke",
    concurrency=4,
    cadence=(Cadence.LOCAL, Cadence.PR, Cadence.NIGHTLY, Cadence.RELEASE),
    evaluators=("faithfulness", "answer_relevancy", "citation_id_validity"),
    owner="ai-platform",
    judge_metrics=True,
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.chat.constants import ChatScope
        from app.chat.dependencies import get_responder
        from app.chat.services.responder import AnswerComplete
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
            completed: AnswerComplete | None = None
            async for event in get_responder().stream_answer(
                value["query"],
                scope,
                [],
                context,
            ):
                if isinstance(event, AnswerComplete):
                    completed = event
        if completed is None:
            raise RuntimeError("chat responder did not emit AnswerComplete")
        return {
            "answer": completed.text,
            "citations": [citation.model_dump(mode="json") for citation in completed.citations],
            "retrieved_utterance_ids": [str(hit.utterance_id) for hit in context.utterances],
            "retrieval_context": [hit.text for hit in context.utterances],
            "model": completed.model,
        }

    return (await capture_task(invoke)).model_dump(mode="json")


def _answer_case(
    input: Any,
    actual: Any,
    expected: Any,
    metadata: dict[str, Any] | None,
) -> LLMTestCase:
    del metadata
    return LLMTestCase(
        input=str(input.get("query", input) if isinstance(input, dict) else input),
        actual_output=str((actual or {}).get("answer", "")),
        expected_output=str((expected or {}).get("answer", "")),
        retrieval_context=list((actual or {}).get("retrieval_context", [])),
    )


faithfulness = build_deepeval_evaluator(
    name="faithfulness",
    metric_factory=lambda: FaithfulnessMetric(
        model=os.environ["EVAL_JUDGE_MODEL"],
        include_reason=True,
    ),
    test_case_factory=_answer_case,
    rubric_version="rag-faithfulness/1.0.0",
    gated=False,
)
answer_relevancy = build_deepeval_evaluator(
    name="answer_relevancy",
    metric_factory=lambda: AnswerRelevancyMetric(
        model=os.environ["EVAL_JUDGE_MODEL"],
        include_reason=True,
    ),
    test_case_factory=_answer_case,
    rubric_version="rag-answer-relevancy/1.0.0",
    gated=False,
)


def experiment(context: RunnerContext) -> Any:
    from app.config import config
    from app.core.prompts import (
        CHAT_PROMPT,
        RAG_FAITHFULNESS_JUDGE_PROMPT,
        RAG_RELEVANCY_JUDGE_PROMPT,
    )

    return context.run_experiment(
        name="Tryniq RAG answer",
        task=task,
        evaluators=[
            faithfulness,
            answer_relevancy,
            citation_scores,
            operational_evaluator,
        ],
        run_evaluators=[
            build_run_evaluator(
                primary_metrics=frozenset(
                    {"faithfulness", "answer_relevancy", "citation_id_validity"}
                ),
                slice_keys=("scope", "query_type", "answerable"),
            )
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            judge=True,
            model_id="production",
            embedding_model_id="production",
            prompt_identities={
                "chat": prompt_identity(CHAT_PROMPT),
                "faithfulness_judge": prompt_identity(RAG_FAITHFULNESS_JUDGE_PROMPT),
                "relevancy_judge": prompt_identity(RAG_RELEVANCY_JUDGE_PROMPT),
            },
            rubric_versions={
                "faithfulness": "1.0.0",
                "answer_relevancy": "1.0.0",
            },
            metric_versions={"langfuse": "4.14.0", "deepeval": "4.1.4"},
            retrieval_configuration={
                "utterance_top_k": config.chat.UTTERANCE_TOP_K_ALL,
                "graph_top_k": config.chat.GRAPH_TOP_K_ALL,
            },
        ),
    )
