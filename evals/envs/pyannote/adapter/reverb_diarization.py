
import argparse
import os
from pathlib import Path

from adapter._base import log


def _load_pipeline():
    token = os.environ.get("HF_TOKEN")
    try:
        from reverb_diarize import ReverbDiarize                
        log("loaded reverb_diarize.ReverbDiarize")
        return ReverbDiarize.from_pretrained(use_auth_token=token)
    except Exception as e:                
        log(f"reverb_diarize import path failed ({e}); trying pyannote-pretrained fallback")

                                                                                
    from pyannote.audio import Pipeline                
    return Pipeline.from_pretrained("Revai/reverb-diarization-v2", use_auth_token=token)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, type=Path)
    ap.add_argument("--out-rttm", required=True, type=Path)
    args = ap.parse_args()

    pipeline = _load_pipeline()
    log(f"running Reverb v2 diarization on {args.audio}")
    diarization = pipeline(str(args.audio))

    args.out_rttm.parent.mkdir(parents=True, exist_ok=True)
    file_id = args.audio.stem
    with args.out_rttm.open("w") as f:
        for segment, _track, label in diarization.itertracks(yield_label=True):
            f.write(
                f"SPEAKER {file_id} 1 {segment.start:.3f} {segment.duration:.3f} "
                f"<NA> <NA> {label} <NA> <NA>\n"
            )


if __name__ == "__main__":
    main()
