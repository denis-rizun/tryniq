
import argparse
import time
from pathlib import Path

from adapter._base import audio_duration_s, emit_ready, log, serve


def _load_model(model_id: str):
                                                         
    from nemo.collections.asr.models import EncDecMultiTaskModel                
    log(f"loading {model_id} (NeMo, CUDA)")
    model = EncDecMultiTaskModel.from_pretrained(model_id)
    decode_cfg = model.cfg.decoding
    decode_cfg.beam.beam_size = 1
    model.change_decoding_strategy(decode_cfg)
    return model


def _transcribe(model, audio: Path, source_lang: str, target_lang: str) -> dict:
    transcripts = model.transcribe(
        audio=[str(audio)],
        batch_size=1,
        source_lang=source_lang,
        target_lang=target_lang,
        task="asr",
        timestamps=True,
    )
    text = transcripts[0].text if hasattr(transcripts[0], "text") else str(transcripts[0])
    segments = []
    if hasattr(transcripts[0], "timestamp"):
        for seg in transcripts[0].timestamp.get("segment", []) or []:
            segments.append({
                "t_start": float(seg["start"]), "t_end": float(seg["end"]),
                "text": seg["segment"], "speaker": None, "words": [],
            })

    return {
        "text": text.strip(),
        "segments": segments,
        "audio_duration_s": audio_duration_s(audio),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--warm-stdin", action="store_true")
    ap.add_argument("--model-id", default="nvidia/canary-qwen-2.5b")
    ap.add_argument("--source-lang", default="en")
    ap.add_argument("--target-lang", default="en")
                                                                          
    ap.add_argument("--beam-size", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--language", default="en")
    ap.add_argument("--vad-aggressiveness", type=int, default=2)
    ap.add_argument("--pace", default="realtime")
    args, _unknown = ap.parse_known_args()

    t0 = time.perf_counter()
    model = _load_model(args.model_id)
    emit_ready(time.perf_counter() - t0)
    serve(args, lambda audio: _transcribe(model, audio, args.source_lang, args.target_lang))


if __name__ == "__main__":
    main()
