
import argparse
import os
from pathlib import Path

from pyannote.audio import Pipeline

from adapter._base import log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, type=Path)
    ap.add_argument("--out-rttm", required=True, type=Path)
    ap.add_argument("--model-id", default="pyannote/speaker-diarization-3.1")
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    log(f"loading {args.model_id} (gated; HF_TOKEN={'set' if token else 'unset'})")
    if not token:
        raise SystemExit(
            "HF_TOKEN is unset; pyannote/speaker-diarization-3.1 is a gated model. "
            "Accept the model terms at https://hf.co/pyannote/speaker-diarization-3.1 "
            "and export HF_TOKEN=hf_xxx before running."
        )
    pipeline = Pipeline.from_pretrained(args.model_id, token=token)

    diarization = pipeline(str(args.audio))
    annotation = getattr(diarization, "speaker_diarization", diarization)

    args.out_rttm.parent.mkdir(parents=True, exist_ok=True)
    with args.out_rttm.open("w") as f:
        if hasattr(annotation, "write_rttm"):
            annotation.write_rttm(f)
        else:
            file_id = args.audio.stem
            for segment, _track, label in annotation.itertracks(yield_label=True):
                f.write(
                    f"SPEAKER {file_id} 1 {segment.start:.3f} {segment.duration:.3f} "
                    f"<NA> <NA> {label} <NA> <NA>\n"
                )


if __name__ == "__main__":
    main()
