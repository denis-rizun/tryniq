import asyncio
from typing import Any

import pytest

from tryniq_evals.adapters.deepeval import build_deepeval_evaluator
from tryniq_evals.contracts import FailureCategory, TaskOutcome


class FakeMetric:
    instances: set[int] = set()

    def __init__(self) -> None:
        self.score = None
        self.reason = None
        self.success = None
        self.instances.add(id(self))

    async def a_measure(self, test_case: Any) -> float:
        await asyncio.sleep(0)
        self.score = float(test_case)
        self.reason = f"score={test_case}"
        self.success = self.score >= 0.5
        return self.score


@pytest.mark.asyncio
async def test_deepeval_metric_is_isolated_per_item_and_preserves_reason() -> None:
    FakeMetric.instances.clear()
    evaluator = build_deepeval_evaluator(
        name="semantic",
        metric_factory=FakeMetric,
        test_case_factory=lambda _input, actual, _expected, _metadata: actual,
        rubric_version="rubric/1",
    )
    results = await asyncio.gather(
        *(
            evaluator(
                input="x",
                output=TaskOutcome.completed(index / 10).model_dump(mode="json"),
            )
            for index in range(10)
        )
    )
    assert len(FakeMetric.instances) == 10
    assert results[7].value == 0.7
    assert results[7].comment == "score=0.7"


@pytest.mark.asyncio
async def test_failed_outcome_is_zeroed_without_invoking_metric() -> None:
    FakeMetric.instances.clear()
    evaluator = build_deepeval_evaluator(
        name="semantic",
        metric_factory=FakeMetric,
        test_case_factory=lambda *_: None,
        rubric_version="rubric/1",
        gated=True,
    )
    result = await evaluator(
        input="x",
        output=TaskOutcome.failed(FailureCategory.UNEXPECTED, "boom").model_dump(mode="json"),
    )
    assert result.value == 0
    assert not FakeMetric.instances
