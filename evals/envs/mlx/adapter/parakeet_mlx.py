
import argparse
import time
from pathlib import Path

from parakeet_mlx import from_pretrained

from adapter._base import audio_duration_s, emit_ready, log, serve


def _transcribe(model, audio: Path) -> dict:
    dur = audio_duration_s(audio)
    kwargs = {"chunk_duration": 120.0, "overlap_duration": 15.0} if dur > 60 else {}
    result = model.transcribe(str(audio), **kwargs)
    segments = []
    if hasattr(result, "sentences") and result.sentences:
        for s in result.sentences:
            words = [
                {"word": w.text, "start": float(w.start), "end": float(w.end), "prob": None}
                for w in getattr(s, "tokens", [])
            ]
            segments.append({
                "t_start": float(s.start), "t_end": float(s.end),
                "text": s.text.strip(), "speaker": None, "words": words,
            })
    return {
        "text": result.text.strip(),
        "segments": segments,
        "audio_duration_s": dur,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--warm-stdin", action="store_true")
    ap.add_argument("--model-id", default="mlx-community/parakeet-tdt-0.6b-v2")
                                                                                              
    ap.add_argument("--beam-size", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--language", default="en")
    ap.add_argument("--vad-aggressiveness", type=int, default=2)
    ap.add_argument("--pace", default="realtime")
    args, _unknown = ap.parse_known_args()

    log(f"loading {args.model_id} via parakeet-mlx")
    t0 = time.perf_counter()
    model = from_pretrained(args.model_id)
    emit_ready(time.perf_counter() - t0)

    serve(args, lambda audio: _transcribe(model, audio))


if __name__ == "__main__":
    main()
