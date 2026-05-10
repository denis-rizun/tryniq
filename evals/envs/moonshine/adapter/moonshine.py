
import argparse
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from moonshine_onnx import MoonshineOnnxModel, load_tokenizer

from adapter._base import audio_duration_s, emit_ready, log, serve

SAMPLE_RATE = 16000
                                                                               
CHUNK_S = 10.0
OVERLAP_S = 1.0


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate:
        return audio
    ratio = dst_rate / src_rate
    new_len = int(round(len(audio) * ratio))
    x_old = np.linspace(0, 1, len(audio), endpoint=False)
    x_new = np.linspace(0, 1, new_len, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def _transcribe(model, tokenizer, audio_path: Path, streaming: bool, pace: str) -> dict:
    audio, sr = sf.read(str(audio_path), dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = _resample(audio, sr, SAMPLE_RATE)

    segments = []
    partials: list[dict] = []
    full_text_parts: list[str] = []
    first_partial_lag_ms: float | None = None

    if streaming:
        step = int((CHUNK_S - OVERLAP_S) * SAMPLE_RATE)
        chunk_n = int(CHUNK_S * SAMPLE_RATE)
        wall_zero = time.perf_counter()
        i = 0
        while i < len(audio):
            slice_ = audio[i:i + chunk_n]
            t_start = i / SAMPLE_RATE
            t_end = min((i + chunk_n) / SAMPLE_RATE, len(audio) / SAMPLE_RATE)
                                                                                     
            if pace == "realtime":
                drift = (wall_zero + t_end) - time.perf_counter()
                if drift > 0:
                    time.sleep(drift)
            tokens = model.generate(slice_[np.newaxis, :].astype(np.float32))
            text = tokenizer.decode_batch(tokens)[0].strip()
            wall_ms = (time.perf_counter() - wall_zero) * 1000.0
            partials.append({
                "text": text,
                "audio_t_end_s": t_end,
                "wall_offset_ms": wall_ms,
                "is_final": False,
            })
            if first_partial_lag_ms is None:
                first_partial_lag_ms = wall_ms - t_end * 1000.0
            segments.append({
                "t_start": t_start, "t_end": t_end, "text": text, "speaker": None, "words": [],
            })
            full_text_parts.append(text)
            i += step
        if partials:
            partials[-1]["is_final"] = True
    else:
        t0 = time.perf_counter()
        tokens = model.generate(audio[np.newaxis, :].astype(np.float32))
        text = tokenizer.decode_batch(tokens)[0].strip()
        log(f"decode_ms={(time.perf_counter() - t0) * 1000:.0f}")
        segments.append({
            "t_start": 0.0, "t_end": len(audio) / SAMPLE_RATE,
            "text": text, "speaker": None, "words": [],
        })
        full_text_parts.append(text)

    return {
        "text": " ".join(full_text_parts).strip(),
        "segments": segments,
        "partials": partials,
        "audio_duration_s": audio_duration_s(audio_path),
        "time_to_first_partial_ms": first_partial_lag_ms,
        "partial_to_final_lag_ms": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--warm-stdin", action="store_true")
    ap.add_argument("--model-id", default="UsefulSensors/moonshine/base")
    ap.add_argument("--streaming", action="store_true", help="Slice into 10s chunks (sim live).")
    ap.add_argument("--pace", choices=("realtime", "fast"), default="realtime",
                    help="In streaming mode, pace chunks at audio-timeline rate or as fast as possible.")
                                                                          
    ap.add_argument("--beam-size", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--language", default="en")
    ap.add_argument("--vad-aggressiveness", type=int, default=2)
    args, _unknown = ap.parse_known_args()

    log(f"loading {args.model_id} streaming={args.streaming} pace={args.pace}")
    t0 = time.perf_counter()
    model = MoonshineOnnxModel(model_name=args.model_id.split("/")[-1])
    tokenizer = load_tokenizer()
    emit_ready(time.perf_counter() - t0)

    serve(args, lambda audio: _transcribe(model, tokenizer, audio, args.streaming, args.pace))


if __name__ == "__main__":
    main()
