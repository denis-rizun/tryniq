from typing import Final

CHUNK_BYTES: Final[int] = 1024 * 1024
ACCEPTED_EXTENSIONS: Final[frozenset[str]] = frozenset({"wav", "mp3", "m4a", "mp4", "webm", "ogg", "flac"})
DEFAULT_SPEAKER_LABEL: Final[str] = "Speaker {idx}"
