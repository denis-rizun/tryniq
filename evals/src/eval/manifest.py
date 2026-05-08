"""Read/write the per-dataset manifest.jsonl format consumed by the runner."""

import json
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, Field

# STM format: <filename> <channel> <speaker> <begin> <end> [<label>] <text>
# Lines starting with `;;` are comments. Some toolchains emit a 6-column form
# (no <label>); both AMI's pseudo-STM and the canonical Sclite STM are supported.
_STM_IGNORE_TOKENS = {"ignore_time_segment_in_scoring", "<no-speech>", "(()", "()"}


def parse_stm(path: Path) -> str:
    """Extract the concatenated text column from an STM file."""
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(";;"):
            continue
        parts = line.split(maxsplit=6)
        if len(parts) >= 7:
            text = parts[6]
        elif len(parts) == 6:
            text = parts[5]
        else:
            continue
        text = text.strip()
        if not text or text.lower() in _STM_IGNORE_TOKENS:
            continue
        out.append(text)
    return " ".join(out)


def read_reference(text_field: str) -> str:
    """Resolve a manifest `text` field into the actual reference string.

    The field is either inline text or a path to .stm/.txt holding the reference.
    """
    p = Path(text_field)
    if p.exists() and p.is_file():
        if p.suffix == ".stm":
            return parse_stm(p)
        if p.suffix == ".txt":
            return p.read_text(encoding="utf-8").strip()
    return text_field


class Sample(BaseModel):
    id: str
    audio: str
    text: str  # ground-truth transcript OR path to a .stm/.txt file (for long-form)
    speakers: str | None = None  # path to RTTM ground truth (for diarization datasets)
    duration_s: float | None = None
    extras: dict[str, object] = Field(default_factory=dict)


def write_manifest(path: Path, samples: list[Sample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(s.model_dump_json() + "\n")


def read_manifest(path: Path) -> Iterator[Sample]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield Sample.model_validate_json(line)
