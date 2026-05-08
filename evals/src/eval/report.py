"""Aggregate results/<run_id>/summary.json files into RESULTS.md and MODEL_CARD.md tables."""

import json
import re
from collections import defaultdict
from pathlib import Path

from eval.paths import EVALS_ROOT, RESULTS_ROOT
from eval.registry import comparison_models_for_family

_RESULTS_MD = EVALS_ROOT / "RESULTS.md"
_MODEL_CARD = EVALS_ROOT / "MODEL_CARD.md"


def _collect() -> dict[str, dict[str, dict]]:
    """Returns {model_name: {dataset_name: chosen_summary}}.

    Within identical decoding configs and limits, the latest run wins. Across
    different (decoding_hash, limit) buckets for the same (model, dataset), the
    bucket with the most samples wins — so a 50-sample smoke run never silently
    clobbers a full-dataset run, and a stale decoding config never beats a fresh
    one with the same coverage.
    """
    if not RESULTS_ROOT.exists():
        return defaultdict(dict)

    # bucket = (model, dataset, decoding_hash, limit) -> latest summary by run_id sort
    buckets: dict[tuple[str, str, str, str], dict] = {}
    for run_dir in sorted(RESULTS_ROOT.iterdir()):
        summary_path = run_dir / "summary.json"
        meta_path = run_dir / "meta.json"
        if not summary_path.exists():
            continue
        s = json.loads(summary_path.read_text())
        decoding_hash = "legacy"
        limit_key = "all"
        if meta_path.exists():
            try:
                m = json.loads(meta_path.read_text())
                decoding_hash = m.get("decoding_hash", "legacy")
                limit = m.get("limit")
                limit_key = "all" if limit is None else str(limit)
            except Exception:
                pass
        key = (s["model"], s["dataset"], decoding_hash, limit_key)
        buckets[key] = s  # sorted iteration → latest wins

    # Pick best bucket per (model, dataset): max n_samples, ties broken by recency.
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for (model, dataset, _h, _l), summary in buckets.items():
        by_pair[(model, dataset)].append(summary)
    for (model, dataset), summaries in by_pair.items():
        # Higher n_samples first; then by run_id (lex-sortable timestamp prefix) desc.
        summaries.sort(
            key=lambda s: (s.get("n_samples", 0), s.get("run_id", "")),
            reverse=True,
        )
        out[model][dataset] = summaries[0]
    return out


def _fmt(v: float | None, fmt: str = ".2%") -> str:
    if v is None:
        return "—"
    if fmt.endswith("%"):
        return f"{v:.2%}".replace("%", " %")
    return f"{v:{fmt}}"


def _fmt_wer_with_ci(s: dict) -> str:
    wer = s.get("wer_normalized")
    if wer is None:
        return "—"
    base = _fmt(wer)
    lo = s.get("wer_normalized_ci_low")
    hi = s.get("wer_normalized_ci_high")
    if lo is not None and hi is not None:
        return f"{base} [{_fmt(lo)}, {_fmt(hi)}]"
    return base


def _table_for_family(family: str, results: dict[str, dict[str, dict]]) -> str:
    models = comparison_models_for_family(family)  # type: ignore[arg-type]
    if not models:
        return "_no models registered_"

    datasets = sorted({ds for m in models for ds in results.get(m.name, {})})
    if not datasets:
        return "_no runs yet_"

    if family == "diarization":
        header_parts = ["Model", "License", "Released"]
        for d in datasets:
            header_parts += [f"DER+OV {d}", f"DER−OV {d}", f"M/FA/Conf {d}"]
        header = "| " + " | ".join(header_parts) + " |"
        sep = "|" + "|".join(["---"] * len(header_parts)) + "|"
        rows = []
        for m in models:
            row = [f"`{m.name}`", m.license or "—", m.release_date or "—"]
            for d in datasets:
                s = results.get(m.name, {}).get(d)
                if s is None:
                    row += ["—", "—", "—"]
                else:
                    miss = s.get("der_missed")
                    fa = s.get("der_false_alarm")
                    conf = s.get("der_confusion")
                    decomp = (
                        f"{_fmt(miss)} / {_fmt(fa)} / {_fmt(conf)}"
                        if miss is not None else "—"
                    )
                    row += [
                        _fmt(s.get("der_with_overlap") or s.get("der")),
                        _fmt(s.get("der_no_overlap")),
                        decomp,
                    ]
            rows.append("| " + " | ".join(row) + " |")
        return "\n".join([header, sep, *rows]) + (
            "\n\n_DER+OV = with-overlap (honest); DER−OV = pyannote skip_overlap=True (comparable to "
            "many published numbers). M/FA/Conf = missed / false-alarm / confusion split of DER+OV "
            "(fractions of reference speech, sum ≈ DER+OV). Confusion is the worst-failure mode for "
            "meeting transcripts — mis-attribution survives into the graph. Peak RSS deliberately "
            "omitted from cross-runtime tables — MLX/CoreML wired memory is invisible to ``psutil`` "
            "so numbers aren't comparable. Per-meeting RSS lives in ``results/<run_id>/per_meeting.json``._"
        )

    # ASR families: per-dataset WER + S/D/I + tail + RTF;
    # live also shows per-dataset first-partial / commit lag.
    header_parts = ["Model", "License", "Released"]
    for d in datasets:
        header_parts += [f"WER {d}", f"S/D/I {d}", f"Tail p90/p95 {d}", f"RTF {d}", f"Load(s) {d}"]
    if family == "live":
        for d in datasets:
            header_parts += [f"FirstP p50 {d} (ms)", f"Stab. {d}"]
    header = "| " + " | ".join(header_parts) + " |"
    sep = "|" + "|".join(["---"] * len(header_parts)) + "|"

    rows = []
    for m in models:
        row = [f"`{m.name}`", m.license or "—", m.release_date or "—"]
        for d in datasets:
            s = results.get(m.name, {}).get(d)
            if s is None:
                row += ["—", "—", "—", "—", "—"]
            else:
                sdi = (
                    f"{_fmt(s.get('subs_rate_normalized'))} / "
                    f"{_fmt(s.get('dels_rate_normalized'))} / "
                    f"{_fmt(s.get('ins_rate_normalized'))}"
                    if s.get("subs_rate_normalized") is not None else "—"
                )
                p90 = s.get("per_utt_wer_norm_p90")
                p95 = s.get("per_utt_wer_norm_p95")
                tail = (
                    f"{_fmt(p90)} / {_fmt(p95)}"
                    if p90 is not None else "—"
                )
                # Prefer steady_rtf (excludes cold load) when available; fall back
                # to the conflated rtf for legacy / fluid_audio runs.
                rtf_val = s.get("steady_rtf")
                if rtf_val is None:
                    rtf_val = s.get("rtf", 0.0)
                load_s = s.get("cold_load_s")
                load_cell = f"{load_s:.1f}" if load_s is not None else "—"
                row += [_fmt_wer_with_ci(s), sdi, tail, f"{rtf_val:.2f}", load_cell]
        if family == "live":
            for d in datasets:
                s = results.get(m.name, {}).get(d)
                if s is None:
                    row += ["—", "—"]
                else:
                    fp = s.get("median_first_partial_ms")
                    stab = s.get("stability_ratio")
                    row += [
                        f"{fp:.0f}" if fp is not None else "—",
                        f"{stab:.2f}" if stab is not None else "—",
                    ]
        rows.append("| " + " | ".join(row) + " |")
    note = (
        "\n\n_WER cells show the normalized WER with a 95% bootstrap CI. "
        "Peak RSS deliberately omitted from cross-runtime tables — MLX/CoreML wired "
        "memory is invisible to ``psutil`` so numbers aren't comparable. Per-run RSS "
        "lives in ``results/<run_id>/summary.json``._"
    )
    return "\n".join([header, sep, *rows]) + note


def _replace_block(text: str, marker: str, content: str) -> str:
    pattern = re.compile(
        rf"(<!-- {marker}_START -->)(.*?)(<!-- {marker}_END -->)", re.DOTALL
    )
    return pattern.sub(rf"\1\n{content}\n\3", text)


def generate() -> None:
    results = _collect()

    table_final = _table_for_family("final", results)
    table_live = _table_for_family("live", results)
    table_diar = _table_for_family("diarization", results)

    # ---- MODEL_CARD.md ----
    if _MODEL_CARD.exists():
        text = _MODEL_CARD.read_text()
        text = _replace_block(text, "TABLE_FINAL", table_final)
        text = _replace_block(text, "TABLE_LIVE", table_live)
        text = _replace_block(text, "TABLE_DIAR", table_diar)
        _MODEL_CARD.write_text(text)

    # ---- RESULTS.md ----
    blocks = [
        "## Final-pass ASR\n\n" + table_final,
        "\n\n## Live-pass ASR\n\n" + table_live,
        "\n\n## Diarization\n\n" + table_diar,
    ]
    body = "\n".join(blocks)
    if _RESULTS_MD.exists():
        text = _RESULTS_MD.read_text()
        text = _replace_block(text, "RESULTS", body)
        _RESULTS_MD.write_text(text)
