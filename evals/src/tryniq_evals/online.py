from __future__ import annotations

import hashlib
import re
from collections.abc import Awaitable, Callable
from typing import Any

from langfuse.experiment import Evaluation
from pydantic import BaseModel, ConfigDict, Field


class OnlineMonitoringSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    staging_sample_rate: float = Field(default=0.05, ge=0, le=0.05)
    production_sample_rate: float = Field(default=0.01, ge=0, le=0.01)
    monthly_cost_cap_usd: float = Field(gt=0)
    page_size: int = Field(default=100, ge=1, le=1000)
    seed: str = "tryniq-online-eval-v1"


def selected_for_sample(trace_id: str, rate: float, seed: str) -> bool:
    digest = hashlib.sha256(f"{seed}:{trace_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big") / (2**64 - 1)
    return bucket < rate


_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)")
_TOKEN = re.compile(
    r"(?i)\b(?:bearer\s+)?(?:sk|pk|api|token|secret)[-_][a-z0-9_-]{8,}\b"
)


def redact(value: Any) -> Any:
    if isinstance(value, str):
        value = _EMAIL.sub("[REDACTED_EMAIL]", value)
        value = _PHONE.sub("[REDACTED_PHONE]", value)
        return _TOKEN.sub("[REDACTED_TOKEN]", value)
    if isinstance(value, dict):
        return {str(key): redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


TraceEvaluator = Callable[[dict[str, Any]], Awaitable[list[Evaluation]]]


class OnlineEvaluationWorker:
    """Score deterministic samples of completed Langfuse traces in-place."""

    def __init__(
        self,
        client: Any,
        settings: OnlineMonitoringSettings,
        evaluator: TraceEvaluator,
    ) -> None:
        self.client = client
        self.settings = settings
        self.evaluator = evaluator

    async def run_once(
        self,
        *,
        environment: str,
        month_spend_usd: float,
    ) -> tuple[int, float]:
        if environment not in {"staging", "production"}:
            raise ValueError("online evaluation environment must be staging or production")
        rate = (
            self.settings.staging_sample_rate
            if environment == "staging"
            else self.settings.production_sample_rate
        )
        if month_spend_usd >= self.settings.monthly_cost_cap_usd:
            return 0, month_spend_usd

        traces = self.client.api.trace.list(
            limit=self.settings.page_size,
            environment=environment,
            order_by="timestamp.desc",
        )
        scored = 0
        spend = month_spend_usd
        for trace in traces.data:
            if trace.output is None:
                continue
            if not selected_for_sample(trace.id, rate, self.settings.seed):
                continue
            existing = self.client.api.scores.get_many(trace_id=trace.id, limit=100)
            if any(
                score.name.startswith("online.")
                or bool((getattr(score, "metadata", None) or {}).get("online_evaluator"))
                for score in existing.data
            ):
                continue
            payload = {
                "trace_id": trace.id,
                "name": trace.name,
                "input": redact(trace.input),
                "output": redact(trace.output),
                "metadata": redact(trace.metadata or {}),
                "environment": environment,
            }
            evaluations = await self.evaluator(payload)
            item_cost = sum(
                float((evaluation.metadata or {}).get("cost_usd", 0.0))
                for evaluation in evaluations
            )
            if spend + item_cost > self.settings.monthly_cost_cap_usd:
                break
            for evaluation in evaluations:
                self.client.create_score(
                    trace_id=trace.id,
                    name=evaluation.name,
                    value=evaluation.value,
                    comment=evaluation.comment,
                    data_type=evaluation.data_type,
                    metadata={
                        **(evaluation.metadata or {}),
                        "online_evaluator": True,
                        "redacted_before_judging": True,
                    },
                    environment=environment,
                )
            spend += item_cost
            scored += 1
        self.client.flush()
        return scored, spend
