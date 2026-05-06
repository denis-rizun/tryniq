import asyncio
import json

import structlog

from app.config import config
from app.upload.exceptions import UploadDecodeError

logger = structlog.get_logger()


class FfmpegClient:
    @staticmethod
    async def probe_duration(path: str) -> float:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("ffprobe failed", stderr=stderr.decode(errors="replace")[:200])
            raise UploadDecodeError()

        try:
            info = json.loads(stdout)
            return float(info["format"]["duration"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise UploadDecodeError() from exc

    @staticmethod
    async def normalize_to_wav(src_path: str, dst_path: str) -> None:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            src_path,
            "-vn",
            "-ac",
            str(config.upload.NORMALIZED_CHANNELS),
            "-ar",
            str(config.upload.NORMALIZED_SAMPLE_RATE),
            "-acodec",
            "pcm_s16le",
            "-f",
            "wav",
            dst_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("ffmpeg failed", stderr=stderr.decode(errors="replace")[-300:])
            raise UploadDecodeError()


ffmpeg_client = FfmpegClient()
