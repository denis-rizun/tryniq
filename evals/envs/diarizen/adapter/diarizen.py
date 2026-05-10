
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

                                                                               
    import torch
    _orig_load = torch.load
    def _load_unsafe(*a, **kw):
        kw["weights_only"] = False
        return _orig_load(*a, **kw)
    torch.load = _load_unsafe

    from diarizen.pipelines.inference import DiariZenPipeline

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    log(f"loading {args.model_id} (HF_TOKEN={'set' if token else 'unset'})")
    pipeline = DiariZenPipeline.from_pretrained(args.model_id)

    log(f"running diarization on {args.audio}")
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
