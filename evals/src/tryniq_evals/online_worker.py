from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from langfuse import Langfuse
from langfuse.experiment import Evaluation

from tryniq_evals.online import OnlineEvaluationWorker, OnlineMonitoringSettings


async def evaluate_trace(payload: dict[str, Any]) -> list[Evaluation]:
    from app.core.prompts import (
        ONLINE_TRACE_QUALITY_JUDGE_CRITERIA,
        ONLINE_TRACE_QUALITY_JUDGE_PROMPT,
    )

    judge_model = os.environ.get("EVAL_JUDGE_MODEL")
    if not judge_model:
        raise ValueError("EVAL_JUDGE_MODEL is required for online evaluation")
    estimated_cost = float(os.environ["EVAL_ONLINE_ESTIMATED_ITEM_COST_USD"])
    metric = GEval(
        name="Online trace quality",
        criteria=ONLINE_TRACE_QUALITY_JUDGE_CRITERIA,
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
        ],
        model=judge_model,
    )
    test_case = LLMTestCase(
        input=json.dumps(payload["input"], sort_keys=True),
        actual_output=json.dumps(payload["output"], sort_keys=True),
    )
    await metric.a_measure(test_case)
    if metric.score is None:
        raise ValueError("online DeepEval metric returned no score")
    return [
        Evaluation(
            name="online.trace_quality",
            value=float(metric.score),
            comment=metric.reason or "DeepEval metric did not provide a reason",
            metadata={
                "cost_usd": estimated_cost,
                "engine": "deepeval",
                "judge_model": judge_model,
                "rubric_version": ONLINE_TRACE_QUALITY_JUDGE_PROMPT.version,
                "rubric_sha256": ONLINE_TRACE_QUALITY_JUDGE_PROMPT.sha256,
            },
        )
    ]


async def run() -> None:
    environment = os.environ["EVAL_ONLINE_ENVIRONMENT"]
    settings = OnlineMonitoringSettings(
        monthly_cost_cap_usd=float(os.environ["EVAL_ONLINE_MONTHLY_COST_CAP_USD"]),
    )
    worker = OnlineEvaluationWorker(Langfuse(), settings, evaluate_trace)
    scored, spend = await worker.run_once(
        environment=environment,
        month_spend_usd=float(os.environ.get("EVAL_ONLINE_MONTH_SPEND_USD", "0")),
    )
    print(json.dumps({"environment": environment, "scored": scored, "month_spend_usd": spend}))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
