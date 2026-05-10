
import argparse
import os
from pathlib import Path

import torch
from pyannote.audio import Pipeline

from adapter._base import log


def _select_device() -> torch.device:
    forced = os.environ.get("PYANNOTE_DEVICE")
    if forced:
        return torch.device(forced)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        return torch.device("mps")
    return torch.device("cpu")


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

    device = _select_device()
    log(f"running on device={device}")
    pipeline.to(device)

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
