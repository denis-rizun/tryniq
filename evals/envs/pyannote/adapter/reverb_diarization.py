"""Reverb Diarization v2 (Rev) — EEND-style diarization. Emits an RTTM file.

License note: the Reverb v2 weights are CC-BY-NC-4.0 — surfaced in MODEL_CARD.md.
The package import path varies by Rev's release; we try the documented entry first
and fall back to the older one. If both fail, the adapter emits a clear error so
the runner records a graceful skip.
"""

import argparse
import os
from pathlib import Path

from adapter._base import log


def _load_pipeline():
    token = os.environ.get("HF_TOKEN")
    try:
        from reverb_diarize import ReverbDiarize  # type: ignore
        log("loaded reverb_diarize.ReverbDiarize")
        return ReverbDiarize.from_pretrained(use_auth_token=token)
    except Exception as e:  # noqa: BLE001
        log(f"reverb_diarize import path failed ({e}); trying pyannote-pretrained fallback")

    # Fallback: Rev publishes the model on HF as ``Revai/reverb-diarization-v2``
    # and it loads through pyannote's Pipeline if the user has accepted the gate.
    from pyannote.audio import Pipeline  # type: ignore
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
