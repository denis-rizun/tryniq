"""faster-whisper / distil-whisper adapter (CTranslate2)."""

import argparse
import time
from pathlib import Path

from faster_whisper import WhisperModel

from adapter._base import audio_duration_s, emit_ready, log, serve


def _transcribe(model: WhisperModel, audio: Path, language: str, beam_size: int) -> dict:
    segments_iter, _info = model.transcribe(
        str(audio),
        language=language,
        beam_size=beam_size,
        word_timestamps=True,
        vad_filter=False,
    )

    segments = []
    full_text_parts: list[str] = []
    for seg in segments_iter:
        words = [
            {"word": w.word, "start": float(w.start or 0), "end": float(w.end or 0),
             "prob": float(w.probability) if w.probability is not None else None}
            for w in (seg.words or [])
        ]
        segments.append({
            "t_start": float(seg.start), "t_end": float(seg.end),
            "text": seg.text.strip(), "speaker": None, "words": words,
        })
        full_text_parts.append(seg.text.strip())

    return {
        "text": " ".join(full_text_parts).strip(),
        "segments": segments,
        "audio_duration_s": audio_duration_s(audio),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--warm-stdin", action="store_true")
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--language", default="en")
    ap.add_argument("--beam-size", type=int, default=5)
    # Decoding-config flags we don't honor — accepted for fairness wrapper compatibility.
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--vad-aggressiveness", type=int, default=2)
    ap.add_argument("--pace", default="realtime")
    args, _unknown = ap.parse_known_args()

    log(f"loading {args.model_id} compute={args.compute_type} device={args.device}")
    t0 = time.perf_counter()
    model = WhisperModel(args.model_id, device=args.device, compute_type=args.compute_type)
    emit_ready(time.perf_counter() - t0)

    serve(args, lambda audio: _transcribe(model, audio, args.language, args.beam_size))


if __name__ == "__main__":
    main()
