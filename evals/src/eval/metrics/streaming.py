
from dataclasses import dataclass


@dataclass
class StreamingStats:
    stability_ratio: float | None
    median_rewrite_words: float | None
    median_realtime_lag_ms: float | None
    p95_realtime_lag_ms: float | None
    n_utterances_with_partials: int


def _token_levenshtein(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


def _utterance_stability(partials: list[dict]) -> tuple[float, float]:
    if len(partials) < 2:
        return 1.0, 0.0
    stable = 0
    rewrites: list[int] = []
    for prev, cur in zip(partials, partials[1:], strict=False):
        prev_text = (prev.get("text") or "").strip()
        cur_text = (cur.get("text") or "").strip()
        if cur_text.startswith(prev_text):
            stable += 1
            rewrites.append(0)
        else:
            rewrites.append(_token_levenshtein(prev_text.split(), cur_text.split()))
    n_transitions = len(partials) - 1
    stability = stable / n_transitions
    rewrites_sorted = sorted(rewrites)
    median = rewrites_sorted[len(rewrites_sorted) // 2]
    return stability, float(median)


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vals = sorted(values)
    k = max(0, min(len(vals) - 1, int(round((p / 100.0) * (len(vals) - 1)))))
    return vals[k]


def aggregate(per_utt_partials: list[list[dict]]) -> StreamingStats:
    stabilities: list[float] = []
    rewrites: list[float] = []
    realtime_lags: list[float] = []
    n_with = 0

    for partials in per_utt_partials:
        if not partials:
            continue
        n_with += 1
        s, r = _utterance_stability(partials)
        stabilities.append(s)
        rewrites.append(r)
        for p in partials:
            audio_t = float(p.get("audio_t_end_s", 0.0))
            wall_ms = float(p.get("wall_offset_ms", 0.0))
            realtime_lags.append(wall_ms - audio_t * 1000.0)

    if not stabilities:
        return StreamingStats(None, None, None, None, 0)

    median_rewrite = sorted(rewrites)[len(rewrites) // 2]
    return StreamingStats(
        stability_ratio=sum(stabilities) / len(stabilities),
        median_rewrite_words=median_rewrite,
        median_realtime_lag_ms=_percentile(realtime_lags, 50),
        p95_realtime_lag_ms=_percentile(realtime_lags, 95),
        n_utterances_with_partials=n_with,
    )
