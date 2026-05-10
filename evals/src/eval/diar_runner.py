
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

from eval.manifest import read_manifest
from eval.metrics import der as der_metric
from eval.metrics.memory import MemorySampler
from eval.paths import ENVS_ROOT, RESULTS_ROOT, dataset_cache
from eval.registry import Dataset, Model


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


def run(model: Model, dataset: Dataset, *, limit: int | None = None, timeout_s: float = 1800.0) -> Path:
    if not dataset.has_diarization_truth:
        raise ValueError(f"Dataset {dataset.name} has no diarization ground truth.")

    manifest_path = dataset_cache(dataset.name) / "manifest.jsonl"
    samples = [s for s in read_manifest(manifest_path) if s.speakers]
    if limit:
        samples = samples[:limit]

    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{model.name}-{dataset.name}"
    run_dir = RESULTS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    der_overlap_total = 0.0
    der_no_overlap_total = 0.0
    jer_total = 0.0
    missed_total = 0.0
    false_alarm_total = 0.0
    confusion_total = 0.0
    duration_total = 0.0
    wall_total = 0.0
    speaker_count_errors: list[int] = []
    peak_rss_max = 0.0
    failed = 0

    for sample in samples:
        out_rttm = run_dir / f"{sample.id}.hyp.rttm"
        env_dir = ENVS_ROOT / model.env
        cmd = [
            "uv", "run", "python", "-m", model.adapter_module,
            "--audio", sample.audio,
            "--out-rttm", str(out_rttm),
            *model.extra_args,
        ]

        proc = subprocess.Popen(cmd, cwd=env_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        sampler = MemorySampler(pid=proc.pid)
        sampler.start()
        t0 = time.perf_counter()
        try:
            proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            sampler.stop()
            failed += 1
            continue
        wall = time.perf_counter() - t0
        peak = sampler.stop()
        peak_rss_max = max(peak_rss_max, peak)

        if proc.returncode != 0 or not out_rttm.exists():
            failed += 1
            continue

        try:
            d = der_metric.score(Path(sample.speakers), out_rttm)
        except Exception:
            failed += 1
            continue

        der_overlap_total += d.der_with_overlap * d.duration_s
        der_no_overlap_total += d.der_no_overlap * d.duration_s
        missed_total += d.der_missed * d.duration_s
        false_alarm_total += d.der_false_alarm * d.duration_s
        confusion_total += d.der_confusion * d.duration_s
        jer_total += d.jer * d.duration_s
        duration_total += d.duration_s
        wall_total += wall
        speaker_count_errors.append(d.speaker_count_error)

    summary = {
        "run_id": run_id,
        "model": model.name,
        "dataset": dataset.name,
        "n_meetings": len(samples),
        "n_failed": failed,
        "der": (der_overlap_total / duration_total) if duration_total > 0 else None,
        "der_with_overlap": (der_overlap_total / duration_total) if duration_total > 0 else None,
        "der_no_overlap": (der_no_overlap_total / duration_total) if duration_total > 0 else None,
                                                                                 
        "der_missed": (missed_total / duration_total) if duration_total > 0 else None,
        "der_false_alarm": (false_alarm_total / duration_total) if duration_total > 0 else None,
        "der_confusion": (confusion_total / duration_total) if duration_total > 0 else None,
        "jer": (jer_total / duration_total) if duration_total > 0 else None,
        "peak_rss_mb": peak_rss_max,
        "total_duration_s": duration_total,
        "wall_seconds_total": wall_total,
        "rtf": (wall_total / duration_total) if duration_total > 0 else None,
        "xrt": (duration_total / wall_total) if wall_total > 0 else None,
        "speaker_count_error_mean": (
            sum(speaker_count_errors) / len(speaker_count_errors)
            if speaker_count_errors else None
        ),
        "speaker_count_error_max": (
            max(speaker_count_errors) if speaker_count_errors else None
        ),
    }
    meta = {
        "run_id": run_id, "git_sha": _git_sha(),
        "host": {"platform": platform.platform(), "machine": platform.machine(),
                 "cpu_count": psutil.cpu_count(),
                 "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1)},
        "model": {"name": model.name, "family": model.family, "env": model.env,
                  "adapter_module": model.adapter_module, "extra_args": list(model.extra_args)},
        "dataset": {"name": dataset.name},
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

    return run_dir
