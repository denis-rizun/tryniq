
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
    if getattr(args, "warm_stdin", False):
        for raw in sys.stdin:
            line = raw.strip()
            if not line or line == "STOP":
                return
            try:
                hyp = transcribe_one(Path(line))
            except Exception as e:                                                          
                log(f"warm-loop error on {line}: {e}")
                hyp = {"text": "", "segments": [], "error": f"{type(e).__name__}: {e}"}
            emit(hyp)
    else:
        emit(transcribe_one(args.audio))
