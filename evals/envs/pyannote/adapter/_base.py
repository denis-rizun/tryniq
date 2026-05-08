"""Shared adapter scaffolding.

Wire contract with the runner:
* Hypothesis JSON is emitted **on its own line**, immediately preceded by the
  sentinel line ``---HYPOTHESIS-JSON---``. This lets adapters interleave any
  amount of stderr/stdout chatter (model download progress, NeMo banners, …)
  without the parent runner mis-parsing.
* In *warm-stdin* mode (``--warm-stdin``) the adapter loads the model once and
  reads audio paths from stdin, one per line. ``STOP`` (or EOF) ends the loop.
  One sentinel + JSON pair is emitted per input line.
"""

import json
import sys
from collections.abc import Callable
from pathlib import Path

HYPOTHESIS_SENTINEL = "---HYPOTHESIS-JSON---"
READY_SENTINEL = "---ADAPTER-READY---"


def emit(hypothesis: dict) -> None:
    sys.stdout.write(HYPOTHESIS_SENTINEL + "\n")
    sys.stdout.write(json.dumps(hypothesis) + "\n")
    sys.stdout.flush()


def emit_ready(load_s: float | None) -> None:
    """Signal end-of-cold-load to the runner.

    Adapters call this exactly once, after their model is loaded but *before*
    the first ``transcribe_one`` call. The runner records ``load_s`` separately
    from per-sample wall time so that RTF reports reflect steady state, not
    cold-start cost. See PLAN.md M4.

    Pass ``None`` when the adapter cannot honestly measure load time
    (e.g. ``parakeet_fluid_audio``, where load happens inside the spawned Swift
    binary on every call). The signal still fires so warm-stdin mode doesn't
    block waiting for a sentinel that would never come; the runner records
    ``cold_load_s=null`` and the report shows it as ``—``.
    """
    payload: dict[str, float | None | str] = {
        "kind": "ready",
        "load_s": float(load_s) if load_s is not None else None,
    }
    sys.stdout.write(READY_SENTINEL + "\n")
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def log(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def audio_duration_s(path: Path) -> float:
    import soundfile as sf
    info = sf.info(str(path))
    return float(info.frames) / float(info.samplerate)


def serve(args, transcribe_one: Callable[[Path], dict]) -> None:
    """Single-shot or warm-stdin loop, depending on ``args.warm_stdin``."""
    if getattr(args, "warm_stdin", False):
        for raw in sys.stdin:
            line = raw.strip()
            if not line or line == "STOP":
                return
            try:
                hyp = transcribe_one(Path(line))
            except Exception as e:  # noqa: BLE001 — surface to runner, never crash the loop
                log(f"warm-loop error on {line}: {e}")
                hyp = {"text": "", "segments": [], "error": f"{type(e).__name__}: {e}"}
            emit(hyp)
    else:
        emit(transcribe_one(args.audio))
