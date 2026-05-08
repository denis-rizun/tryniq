"""DiariZen (BUTSpeechFIT) — production diarization. Emits an RTTM file.

Mirrors the production install pattern (upload/clients/diarization.py): the package
ships a CLI-ish ``Pipeline`` that loads a HuggingFace model id and runs end-to-end
neural diarization. Output is converted to standard RTTM.
"""

import argparse
import os
from pathlib import Path

from adapter._base import log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, type=Path)
    ap.add_argument("--out-rttm", required=True, type=Path)
    ap.add_argument("--model-id", default="BUTSpeechFIT/diarizen-wavlm-large-s80-md")
    args = ap.parse_args()

    # Imported lazily so adapter --help works even if dependencies are missing.
    from diarizen.pipelines import SpeakerDiarization  # type: ignore

    token = os.environ.get("HF_TOKEN")
    log(f"loading {args.model_id} (HF_TOKEN={'set' if token else 'unset'})")
    pipeline = SpeakerDiarization.from_pretrained(args.model_id, use_auth_token=token)

    log(f"running diarization on {args.audio}")
    diarization = pipeline(str(args.audio))

    args.out_rttm.parent.mkdir(parents=True, exist_ok=True)
    file_id = args.audio.stem
    with args.out_rttm.open("w") as f:
        # ``diarization`` is a pyannote ``Annotation`` (DiariZen reuses pyannote types).
        for segment, _track, label in diarization.itertracks(yield_label=True):
            f.write(
                f"SPEAKER {file_id} 1 {segment.start:.3f} {segment.duration:.3f} "
                f"<NA> <NA> {label} <NA> <NA>\n"
            )


if __name__ == "__main__":
    main()
