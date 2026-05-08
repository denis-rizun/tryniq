
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

    token = os.environ.get("HF_TOKEN")
    log(f"loading {args.model_id} (gated; HF_TOKEN={'set' if token else 'unset'})")
    pipeline = Pipeline.from_pretrained(args.model_id, use_auth_token=token)

    diarization = pipeline(str(args.audio))
    args.out_rttm.parent.mkdir(parents=True, exist_ok=True)
    with args.out_rttm.open("w") as f:
        diarization.write_rttm(f)


if __name__ == "__main__":
    main()
