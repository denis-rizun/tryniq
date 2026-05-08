"""Live-only latency aggregations from per-utterance hypothesis fields."""

from dataclasses import dataclass


@dataclass
class LatencyStats:
    median_first_partial_ms: float | None
    p95_first_partial_ms: float | None
    median_commit_lag_ms: float | None
    p95_commit_lag_ms: float | None


def _percentile(values: list[float], p: float) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = max(0, min(len(vals) - 1, int(round((p / 100.0) * (len(vals) - 1)))))
    return vals[k]


def aggregate(first_partials: list[float | None], commit_lags: list[float | None]) -> LatencyStats:
    fps = [v for v in first_partials if v is not None]
    cls_ = [v for v in commit_lags if v is not None]
    return LatencyStats(
        median_first_partial_ms=_percentile(fps, 50) if fps else None,
        p95_first_partial_ms=_percentile(fps, 95) if fps else None,
        median_commit_lag_ms=_percentile(cls_, 50) if cls_ else None,
        p95_commit_lag_ms=_percentile(cls_, 95) if cls_ else None,
    )
