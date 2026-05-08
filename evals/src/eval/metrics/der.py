"""Diarization error rate via pyannote.metrics. Inputs are RTTM file paths.

We compute DER both with and without overlap regions:
* ``der_with_overlap`` — counts errors inside overlapping speech (the honest number).
* ``der_no_overlap`` — pyannote's ``skip_overlap=True``; comparable to many published
  numbers that hide overlap performance.
"""

from dataclasses import dataclass
from pathlib import Path

from pyannote.core import Annotation, Segment
from pyannote.metrics.diarization import DiarizationErrorRate, JaccardErrorRate


@dataclass
class DerResult:
    der_with_overlap: float
    der_no_overlap: float
    jer: float
    speaker_count_error: int
    duration_s: float
    # M5 — DER decomposition (with-overlap variant). Each is a fraction of
    # ``total`` reference speech: ``der_missed + der_false_alarm + der_confusion``
    # equals ``der_with_overlap`` (within float epsilon).
    der_missed: float
    der_false_alarm: float
    der_confusion: float


def _load_rttm(path: Path) -> Annotation:
    annotation = Annotation()
    with path.open() as f:
        for line in f:
            parts = line.strip().split()
            if not parts or parts[0] != "SPEAKER":
                continue
            onset = float(parts[3])
            dur = float(parts[4])
            speaker = parts[7]
            annotation[Segment(onset, onset + dur)] = speaker
    return annotation


def score(reference_rttm: Path, hypothesis_rttm: Path) -> DerResult:
    ref = _load_rttm(reference_rttm)
    hyp = _load_rttm(hypothesis_rttm)

    der_overlap = DiarizationErrorRate(collar=0.25, skip_overlap=False)
    der_no_overlap = DiarizationErrorRate(collar=0.25, skip_overlap=True)
    jer_metric = JaccardErrorRate(collar=0.25)

    # ``detailed`` returns the components as float seconds (or fractions, depending
    # on pyannote version) plus the aggregate DER. We normalize against the
    # ``total`` field so each component is a fraction of reference speech.
    detailed = der_overlap(ref, hyp, detailed=True)
    total = float(detailed.get("total", 0.0)) or 1.0
    missed = float(detailed.get("missed detection", 0.0)) / total
    false_alarm = float(detailed.get("false alarm", 0.0)) / total
    confusion = float(detailed.get("confusion", 0.0)) / total
    der_overlap_value = float(detailed.get("diarization error rate", missed + false_alarm + confusion))

    return DerResult(
        der_with_overlap=der_overlap_value,
        der_no_overlap=float(der_no_overlap(ref, hyp)),
        jer=float(jer_metric(ref, hyp)),
        speaker_count_error=abs(len(ref.labels()) - len(hyp.labels())),
        duration_s=ref.get_timeline().duration(),
        der_missed=missed,
        der_false_alarm=false_alarm,
        der_confusion=confusion,
    )
