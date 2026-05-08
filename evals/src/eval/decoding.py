"""Centralised decoding parameters passed from the runner to every adapter.

Standardising these across adapters is what makes comparisons fair. Adapters that
don't honor a particular flag must silently ignore it (we use ``parse_known_args``
so unknown flags don't error). Where a model genuinely cannot honor a value, the
adapter is expected to ``log()`` the deviation so it shows up in the run's
errors.log captured by the runner.

Per-model overrides live in ``Model.extra_args`` in the registry; those are
appended *after* the decoding flags, so the registry can override a default for a
model that needs it (e.g. a different language hint).
"""

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DecodingConfig:
    beam_size: int = 1
    temperature: float = 0.0
    language: str = "en"
    vad_aggressiveness: int = 2  # 0..3, Silero/WebRTC convention
    pace: str = "realtime"  # live-only: "realtime" | "fast"

    def to_cli_args(self) -> list[str]:
        return [
            "--beam-size", str(self.beam_size),
            "--temperature", str(self.temperature),
            "--language", self.language,
            "--vad-aggressiveness", str(self.vad_aggressiveness),
            "--pace", self.pace,
        ]

    def hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:8]


DEFAULT_DECODING = DecodingConfig()
