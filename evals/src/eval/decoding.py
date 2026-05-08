
import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DecodingConfig:
    beam_size: int = 1
    temperature: float = 0.0
    language: str = "en"
    vad_aggressiveness: int = 2                                  
    pace: str = "realtime"                                  

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
