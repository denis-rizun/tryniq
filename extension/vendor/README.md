# Vendored binaries

## silero_vad.onnx

- Source: https://github.com/snakers4/silero-vad
- Version: v5.1.2 (ONNX export shipped in `src/silero_vad/data/silero_vad.onnx`)
- License: MIT
- Used by: `extension/src/vad.ts` (Silero VAD wrapper) — runs in the isolated-world content
  script via `onnxruntime-web`. Gates per-stream PCM with a 3-window onset / 12-window
  hangover state machine and a 200 ms pre-roll, per Phase 1 spec §3.4–§3.5.

To refresh: `curl -fsSL -o silero_vad.onnx https://github.com/snakers4/silero-vad/raw/v5.1.2/src/silero_vad/data/silero_vad.onnx`
