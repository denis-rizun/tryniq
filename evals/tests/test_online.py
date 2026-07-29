import pytest

from tryniq_evals.online import (
    OnlineEvaluationWorker,
    OnlineMonitoringSettings,
    redact,
    selected_for_sample,
)


def test_sampling_is_deterministic() -> None:
    assert selected_for_sample("trace-1", 0.5, "seed") == selected_for_sample(
        "trace-1", 0.5, "seed"
    )
    assert not selected_for_sample("trace-1", 0.0, "seed")
    assert selected_for_sample("trace-1", 1.0, "seed")


def test_redaction_is_recursive() -> None:
    payload = {
        "text": "Email Person@example.com or +49 151 12345678",
        "nested": ["token-secret_abcdefghijk"],
    }
    cleaned = redact(payload)
    assert "example.com" not in cleaned["text"]
    assert "12345678" not in cleaned["text"]
    assert "abcdefghijk" not in cleaned["nested"][0]


@pytest.mark.asyncio
async def test_online_worker_rejects_non_staging_or_production_environment() -> None:
    async def evaluator(_):
        return []

    worker = OnlineEvaluationWorker(
        object(),
        OnlineMonitoringSettings(monthly_cost_cap_usd=1.0),
        evaluator,
    )
    with pytest.raises(ValueError, match="staging or production"):
        await worker.run_once(environment="evaluation", month_spend_usd=0)
