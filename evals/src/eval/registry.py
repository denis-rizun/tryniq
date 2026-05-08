"""Static registry of models and datasets.

Each `Model` entry maps to a subprocess invocation: `cd envs/<family> && uv run python -m <module> ...`.
Adding a new model = adding a row here + a script under `envs/<env>/adapter/`.

The lineup is intentionally narrow — three models per family — so the model card
answers a clear question per slot. Speaker-embedding / verification (ECAPA) is
registered but excluded from the diarization comparison via ``in_comparison=False``;
it doesn't represent the production diarization choice.
"""

from dataclasses import dataclass, field
from typing import Literal

ModelFamily = Literal["final", "live", "diarization"]
EnvName = Literal[
    "faster-whisper",
    "mlx",
    "nemo",
    "moonshine",
    "whispercpp",
    "pyannote",
    "streamer",
    "diarizen",
    "cuda",
]


@dataclass(frozen=True)
class Model:
    name: str
    family: ModelFamily
    env: EnvName
    adapter_module: str  # `adapter.<file>` invoked as `python -m`
    extra_args: tuple[str, ...] = ()
    description: str = ""
    license: str = ""
    release_date: str = ""  # ISO YYYY-MM-DD; "" if unknown
    in_comparison: bool = True  # False = registered but excluded from MODEL_CARD tables


@dataclass(frozen=True)
class Dataset:
    name: str
    multi_speaker: bool = False
    has_diarization_truth: bool = False
    description: str = ""
    license: str = ""


MODELS: list[Model] = [
    # ---------- Final-pass ASR ----------
    Model(
        name="faster_whisper_large_v3_turbo",
        family="final",
        env="faster-whisper",
        adapter_module="adapter.faster_whisper",
        extra_args=("--model-id", "dropbox-dash/faster-whisper-large-v3-turbo", "--compute-type", "int8"),
        description="Backend baseline. CTranslate2 int8, runs on CPU/Metal.",
        license="MIT",
        release_date="2024-10-01",
    ),
    Model(
        name="canary_qwen_2_5b",
        family="final",
        env="cuda",
        adapter_module="adapter.canary_qwen",
        extra_args=("--model-id", "nvidia/canary-qwen-2.5b"),
        description="OpenASR leaderboard top (~5.6% avg WER). NeMo, requires CUDA 12.x + 16 GB VRAM.",
        license="CC-BY-4.0",
        release_date="2025-07-01",
    ),
    # Same model as the Mac default, but on CUDA fp16 — answers "what does our
    # production final-pass look like on a real GPU instead of M4 int8 CPU".
    # Both rows are kept ``in_comparison=True`` so the model card surfaces the
    # M4-vs-CUDA delta directly.
    Model(
        name="faster_whisper_large_v3_turbo_cuda",
        family="final",
        env="cuda",
        adapter_module="adapter.faster_whisper",
        extra_args=(
            "--model-id", "dropbox-dash/faster-whisper-large-v3-turbo",
            "--device", "cuda", "--compute-type", "float16",
        ),
        description="Same backend baseline, CUDA fp16. Honest GPU datapoint vs. the M4 int8 row.",
        license="MIT",
        release_date="2024-10-01",
    ),
    Model(
        name="parakeet_tdt_0_6b_v2_offline",
        family="final",
        env="mlx",
        adapter_module="adapter.parakeet_mlx",
        extra_args=("--model-id", "mlx-community/parakeet-tdt-0.6b-v2"),
        description="Compact reference. NVIDIA Parakeet-TDT-0.6B-v2 via parakeet-mlx (Apple Silicon).",
        license="CC-BY-4.0",
        release_date="2025-06-01",
    ),

    # ---------- Live-pass ASR ----------
    Model(
        name="parakeet_fluid_audio",
        family="live",
        env="streamer",
        adapter_module="adapter.fluid_audio",
        description="Production live model. Parakeet-TDT v2 via the prebuilt Swift `streamer` binary on $PATH.",
        license="CC-BY-4.0",
        release_date="2025-06-01",
    ),
    Model(
        name="moonshine_base",
        family="live",
        env="moonshine",
        adapter_module="adapter.moonshine",
        extra_args=("--model-id", "UsefulSensors/moonshine-base", "--streaming"),
        description="Streaming-native architecture reference. Moonshine base ONNX.",
        license="MIT",
        release_date="2024-10-01",
    ),
    Model(
        name="whisper_live_large_v3",
        family="live",
        env="cuda",
        adapter_module="adapter.whisper_live",
        extra_args=("--backend", "faster_whisper", "--model", "large-v3"),
        description="WhisperLive (large-v3 via faster-whisper) — productionized streaming Whisper. CUDA fp16.",
        license="MIT",
        release_date="2024-04-01",
    ),

    # ---------- Diarization (comparison triple) ----------
    Model(
        name="diarizen",
        family="diarization",
        env="diarizen",
        adapter_module="adapter.diarizen",
        extra_args=("--model-id", "BUTSpeechFIT/diarizen-wavlm-large-s80-md"),
        description="Production model. EEND via DiariZen (BUT Speech).",
        license="MIT",  # DiariZen MIT; weights vary — confirm on HF.
        release_date="2024-12-01",
    ),
    Model(
        name="pyannote_3_1",
        family="diarization",
        env="pyannote",
        adapter_module="adapter.pyannote_diar",
        extra_args=("--model-id", "pyannote/speaker-diarization-3.1"),
        description="Industry baseline. pyannote/speaker-diarization-3.1 (gated).",
        license="MIT (gated)",
        release_date="2023-11-01",
    ),
    Model(
        name="reverb_diarization_v2",
        family="diarization",
        env="pyannote",
        adapter_module="adapter.reverb_diarization",
        description="Modern challenger. Reverb Diarization v2 (Rev). EEND-style.",
        license="CC-BY-NC-4.0",
        release_date="2024-09-01",
    ),

    # ---------- Registered but not in the comparison table ----------
    Model(
        name="ecapa_speechbrain",
        family="diarization",
        env="pyannote",
        adapter_module="adapter.ecapa_speechbrain",
        description="Speaker-embedding building block (PRD §10), not a production diarization baseline.",
        license="Apache-2.0",
        release_date="2020-01-01",
        in_comparison=False,
    ),
]


DATASETS: list[Dataset] = [
    Dataset(
        "librispeech_test_clean",
        description="LibriSpeech test-clean (clean read English).",
        license="CC-BY-4.0",
    ),
    Dataset(
        "librispeech_test_other",
        description="LibriSpeech test-other (harder).",
        license="CC-BY-4.0",
    ),
    Dataset(
        "ami_subset",
        multi_speaker=True,
        has_diarization_truth=True,
        description="AMI Meeting Corpus subset (3 ES2004 meetings).",
        license="CC-BY-4.0",
    ),
    Dataset(
        "earnings21",
        description="Earnings-21 long-form business calls.",
        license="CC-BY-4.0",
    ),
    Dataset(
        "chime6_dev",
        multi_speaker=True,
        has_diarization_truth=True,
        description="CHiME-6 dev — far-field overlapped meeting audio (manual acquisition).",
        license="LDC (custom)",
    ),
]


def get_model(name: str) -> Model:
    for m in MODELS:
        if m.name == name:
            return m
    raise KeyError(f"Unknown model: {name}. Known: {[m.name for m in MODELS]}")


def get_dataset(name: str) -> Dataset:
    for d in DATASETS:
        if d.name == name:
            return d
    raise KeyError(f"Unknown dataset: {name}. Known: {[d.name for d in DATASETS]}")


def models_for_family(family: ModelFamily) -> list[Model]:
    """All models in a family, including those flagged ``in_comparison=False``."""
    return [m for m in MODELS if m.family == family]


def comparison_models_for_family(family: ModelFamily) -> list[Model]:
    """Only the models that should appear in the model-card comparison table."""
    return [m for m in MODELS if m.family == family and m.in_comparison]


def datasets_for_family(family: ModelFamily) -> list[Dataset]:
    if family == "diarization":
        return [d for d in DATASETS if d.has_diarization_truth]
    return list(DATASETS)
