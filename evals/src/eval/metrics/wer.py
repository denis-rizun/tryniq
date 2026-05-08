
from dataclasses import dataclass, field

import jiwer
import numpy as np
from whisper_normalizer.english import EnglishTextNormalizer

_normalizer = EnglishTextNormalizer()

_BOOTSTRAP_RESAMPLES = 1000
_BOOTSTRAP_RNG = np.random.default_rng(seed=42)

                                     
MIN_REF_WORDS_FOR_PERCENTILES = 5

                                                                                 
_LENGTH_BUCKETS: tuple[tuple[str, float, float | None], ...] = (
    ("lt_5s", 0.0, 5.0),
    ("5_15s", 5.0, 15.0),
    ("gt_15s", 15.0, 60.0),
    ("long_form_60s+", 60.0, None),
)


@dataclass
class WerResult:
    wer: float
    cer: float
    wer_normalized: float
    cer_normalized: float
    words_ref: int
    words_hyp: int
    word_errors: int              
    word_errors_normalized: int
    chars_ref: int
    char_errors: int
    char_errors_normalized: int
                                                                       
    subs: int
    dels: int
    ins: int
                                                                                   
    subs_normalized: int
    dels_normalized: int
    ins_normalized: int


@dataclass
class BucketAggregate:
    label: str
    n_utts: int
    words_ref: int
    wer_normalized: float
    wer_normalized_ci_low: float | None
    wer_normalized_ci_high: float | None


@dataclass
class WerAggregate:
    wer: float
    cer: float
    wer_normalized: float
    cer_normalized: float
    words_ref: int
    words_hyp: int
                                                                   
    wer_normalized_ci_low: float | None
    wer_normalized_ci_high: float | None
    n_bootstrap: int
                                                 
    subs_rate: float
    dels_rate: float
    ins_rate: float
    subs_rate_normalized: float
    dels_rate_normalized: float
    ins_rate_normalized: float
                                                                            
    per_utt_wer_norm_p50: float | None
    per_utt_wer_norm_p90: float | None
    per_utt_wer_norm_p95: float | None
    per_utt_n_eligible: int
    per_utt_min_ref_words: int
                                                                             
    by_length: list[BucketAggregate] = field(default_factory=list)


def _process_words(ref: str, hyp: str) -> tuple[float, int, int, int, int, int]:
    if not ref.strip():
        if hyp.strip():
            n = len(hyp.split())
            return 1.0, n, 0, 0, 0, n
        return 0.0, 0, 0, 0, 0, 0
    try:
        out = jiwer.process_words(ref, hyp)
    except ValueError:
        n = len(ref.split())
        return 1.0, 0, n, 0, n, 0
    errors = out.substitutions + out.deletions + out.insertions
    n_ref = out.hits + out.substitutions + out.deletions
    return (
        float(out.wer), int(errors), int(n_ref),
        int(out.substitutions), int(out.deletions), int(out.insertions),
    )


def _process_chars(ref: str, hyp: str) -> tuple[float, int, int]:
    if not ref.strip():
        if hyp.strip():
            return 1.0, len(hyp), 0
        return 0.0, 0, 0
    try:
        out = jiwer.process_characters(ref, hyp)
    except ValueError:
        return 1.0, 0, len(ref)
    errors = out.substitutions + out.deletions + out.insertions
    n_ref = out.hits + out.substitutions + out.deletions
    return float(out.cer), int(errors), int(n_ref)


def score(reference: str, hypothesis: str) -> WerResult:
    ref_norm = _normalizer(reference)
    hyp_norm = _normalizer(hypothesis)

    wer_raw, w_err_raw, n_ref_raw, s_raw, d_raw, i_raw = _process_words(reference, hypothesis)
    wer_norm, w_err_norm, _n_norm, s_n, d_n, i_n = _process_words(ref_norm, hyp_norm)
    cer_raw, c_err_raw, n_chars_raw = _process_chars(reference, hypothesis)
    cer_norm, c_err_norm, _ = _process_chars(ref_norm, hyp_norm)

    return WerResult(
        wer=wer_raw,
        cer=cer_raw,
        wer_normalized=wer_norm,
        cer_normalized=cer_norm,
        words_ref=n_ref_raw,
        words_hyp=len(hypothesis.split()),
        word_errors=w_err_raw,
        word_errors_normalized=w_err_norm,
        chars_ref=n_chars_raw,
        char_errors=c_err_raw,
        char_errors_normalized=c_err_norm,
        subs=s_raw, dels=d_raw, ins=i_raw,
        subs_normalized=s_n, dels_normalized=d_n, ins_normalized=i_n,
    )


def _bootstrap_wer_norm(per_utt: list[WerResult]) -> tuple[float | None, float | None]:
    if len(per_utt) < 2:
        return None, None
    errors = np.array([r.word_errors_normalized for r in per_utt], dtype=np.float64)
    refs = np.array([r.words_ref for r in per_utt], dtype=np.float64)
    n = len(per_utt)
    samples = np.empty(_BOOTSTRAP_RESAMPLES, dtype=np.float64)
    for i in range(_BOOTSTRAP_RESAMPLES):
        idx = _BOOTSTRAP_RNG.integers(0, n, size=n)
        denom = refs[idx].sum()
        samples[i] = errors[idx].sum() / denom if denom > 0 else 0.0
    return float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))


def _per_utt_percentiles(per_utt: list[WerResult]) -> tuple[float | None, float | None, float | None, int]:
    eligible = [
        r.wer_normalized for r in per_utt
        if r.words_ref >= MIN_REF_WORDS_FOR_PERCENTILES
    ]
    if not eligible:
        return None, None, None, 0
    arr = np.array(eligible, dtype=np.float64)
    return (
        float(np.percentile(arr, 50)),
        float(np.percentile(arr, 90)),
        float(np.percentile(arr, 95)),
        len(eligible),
    )


def _bucket_for(audio_s: float) -> str | None:
    for label, lo, hi in _LENGTH_BUCKETS:
        if audio_s >= lo and (hi is None or audio_s < hi):
            return label
    return None


def aggregate_by_length(
    per_utt: list[WerResult], audio_durations: list[float],
) -> list[BucketAggregate]:
    if not per_utt or len(per_utt) != len(audio_durations):
        return []
    by_label: dict[str, list[WerResult]] = {label: [] for label, _, _ in _LENGTH_BUCKETS}
    for r, d in zip(per_utt, audio_durations, strict=True):
        b = _bucket_for(d)
        if b is not None:
            by_label[b].append(r)

    out: list[BucketAggregate] = []
    for label, _, _ in _LENGTH_BUCKETS:
        items = by_label[label]
        if not items:
            out.append(BucketAggregate(
                label=label, n_utts=0, words_ref=0,
                wer_normalized=0.0,
                wer_normalized_ci_low=None, wer_normalized_ci_high=None,
            ))
            continue
        total_ref = sum(r.words_ref for r in items) or 1
        wer_norm = sum(r.word_errors_normalized for r in items) / total_ref
        ci_low, ci_high = _bootstrap_wer_norm(items)
        out.append(BucketAggregate(
            label=label, n_utts=len(items),
            words_ref=sum(r.words_ref for r in items),
            wer_normalized=wer_norm,
            wer_normalized_ci_low=ci_low, wer_normalized_ci_high=ci_high,
        ))
    return out


def aggregate(
    per_utt: list[WerResult],
    audio_durations: list[float] | None = None,
) -> WerAggregate:
    if not per_utt:
        return WerAggregate(
            0.0, 0.0, 0.0, 0.0, 0, 0, None, None, 0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            None, None, None, 0, MIN_REF_WORDS_FOR_PERCENTILES,
            by_length=[],
        )

    total_ref = sum(r.words_ref for r in per_utt) or 1
    total_chars = sum(r.chars_ref for r in per_utt) or 1
    wer_raw = sum(r.word_errors for r in per_utt) / total_ref
    wer_norm = sum(r.word_errors_normalized for r in per_utt) / total_ref
    cer_raw = sum(r.char_errors for r in per_utt) / total_chars
    cer_norm = sum(r.char_errors_normalized for r in per_utt) / total_chars

    ci_low, ci_high = _bootstrap_wer_norm(per_utt)
    p50, p90, p95, n_elig = _per_utt_percentiles(per_utt)

    subs_raw = sum(r.subs for r in per_utt)
    dels_raw = sum(r.dels for r in per_utt)
    ins_raw = sum(r.ins for r in per_utt)
    subs_n = sum(r.subs_normalized for r in per_utt)
    dels_n = sum(r.dels_normalized for r in per_utt)
    ins_n = sum(r.ins_normalized for r in per_utt)

    by_length = aggregate_by_length(per_utt, audio_durations) if audio_durations else []

    return WerAggregate(
        wer=wer_raw,
        cer=cer_raw,
        wer_normalized=wer_norm,
        cer_normalized=cer_norm,
        words_ref=total_ref,
        words_hyp=sum(r.words_hyp for r in per_utt),
        wer_normalized_ci_low=ci_low,
        wer_normalized_ci_high=ci_high,
        n_bootstrap=_BOOTSTRAP_RESAMPLES if len(per_utt) >= 2 else 0,
        subs_rate=subs_raw / total_ref,
        dels_rate=dels_raw / total_ref,
        ins_rate=ins_raw / total_ref,
        subs_rate_normalized=subs_n / total_ref,
        dels_rate_normalized=dels_n / total_ref,
        ins_rate_normalized=ins_n / total_ref,
        per_utt_wer_norm_p50=p50,
        per_utt_wer_norm_p90=p90,
        per_utt_wer_norm_p95=p95,
        per_utt_n_eligible=n_elig,
        per_utt_min_ref_words=MIN_REF_WORDS_FOR_PERCENTILES,
        by_length=by_length,
    )
