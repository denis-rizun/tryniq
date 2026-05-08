
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from pyannote.audio import Model, Pipeline
from sklearn.cluster import AgglomerativeClustering
from speechbrain.inference.speaker import EncoderClassifier

from adapter._base import log

SAMPLE_RATE = 16000
EMBED_WINDOW_S = 1.5
EMBED_HOP_S = 0.75


def _load_vad() -> Pipeline:
                                                                                            
    try:
        return Pipeline.from_pretrained("pyannote/voice-activity-detection")
    except Exception as e:
        log(f"VAD load failed ({e}); will treat full audio as voiced")
        return None                              


def _voiced_segments(vad: Pipeline | None, audio_path: Path, total_dur: float) -> list[tuple[float, float]]:
    if vad is None:
        return [(0.0, total_dur)]
    out = vad(str(audio_path))
    return [(seg.start, seg.end) for seg in out.get_timeline().support()]


def _embed(classifier: EncoderClassifier, samples: np.ndarray) -> np.ndarray:
    tensor = torch.from_numpy(samples).unsqueeze(0).float()
    with torch.no_grad():
        emb = classifier.encode_batch(tensor)
    return emb.squeeze().cpu().numpy()


def _cluster(embeddings: np.ndarray, distance_threshold: float) -> np.ndarray:
    if len(embeddings) <= 1:
        return np.zeros(len(embeddings), dtype=int)
    clustering = AgglomerativeClustering(
        n_clusters=None, metric="cosine", linkage="average",
        distance_threshold=distance_threshold,
    )
    return clustering.fit_predict(embeddings)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, type=Path)
    ap.add_argument("--out-rttm", required=True, type=Path)
    ap.add_argument("--threshold", type=float, default=0.45,
                    help="Cosine distance threshold for cluster merge.")
    args = ap.parse_args()

    log("loading SpeechBrain ECAPA-TDNN")
    classifier = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir="/tmp/spkrec-ecapa-voxceleb",
        run_opts={"device": "cpu"},
    )

    audio, sr = sf.read(str(args.audio), dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE:
        ratio = SAMPLE_RATE / sr
        new_len = int(round(len(audio) * ratio))
        x_old = np.linspace(0, 1, len(audio), endpoint=False)
        x_new = np.linspace(0, 1, new_len, endpoint=False)
        audio = np.interp(x_new, x_old, audio).astype(np.float32)
    total_dur = len(audio) / SAMPLE_RATE

    log("running VAD")
    vad = _load_vad()
    voiced = _voiced_segments(vad, args.audio, total_dur)

    win = int(EMBED_WINDOW_S * SAMPLE_RATE)
    hop = int(EMBED_HOP_S * SAMPLE_RATE)

    windows: list[tuple[float, float]] = []
    embeddings: list[np.ndarray] = []
    for v_start, v_end in voiced:
        i_start = int(v_start * SAMPLE_RATE)
        i_end = int(v_end * SAMPLE_RATE)
        i = i_start
        while i + win <= i_end:
            samples = audio[i:i + win]
            embeddings.append(_embed(classifier, samples))
            windows.append((i / SAMPLE_RATE, (i + win) / SAMPLE_RATE))
            i += hop

    if not embeddings:
        log("no embeddable windows; writing empty RTTM")
        args.out_rttm.parent.mkdir(parents=True, exist_ok=True)
        args.out_rttm.write_text("")
        return

    log(f"clustering {len(embeddings)} embeddings (threshold={args.threshold})")
    labels = _cluster(np.stack(embeddings), args.threshold)

                                           
    merged: list[tuple[float, float, int]] = []
    for (start, end), label in zip(windows, labels, strict=True):
        if merged and merged[-1][2] == label and start <= merged[-1][1] + 0.05:
            merged[-1] = (merged[-1][0], end, label)
        else:
            merged.append((start, end, int(label)))

    args.out_rttm.parent.mkdir(parents=True, exist_ok=True)
    file_id = args.audio.stem
    with args.out_rttm.open("w") as f:
        for start, end, label in merged:
            f.write(
                f"SPEAKER {file_id} 1 {start:.3f} {end - start:.3f} <NA> <NA> SPK{label:02d} <NA> <NA>\n"
            )


if __name__ == "__main__":
    main()
