
import argparse
import asyncio
import os
import shutil
import struct
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf
import websockets
from websockets.asyncio.server import ServerConnection, serve as ws_serve

from adapter._base import audio_duration_s, emit_ready, log, serve as adapter_serve

                                                                                  
AUDIO_FRAME_HEADER_FMT = "<II"
AUDIO_FRAME_HEADER_LEN = struct.calcsize(AUDIO_FRAME_HEADER_FMT)
SAMPLE_RATE = 16000
FRAME_SAMPLES = 320                                                     
EVENT_HELLO = "hello"
EVENT_STREAM_OPEN = "stream_open"
EVENT_STREAM_CLOSE = "stream_close"
EVENT_PARTIAL = "partial"
EVENT_FINAL = "final"
EVENT_PING = "ping"

STREAMER_BIN_ENV = "TRYNIQ_STREAMER_BIN"                                            


@dataclass
class _Capture:
    partials: list[dict] = field(default_factory=list)
    finals: list[dict] = field(default_factory=list)
    audio_send_started_at: float | None = None
    first_partial_at: float | None = None
    first_final_at: float | None = None
    final_audio_t_end: float = 0.0


def _resample_int16(audio_path: Path) -> np.ndarray:
    audio, sr = sf.read(str(audio_path), dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE:
        ratio = SAMPLE_RATE / sr
        new_len = int(round(len(audio) * ratio))
        x_old = np.linspace(0, 1, len(audio), endpoint=False)
        x_new = np.linspace(0, 1, new_len, endpoint=False)
        audio = np.interp(x_new, x_old, audio).astype(np.float32)
    pcm = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    return pcm


def _resolve_binary() -> str:
    override = os.environ.get(STREAMER_BIN_ENV)
    if override:
        if not Path(override).is_file():
            raise RuntimeError(f"{STREAMER_BIN_ENV}={override} is not a file")
        return override
    found = shutil.which("streamer")
    if not found:
        raise RuntimeError(
            "streamer binary not found on $PATH. "
            f"Set {STREAMER_BIN_ENV}=/path/to/streamer or add it to PATH. "
            "Build with: cd streamer && swift build -c release && "
            "ln -s $(pwd)/.build/release/streamer /usr/local/bin/streamer"
        )
    return found


async def _drive_session(
    ws: ServerConnection,
    pcm: np.ndarray,
    cap: _Capture,
    pace: str,
    settle_s: float,
) -> None:
    stream_id = uuid.uuid4()
    meeting_id = uuid.uuid4()
    stream_idx = 0
    seq = 0

                                             
    hello_seen = False
    async for msg in ws:
        if isinstance(msg, str):
            try:
                import json as _json
                env = _json.loads(msg)
            except Exception:
                continue
            if env.get("kind") == EVENT_HELLO:
                hello_seen = True
                break
    if not hello_seen:
        return

                               
    await ws.send(_json_dump({
        "kind": EVENT_STREAM_OPEN,
        "meeting_id": str(meeting_id),
        "stream_id": str(stream_id),
        "stream_idx": stream_idx,
        "participant_id": None,
        "speaker": {"display_name": "eval", "is_local_user": False},
        "sample_rate": SAMPLE_RATE,
        "encoding": "pcm_s16le",
    }))

                                                                                   
    cap.final_audio_t_end = len(pcm) / SAMPLE_RATE

    async def producer() -> None:
        nonlocal seq
        cap.audio_send_started_at = time.perf_counter()
        frame_period_s = FRAME_SAMPLES / SAMPLE_RATE
        next_send = cap.audio_send_started_at
        for start in range(0, len(pcm), FRAME_SAMPLES):
            chunk = pcm[start:start + FRAME_SAMPLES]
            if len(chunk) < FRAME_SAMPLES:
                pad = np.zeros(FRAME_SAMPLES - len(chunk), dtype=np.int16)
                chunk = np.concatenate([chunk, pad])
            header = struct.pack(AUDIO_FRAME_HEADER_FMT, stream_idx, seq)
            seq += 1
            try:
                await ws.send(header + chunk.tobytes())
            except websockets.ConnectionClosed:
                return
            if pace == "realtime":
                next_send += frame_period_s
                drift = next_send - time.perf_counter()
                if drift > 0:
                    await asyncio.sleep(drift)
                                                                                 
        try:
            await ws.send(_json_dump({"kind": EVENT_STREAM_CLOSE, "stream_id": str(stream_id)}))
        except websockets.ConnectionClosed:
            return

    async def consumer() -> None:
        try:
            async for msg in ws:
                if not isinstance(msg, str):
                    continue
                try:
                    import json as _json
                    env = _json.loads(msg)
                except Exception:
                    continue
                kind = env.get("kind")
                now = time.perf_counter()
                if cap.audio_send_started_at is not None:
                    wall_offset_ms = (now - cap.audio_send_started_at) * 1000.0
                else:
                    wall_offset_ms = 0.0
                if kind == EVENT_PARTIAL:
                    if cap.first_partial_at is None:
                        cap.first_partial_at = now
                    env["_wall_offset_ms"] = wall_offset_ms
                    cap.partials.append(env)
                elif kind == EVENT_FINAL:
                    if cap.first_final_at is None:
                        cap.first_final_at = now
                    env["_wall_offset_ms"] = wall_offset_ms
                    cap.finals.append(env)
        except websockets.ConnectionClosed:
            pass

    prod_task = asyncio.create_task(producer())
    cons_task = asyncio.create_task(consumer())
    await prod_task
                                                                    
    try:
        await asyncio.wait_for(cons_task, timeout=settle_s)
    except asyncio.TimeoutError:
        cons_task.cancel()


def _json_dump(obj: dict) -> str:
    import json as _json
    return _json.dumps(obj)


def _build_hypothesis(audio_path: Path, cap: _Capture) -> dict:
    finals = sorted(cap.finals, key=lambda f: f.get("t_start", 0.0))
    segments = [
        {
            "t_start": float(f.get("t_start", 0.0)),
            "t_end": float(f.get("t_end", 0.0)),
            "text": (f.get("text") or "").strip(),
            "speaker": None,
            "words": [],
        }
        for f in finals
    ]
    text = " ".join(s["text"] for s in segments if s["text"])

    last_final_offset = max(
        (float(f.get("_wall_offset_ms", 0.0)) for f in cap.finals),
        default=-1.0,
    )
    tail_partial = ""
    for p in reversed(cap.partials):
        if float(p.get("_wall_offset_ms", 0.0)) > last_final_offset:
            tail_partial = (p.get("text") or "").strip()
            break
    if tail_partial:
        text = (text + " " + tail_partial).strip() if text else tail_partial

                                                                            
    partials_trace: list[dict] = []
    last_audio_t_end = 0.0
    combined = sorted(
        list(cap.partials) + list(cap.finals),
        key=lambda e: float(e.get("_wall_offset_ms", 0.0)),
    )
    for env in combined:
        is_final = env.get("kind") == EVENT_FINAL
        t_end = env.get("t_end")
        if t_end is None:
                                                                                                
            t_end = float(env.get("_wall_offset_ms", 0.0)) / 1000.0
        last_audio_t_end = max(last_audio_t_end, float(t_end))
        partials_trace.append({
            "text": (env.get("text") or "").strip(),
            "audio_t_end_s": last_audio_t_end,
            "wall_offset_ms": float(env.get("_wall_offset_ms", 0.0)),
            "is_final": is_final,
        })

    ttfp_ms: float | None = None
    if cap.audio_send_started_at is not None and cap.first_partial_at is not None:
        ttfp_ms = (cap.first_partial_at - cap.audio_send_started_at) * 1000.0

    pf_lag_ms: float | None = None
    if cap.first_partial_at is not None and cap.first_final_at is not None:
        pf_lag_ms = (cap.first_final_at - cap.first_partial_at) * 1000.0

    return {
        "text": text.strip(),
        "segments": segments,
        "partials": partials_trace,
        "audio_duration_s": audio_duration_s(audio_path),
        "time_to_first_partial_ms": ttfp_ms,
        "partial_to_final_lag_ms": pf_lag_ms,
    }


async def _transcribe_async(
    binary: str,
    audio_path: Path,
    pace: str,
    settle_s: float,
    handshake_timeout_s: float,
) -> dict:
    pcm = _resample_int16(audio_path)
    cap = _Capture()
    served: asyncio.Event = asyncio.Event()

    async def handler(ws: ServerConnection) -> None:
        await _drive_session(ws, pcm, cap, pace, settle_s)
        served.set()

    server = await ws_serve(handler, "127.0.0.1", 0)
    sock = next(iter(server.sockets))
    port = sock.getsockname()[1]
    log(f"stub /asr/sessions listening on 127.0.0.1:{port}")

    env = os.environ.copy()
    env["BACKEND_WS_URL"] = f"ws://127.0.0.1:{port}"
    env.setdefault("WORKER_TOKEN", "eval-token")
                                                  
    env.setdefault("ASR_CHUNK_S", "2.0")
    env.setdefault("ASR_RIGHT_CTX_S", "1.0")
    env.setdefault("ASR_LEFT_CTX_S", "5.0")
    env.setdefault("ASR_MIN_CONFIRM_S", "4.0")

    proc = await asyncio.create_subprocess_exec(
        binary,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    log(f"spawned streamer pid={proc.pid}")

    try:
        try:
            await asyncio.wait_for(served.wait(), timeout=handshake_timeout_s)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"streamer did not complete handshake within {handshake_timeout_s}s"
            )
    finally:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        server.close()
        await server.wait_closed()

    return _build_hypothesis(audio_path, cap)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--warm-stdin", action="store_true")
    ap.add_argument("--pace", choices=("realtime", "fast"), default="realtime")
    ap.add_argument("--settle-s", type=float, default=10.0,
                    help="Seconds to wait after audio ends for trailing finals.")
    ap.add_argument("--handshake-timeout-s", type=float, default=300.0,
                    help="Max wall-time for the full session (audio + settle).")
                                                                                     
    ap.add_argument("--beam-size", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--language", default="en")
    ap.add_argument("--vad-aggressiveness", type=int, default=2)
    args, _unknown = ap.parse_known_args()

    try:
        binary = _resolve_binary()
    except RuntimeError as e:
        log(str(e))
        sys.exit(2)

    log(f"using streamer binary: {binary}")
                                                                                    
                                                                                  
    emit_ready(None)

    def transcribe_one(audio: Path) -> dict:
        return asyncio.run(_transcribe_async(
            binary, audio, args.pace, args.settle_s, args.handshake_timeout_s,
        ))

    adapter_serve(args, transcribe_one)


if __name__ == "__main__":
    main()
