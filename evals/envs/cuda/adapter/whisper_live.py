
import argparse
import asyncio
import os
import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

import soundfile as sf

from adapter._base import audio_duration_s, emit_ready, log, serve


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return
            except OSError:
                time.sleep(0.5)
    raise RuntimeError(f"whisper-live server did not open {host}:{port} within {timeout_s}s")


def _spawn_server(port: int, backend: str, model: str) -> subprocess.Popen:
    cmd = [
        sys.executable, "-m", "whisper_live.server",
        "--port", str(port),
        "--backend", backend,
    ]
                                                                            
                                                                        
    env = os.environ.copy()
    env["WHISPER_MODEL"] = model
    log(f"spawning whisper-live server on 127.0.0.1:{port} (backend={backend} model={model})")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)


def _transcribe(audio: Path, host: str, port: int, model: str) -> dict:
                                                                    
    from whisper_live.client import TranscriptionClient                

    duration = audio_duration_s(audio)
    log(f"connecting whisper-live client → {host}:{port} for {audio.name} ({duration:.1f}s)")

                                                                                    
    client = TranscriptionClient(
        host, port,
        lang="en", translate=False,
        model=model, use_vad=False,
        save_output_recording=False,
    )
    t0 = time.perf_counter()
    client(str(audio))                                  
    wall = time.perf_counter() - t0

    segments_raw: list[dict] = list(getattr(client, "transcript", []) or [])
    segments = [
        {
            "t_start": float(s.get("start", 0.0)),
            "t_end": float(s.get("end", 0.0)),
            "text": (s.get("text") or "").strip(),
            "speaker": None,
            "words": [],
        }
        for s in segments_raw
    ]
    text = " ".join(s["text"] for s in segments if s["text"]).strip()

                                                                                   
    partials = []
    if segments:
        per_chunk = wall / max(len(segments), 1) * 1000.0
        for i, s in enumerate(segments, 1):
            partials.append({
                "text": " ".join(seg["text"] for seg in segments[:i]),
                "audio_t_end_s": s["t_end"],
                "wall_offset_ms": i * per_chunk,
                "is_final": i == len(segments),
            })

    return {
        "text": text,
        "segments": segments,
        "partials": partials,
        "audio_duration_s": duration,
        "time_to_first_partial_ms": (
            (wall / max(len(segments), 1)) * 1000.0 if segments else None
        ),
        "partial_to_final_lag_ms": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--warm-stdin", action="store_true")
    ap.add_argument("--backend", default="faster_whisper",
                    help="Server backend: faster_whisper | tensorrt | openvino")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--server-startup-timeout-s", type=float, default=120.0)
                                                                          
    ap.add_argument("--beam-size", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--language", default="en")
    ap.add_argument("--vad-aggressiveness", type=int, default=2)
    ap.add_argument("--pace", default="realtime")
    args, _unknown = ap.parse_known_args()

    port = _free_port()
    t0 = time.perf_counter()
    server = _spawn_server(port, args.backend, args.model)
    try:
        _wait_for_port("127.0.0.1", port, timeout_s=args.server_startup_timeout_s)
        emit_ready(time.perf_counter() - t0)

        def transcribe_one(audio: Path) -> dict:
            return _transcribe(audio, "127.0.0.1", port, args.model)

        serve(args, transcribe_one)
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == "__main__":
    main()
