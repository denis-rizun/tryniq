
import csv
import json
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import psutil
import soundfile as sf

from eval.decoding import DEFAULT_DECODING, DecodingConfig
from eval.manifest import Sample, read_manifest, read_reference
from eval.metrics import streaming as streaming_metric
from eval.metrics import wer as wer_metric
from eval.metrics.latency import aggregate as agg_latency
from eval.metrics.memory import MemorySampler
from eval.metrics.rtf import rtf as compute_rtf
from eval.paths import ENVS_ROOT, RESULTS_ROOT, dataset_cache
from eval.registry import Dataset, Model
from eval.types import Hypothesis

HYPOTHESIS_SENTINEL = "---HYPOTHESIS-JSON---"
READY_SENTINEL = "---ADAPTER-READY---"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent
        ).decode().strip()
    except Exception:
        return "unknown"


_FREEZE_CACHE: dict[str, list[str]] = {}


def _adapter_env_freeze(env: str) -> list[str]:
    if env in _FREEZE_CACHE:
        return _FREEZE_CACHE[env]
    env_dir = ENVS_ROOT / env
    try:
        out = subprocess.check_output(
            ["uv", "pip", "freeze"], cwd=env_dir,
            stderr=subprocess.DEVNULL, text=True, timeout=60.0,
        )
        frozen = [ln for ln in out.splitlines() if ln.strip()]
    except Exception:
        frozen = []
    _FREEZE_CACHE[env] = frozen
    return frozen


def _nvidia_smi_version() -> str | None:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL, text=True, timeout=5.0,
        ).strip().splitlines()
        return out[0] if out else None
    except Exception:
        return None


def _audio_duration(path: Path) -> float:
    try:
        info = sf.info(str(path))
        return float(info.frames) / float(info.samplerate)
    except Exception:
        return 0.0


def _read_text_reference(text_field: str) -> str:
    return read_reference(text_field)


def _adapter_command(
    model: Model, audio: str | None, decoding: DecodingConfig
) -> tuple[list[str], Path]:
    env_dir = ENVS_ROOT / model.env
    cmd = ["uv", "run", "python", "-m", model.adapter_module]
    if audio is not None:
        cmd += ["--audio", audio]
    cmd += decoding.to_cli_args()
    cmd += list(model.extra_args)
    return cmd, env_dir


def _extract_hypothesis(stdout: str) -> tuple[Hypothesis | None, str]:
    lines = stdout.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == HYPOTHESIS_SENTINEL and i + 1 < len(lines):
            payload = lines[i + 1]
            try:
                return Hypothesis.model_validate_json(payload), ""
            except Exception as e:
                return None, f"failed to parse hypothesis JSON: {e}\nLINE:\n{payload}"
    return None, "no hypothesis sentinel found in stdout"


def _extract_load_s(stdout: str) -> float | None:
    lines = stdout.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == READY_SENTINEL and i + 1 < len(lines):
            try:
                payload = json.loads(lines[i + 1])
            except Exception:
                return None
            v = payload.get("load_s")
            return float(v) if v is not None else None
    return None


def _run_cold(
    model: Model, sample: Sample, timeout_s: float, decoding: DecodingConfig,
) -> tuple[Hypothesis | None, str, float, float, float | None]:
    cmd, cwd = _adapter_command(model, sample.audio, decoding)
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    sampler = MemorySampler(pid=proc.pid)
    sampler.start()
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        peak = sampler.stop()
        return None, f"TIMEOUT after {timeout_s}s\n{stderr}", time.perf_counter() - t0, peak, None
    wall = time.perf_counter() - t0
    peak = sampler.stop()

    if proc.returncode != 0:
        return None, stderr or f"exited with {proc.returncode}", wall, peak, None

    hyp, parse_err = _extract_hypothesis(stdout)
    load_s = _extract_load_s(stdout)
    if hyp is None:
        return None, f"{parse_err}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}", wall, peak, load_s
    return hyp, stderr, wall, peak, load_s


class _WarmAdapter:

    def __init__(self, model: Model, timeout_s: float, decoding: DecodingConfig) -> None:
        cmd, cwd = _adapter_command(model, audio=None, decoding=decoding)
        cmd = cmd + ["--warm-stdin"]
        self.timeout_s = timeout_s
        self.proc = subprocess.Popen(
            cmd, cwd=cwd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        self.sampler = MemorySampler(pid=self.proc.pid)
        self.sampler.start()
        self.stderr_buf: list[str] = []
                                                                             
                                                                                 
        self.cold_load_s: float | None = None
        self._wait_for_ready()

    def _wait_for_ready(self) -> None:
        assert self.proc.stdout is not None
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                return
            if line.strip() == READY_SENTINEL:
                payload = self.proc.stdout.readline()
                try:
                    v = json.loads(payload).get("load_s")
                    self.cold_load_s = float(v) if v is not None else None
                except Exception:
                    self.cold_load_s = None
                return

    def transcribe(self, sample: Sample) -> tuple[Hypothesis | None, str, float]:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        t0 = time.perf_counter()
        try:
            self.proc.stdin.write(sample.audio + "\n")
            self.proc.stdin.flush()
        except BrokenPipeError:
            wall = time.perf_counter() - t0
            return None, "adapter stdin closed (subprocess died)", wall

                                                                 
        deadline = time.monotonic() + self.timeout_s
        sentinel_seen = False
        while time.monotonic() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                break
            if sentinel_seen:
                wall = time.perf_counter() - t0
                try:
                    return Hypothesis.model_validate_json(line.strip()), "", wall
                except Exception as e:
                    return None, f"failed to parse hypothesis JSON: {e}\nLINE: {line}", wall
            if line.strip() == HYPOTHESIS_SENTINEL:
                sentinel_seen = True
        wall = time.perf_counter() - t0
        return None, f"warm-mode timeout after {self.timeout_s}s waiting for sentinel", wall

    def close(self) -> tuple[float, str]:
        assert self.proc.stdin is not None
        try:
            self.proc.stdin.write("STOP\n")
            self.proc.stdin.flush()
            self.proc.stdin.close()
        except BrokenPipeError:
            pass
        try:
            _, stderr = self.proc.communicate(timeout=10.0)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            _, stderr = self.proc.communicate()
        peak = self.sampler.stop()
        return peak, stderr or ""


def run(
    model: Model,
    dataset: Dataset,
    *,
    limit: int | None = None,
    timeout_s: float = 600.0,
    warm: bool = False,
    decoding: DecodingConfig | None = None,
) -> Path:
    decoding = decoding or DEFAULT_DECODING
    manifest_path = dataset_cache(dataset.name) / "manifest.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"manifest missing at {manifest_path}. Run `uv run eval prepare {dataset.name}` first."
        )

    decoding_hash = decoding.hash()
    limit_tag = f"l{limit}" if limit else "lall"
    run_id = (
        f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        f"-{model.name}-{dataset.name}-{limit_tag}-{decoding_hash}"
    )
    run_dir = RESULTS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    samples = list(read_manifest(manifest_path))
    if limit:
        samples = samples[:limit]

    per_utt_rows: list[dict] = []
    per_utt_wer: list[wer_metric.WerResult] = []
    per_utt_audio_s: list[float] = []
    per_utt_partials: list[list[dict]] = []
    first_partials: list[float | None] = []
    commit_lags: list[float | None] = []
    cold_loads: list[float] = []                                      
    peak_rss_max = 0.0
    errors_log: list[str] = []
    total_audio_s = 0.0
    total_wall_s = 0.0
    failed = 0

    warm_adapter: _WarmAdapter | None = None
    if warm:
        warm_adapter = _WarmAdapter(model, timeout_s=timeout_s, decoding=decoding)

    try:
        for sample in samples:
            ref = _read_text_reference(sample.text)
            audio_s = sample.duration_s or _audio_duration(Path(sample.audio))
            total_audio_s += audio_s

            sample_load_s: float | None = None
            if warm_adapter is not None:
                hyp, stderr, wall_s = warm_adapter.transcribe(sample)
                peak_mb = warm_adapter.sampler.peak_rss_mb
            else:
                hyp, stderr, wall_s, peak_mb, sample_load_s = _run_cold(
                    model, sample, timeout_s=timeout_s, decoding=decoding,
                )
                if sample_load_s is not None:
                    cold_loads.append(sample_load_s)
            total_wall_s += wall_s
            peak_rss_max = max(peak_rss_max, peak_mb)

            if hyp is None:
                failed += 1
                errors_log.append(f"[{sample.id}] {stderr}")
                per_utt_rows.append({
                    "id": sample.id, "audio": sample.audio,
                    "audio_s": audio_s, "wall_s": wall_s,
                    "peak_rss_mb": peak_mb, "wer": None, "cer": None,
                    "wer_norm": None, "cer_norm": None, "hypothesis": "",
                    "reference": ref,
                    "error": (stderr.splitlines()[0] if stderr else "unknown"),
                })
                continue

            wer_r = wer_metric.score(ref, hyp.text)
            per_utt_wer.append(wer_r)
            per_utt_audio_s.append(audio_s)
            per_utt_partials.append([p.model_dump() for p in hyp.partials])
            first_partials.append(hyp.time_to_first_partial_ms)
            commit_lags.append(hyp.partial_to_final_lag_ms)
            per_utt_rows.append({
                "id": sample.id, "audio": sample.audio,
                "audio_s": audio_s, "wall_s": wall_s,
                "peak_rss_mb": peak_mb,
                "wer": wer_r.wer, "cer": wer_r.cer,
                "wer_norm": wer_r.wer_normalized, "cer_norm": wer_r.cer_normalized,
                "hypothesis": hyp.text, "reference": ref, "error": "",
            })
    finally:
        if warm_adapter is not None:
            warm_peak, warm_stderr = warm_adapter.close()
            peak_rss_max = max(peak_rss_max, warm_peak)
            if warm_stderr:
                errors_log.append(f"[adapter-stderr]\n{warm_stderr}")

                       
    agg = wer_metric.aggregate(per_utt_wer, per_utt_audio_s)
    lat = agg_latency(first_partials, commit_lags)
    stream = streaming_metric.aggregate(per_utt_partials)

                                                                               
    if warm:
        cold_load_s_total: float | None = (
            warm_adapter.cold_load_s if warm_adapter is not None else None
        )
        steady_wall_s = total_wall_s
    else:
        cold_load_s_total = sum(cold_loads) / len(cold_loads) if cold_loads else None
                                                                                 
                                                               
        steady_wall_s = max(0.0, total_wall_s - sum(cold_loads))
    steady_rtf = compute_rtf(steady_wall_s, total_audio_s)

    summary = {
        "run_id": run_id,
        "model": model.name,
        "dataset": dataset.name,
        "mode": "warm" if warm else "cold",
        "n_samples": len(samples),
        "n_failed": failed,
        "audio_seconds_total": total_audio_s,
        "wall_seconds_total": total_wall_s,
        "rtf": compute_rtf(total_wall_s, total_audio_s),
                                                
        "cold_load_s": cold_load_s_total,
        "steady_rtf": steady_rtf,
        "n_cold_load_samples": len(cold_loads) if not warm else (1 if cold_load_s_total is not None else 0),
        "peak_rss_mb": peak_rss_max,
        "wer": agg.wer,
        "cer": agg.cer,
        "wer_normalized": agg.wer_normalized,
        "cer_normalized": agg.cer_normalized,
        "wer_normalized_ci_low": agg.wer_normalized_ci_low,
        "wer_normalized_ci_high": agg.wer_normalized_ci_high,
        "n_bootstrap": agg.n_bootstrap,
                                                    
        "subs_rate": agg.subs_rate,
        "dels_rate": agg.dels_rate,
        "ins_rate": agg.ins_rate,
        "subs_rate_normalized": agg.subs_rate_normalized,
        "dels_rate_normalized": agg.dels_rate_normalized,
        "ins_rate_normalized": agg.ins_rate_normalized,
                                                                                 
        "per_utt_wer_norm_p50": agg.per_utt_wer_norm_p50,
        "per_utt_wer_norm_p90": agg.per_utt_wer_norm_p90,
        "per_utt_wer_norm_p95": agg.per_utt_wer_norm_p95,
        "per_utt_n_eligible": agg.per_utt_n_eligible,
        "per_utt_min_ref_words": agg.per_utt_min_ref_words,
                                           
        "wer_by_length": [asdict(b) for b in agg.by_length],
        "median_first_partial_ms": lat.median_first_partial_ms,
        "p95_first_partial_ms": lat.p95_first_partial_ms,
        "median_commit_lag_ms": lat.median_commit_lag_ms,
        "p95_commit_lag_ms": lat.p95_commit_lag_ms,
        "stability_ratio": stream.stability_ratio,
        "median_rewrite_words": stream.median_rewrite_words,
        "median_realtime_lag_ms": stream.median_realtime_lag_ms,
        "p95_realtime_lag_ms": stream.p95_realtime_lag_ms,
        "n_utterances_with_partials": stream.n_utterances_with_partials,
    }

    meta = {
        "run_id": run_id,
        "git_sha": _git_sha(),
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": psutil.cpu_count(),
            "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
        },
        "model": {
            "name": model.name, "family": model.family, "env": model.env,
            "adapter_module": model.adapter_module, "extra_args": list(model.extra_args),
            "description": model.description,
        },
        "dataset": {"name": dataset.name, "description": dataset.description},
        "limit": limit,
        "timeout_s": timeout_s,
        "mode": "warm" if warm else "cold",
        "decoding": asdict(decoding),
        "decoding_hash": decoding_hash,
        "adapter_env": {
            "name": model.env,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "nvidia_driver": _nvidia_smi_version(),
            "frozen": _adapter_env_freeze(model.env),
        },
    }

    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    if errors_log:
        (run_dir / "errors.log").write_text("\n\n".join(errors_log))

                                                                  
    scored_rows = [r for r in per_utt_rows if r.get("wer_norm") is not None]
    worst_rows = sorted(scored_rows, key=lambda r: r["wer_norm"], reverse=True)[:10]
    worst_dump = [
        {
            "id": r["id"], "audio": r.get("audio", ""),
            "hypothesis": r["hypothesis"], "reference": r["reference"],
            "wer": r["wer_norm"], "audio_s": r["audio_s"],
        }
        for r in worst_rows
    ]
    (run_dir / "worst.json").write_text(json.dumps(worst_dump, indent=2))

    csv_path = run_dir / "per_utterance.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_utt_rows[0].keys()) if per_utt_rows else [])
        writer.writeheader()
        writer.writerows(per_utt_rows)

    return run_dir
