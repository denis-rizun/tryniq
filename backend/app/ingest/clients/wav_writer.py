import struct

from app.ingest.clients.minio import minio_client
from app.ingest.constants import BITS_PER_SAMPLE, BYTES_PER_SAMPLE, CHANNELS, SAMPLE_RATE, WAV_CONTENT_TYPE


class WavWriter:
    def __init__(self, key: str) -> None:
        self.key = key
        self._audio_buffer = bytearray()
        self.closed = False

    def append(self, audio_chunk: bytes) -> None:
        if self.closed:
            return

        self._audio_buffer.extend(audio_chunk)

    def pad_silence_to(self, target_bytes: int) -> None:
        if self.closed:
            return
        gap = target_bytes - len(self._audio_buffer)
        if gap > 0:
            self._audio_buffer.extend(b"\x00" * gap)

    async def close(self) -> int:
        if self.closed:
            return 0

        self.closed = True
        audio_byte_count = len(self._audio_buffer)
        if audio_byte_count == 0:
            return 0

        wav_file = self._build_wav_header(audio_byte_count) + bytes(self._audio_buffer)
        await minio_client.put_object(self.key, wav_file, WAV_CONTENT_TYPE)
        return audio_byte_count

    def abort(self) -> None:
        self.closed = True
        self._audio_buffer = bytearray()

    @property
    def duration_seconds(self) -> float:
        return len(self._audio_buffer) / (BYTES_PER_SAMPLE * SAMPLE_RATE)

    @staticmethod
    def _build_wav_header(audio_byte_count: int) -> bytes:
        byte_rate = SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE
        block_align = CHANNELS * BYTES_PER_SAMPLE
        riff_chunk_size = 36 + audio_byte_count
        return (
            b"RIFF"
            + struct.pack("<I", riff_chunk_size)
            + b"WAVE"
            + b"fmt "
            + struct.pack("<I", 16)
            + struct.pack("<H", 1)
            + struct.pack("<H", CHANNELS)
            + struct.pack("<I", SAMPLE_RATE)
            + struct.pack("<I", byte_rate)
            + struct.pack("<H", block_align)
            + struct.pack("<H", BITS_PER_SAMPLE)
            + b"data"
            + struct.pack("<I", audio_byte_count)
        )
