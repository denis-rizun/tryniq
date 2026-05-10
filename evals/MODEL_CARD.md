# Model Card — Open Voice Notetaker challenge submission

> Submission for the internal challenge to build an open-source replacement for tl;dv. Demo day: **2026-05-11**. Benchmark hosts: **MacBook M4, 16 GB unified** (Mac-native models) + **Ryzen 5 3600X with RTX 3060 Ti, 16 GB VRAM** running **CUDA 12.x in Docker on Windows / WSL2** (CUDA-only models).

This card is partly auto-generated. Narrative answers are written by hand; the comparison tables at the bottom are regenerated from `results/` by `uv run eval report`.

---

## 1. Which models did we use?

Three slots per family, picked to answer one question each: *what's the production pick*, *what's the strongest open alternative*, *what's a meaningfully different reference point*.

### Final-pass ASR (post-meeting refine)

| Slot               | Model                                | Size   | License   | Released | Runtime                             |
|--------------------|--------------------------------------|--------|-----------|----------|-------------------------------------|
| Mac default        | `faster_whisper_large_v3_turbo`      | ~809 M | MIT       | 2024-10  | CTranslate2 int8, M4 CPU/Metal      |
| Same model on CUDA | `faster_whisper_large_v3_turbo_cuda` | ~809 M | MIT       | 2024-10  | CTranslate2 fp16, RTX 3060 Ti       |
| CUDA accuracy      | `canary_qwen_2_5b`                   | 2.5 B  | CC-BY-4.0 | 2025-07  | NeMo, RTX 3060 Ti fp16 (~5 GB VRAM) |
| Compact reference  | `parakeet_tdt_0_6b_v2_offline`       | 600 M  | CC-BY-4.0 | 2025-06  | parakeet-mlx (Apple Silicon)        |

The two `faster_whisper_large_v3_turbo*` rows share weights but run on different hardware/precision. They answer "what does the same model do at int8 on M4 vs. fp16 on a real GPU?" — useful for the model card's hybrid recommendation.

### Live-pass ASR (per-speaker streaming)

| Slot                       | Model                                                         | Size   | License   | Released | Runtime                  |
|----------------------------|---------------------------------------------------------------|--------|-----------|----------|--------------------------|
| Production                 | `parakeet_fluid_audio` (Parakeet-TDT v2 via `fluid_audio`)    | 600 M  | CC-BY-4.0 | 2025-06  | Swift + CoreML/ANE on M4 |
| Streaming-native reference | `moonshine_base`                                              | ~60 M  | MIT       | 2024-10  | onnxruntime CPU          |
| CUDA reference             | `whisper_live_large_v3` (WhisperLive, faster-whisper backend) | ~809 M | MIT       | 2024-04  | RTX 3060 Ti fp16         |

### Diarization

| Slot              | Model                                 | License            | Released | Runtime              |
|-------------------|---------------------------------------|--------------------|----------|----------------------|
| Production        | `diarizen` (BUT-FIT, EEND-style)      | MIT (weights vary) | 2024-12  | torch CUDA preferred |
| Industry baseline | `pyannote_3_1`                        | MIT (gated)        | 2023-11  | torch CPU/CUDA       |

## 2. Why these models?

- **Per-speaker WebRTC capture lets us pick streaming ASR by latency, not by diarization quality.** Each track is already isolated, so we benchmark live ASR purely on per-stream WER and time-to-first-partial. Models like Moonshine that would be unusable in a mixed-stream setup are fair game here.
- **Final pass is allowed to be slow.** It runs as a TaskIQ job after the meeting. The Mac picks `faster-whisper large-v3-turbo` because it's already shipping in `backend/`; the CUDA host runs `canary_qwen_2_5b` because it's currently top of the OpenASR leaderboard at ~5.6% avg WER and fits comfortably in 16 GB VRAM at fp16.
- **Diarization is a backstop for the post-MVP "uploaded recording" path, not the live path.** The architecture commits to per-speaker capture; diarization is benchmarked honestly because the challenge rubric weighs it (20 pt) and we want a credible answer when audio arrives without per-speaker tracks.
- **NVIDIA constraint, kept tight.** Any NVIDIA model in this lineup installs via the **NeMo toolkit pip path** (`nemo-toolkit[all]` + `libsndfile1` + `ffmpeg`). No Riva, no NIM, no NGC API keys, no Triton. Canary-Qwen-2.5B is the only NVIDIA-authored entry and it meets that constraint.
- **Everything is open-source and self-hostable.** No commercial ASR APIs in the loop.

## 3. Hardware required?

**Local-first, two hosts, deliberately split by what each runs natively.**

| Host                                                        |   | Role                          | What runs natively                                                                                                                                                      |
|-------------------------------------------------------------|:--|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| MacBook M4, 16 GB unified                                   |   | Mac-native runtime            | `faster_whisper_large_v3_turbo`, `parakeet_tdt_0_6b_v2_offline`, `parakeet_fluid_audio` (Swift + ANE), `moonshine_base`, `pyannote_3_1`, `diarizen` (slow) |
| Ryzen 5 3600X + RTX 3060 Ti 16 GB (Linux or Windows + WSL2) |   | CUDA 12.x runtime, **Docker** | `canary_qwen_2_5b`, `whisper_live_large_v3`, `diarizen`, `pyannote_3_1` (when GPU is free)                                                     |

Memory budget per family:
- **Live path** at runtime: per-speaker stream → 16 kHz mono int16 → Swift `streamer/` process. Parakeet-TDT v2 via FluidAudio uses CoreML on the Mac's ANE. Memory: <2 GB resident per streamer worker.
- **Final path**: TaskIQ worker on Mac loads `faster-whisper large-v3-turbo` (~3 GB int8) lazily. The CUDA candidate (`canary_qwen_2_5b`) fits in ~5 GB VRAM at fp16.
- **Diarization**: DiariZen fits in ~3–5 GB VRAM; `pyannote_3_1` runs on CPU at ~1 GB.

**Self-host implication:** a Mac mini M4 + a single Linux/Windows box with a 16 GB-class GPU covers the whole stack for our team-scale demo. For production we'd front the api with a small Linux server, keep the Swift streamer on Mac for ANE access, and run the post-meeting + diarization workers wherever there's a GPU.

## 4. Local, cloud, or hybrid?

**Local-first, optional cloud for the LLM only.**

| Component                   | Where it runs                                    | Notes                                 |
|-----------------------------|--------------------------------------------------|---------------------------------------|
| Browser extension (capture) | User's machine                                   | Chrome MV3, no server-side dependency |
| `api` (FastAPI)             | Self-host (Linux container)                      | Stateless ingest + REST               |
| `worker` (TaskIQ)           | Self-host (Linux container, Docker)              | CPU/GPU-bound final ASR + diarization |
| `streamer` (Swift)          | Apple Silicon Mac                                | CoreML/ANE-bound; not containerizable |
| Postgres / Redis / MinIO    | Self-host containers                             | Vanilla compose stack                 |
| Graph LLM (Phase 3+)        | Configurable: Anthropic Haiku **or** Ollama/vLLM | Default cloud, switchable to local    |

No model weights are sent off-machine. Audio never leaves the self-host stack.

## 5. What worked well?

> Filled in after the bake-off completes. Auto-injected hooks below.

<!-- WORKED_WELL_START -->
- _(populated by `uv run eval report` from `results/`)_
<!-- WORKED_WELL_END -->

## 6. What didn't work?

> Filled in after the bake-off completes. Honest list of failures, blockers, and known regressions.

<!-- DID_NOT_WORK_START -->
- _(populated by `uv run eval report` from `results/`)_
<!-- DID_NOT_WORK_END -->

## 7. Should we build v2 on this stack?

> Filled in after the bake-off. Recommendation will cite the result tables below directly.

<!-- RECOMMENDATION_START -->
- _(populated by `uv run eval report` from `results/`)_
<!-- RECOMMENDATION_END -->

---

## Comparison tables (auto-generated)

These tables are regenerated by `uv run eval report` from `results/<run_id>/summary.json`. Do not edit by hand between the markers. WER cells show the normalized WER with a 95% bootstrap CI. Peak RSS is deliberately omitted from cross-runtime tables — MLX/CoreML wired memory is invisible to `psutil` so numbers aren't comparable; per-run RSS lives in each run's `summary.json`.

### Final-pass ASR

<!-- TABLE_FINAL_START -->
| Model | License | Released | WER earnings21 | S/D/I earnings21 | Tail p90/p95 earnings21 | RTF earnings21 | Load(s) earnings21 | WER librispeech_test_clean | S/D/I librispeech_test_clean | Tail p90/p95 librispeech_test_clean | RTF librispeech_test_clean | Load(s) librispeech_test_clean | WER librispeech_test_other | S/D/I librispeech_test_other | Tail p90/p95 librispeech_test_other | RTF librispeech_test_other | Load(s) librispeech_test_other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `faster_whisper_large_v3_turbo` | MIT | 2024-10-01 | 8.44 % | 3.85 % / 3.46 % / 1.13 % | 8.41 % / 8.41 % | 0.29 | 1.1 | 1.07 % [0.50 %, 1.71 %] | 0.77 % / 0.13 % / 0.17 % | 3.73 % / 9.36 % | 0.72 | 1.3 | 2.93 % [1.96 %, 3.93 %] | 2.55 % / 0.13 % / 0.25 % | 10.00 % / 16.05 % | 1.07 | 1.1 |
| `canary_qwen_2_5b` | CC-BY-4.0 | 2025-07-01 | 7.73 % | 2.98 % / 4.06 % / 0.68 % | 7.71 % / 7.71 % | 2.27 | 197.3 | 1.66 % [1.04 %, 2.38 %] | 1.15 % / 0.34 % / 0.17 % | 6.64 % / 10.33 % | 1.13 | 972.2 | 2.86 % [1.54 %, 4.32 %] | 2.48 % / 0.00 % / 0.38 % | 9.64 % / 15.12 % | 0.69 | 269.2 |
| `faster_whisper_large_v3_turbo_cuda` | MIT | 2024-10-01 | 10.00 % | 3.49 % / 5.75 % / 0.76 % | 9.96 % / 9.96 % | 0.02 | 1.9 | 1.02 % [0.48 %, 1.66 %] | 0.77 % / 0.13 % / 0.13 % | 3.18 % / 9.36 % | 0.04 | 2.7 | 2.86 % [1.91 %, 3.85 %] | 2.48 % / 0.06 % / 0.32 % | 9.64 % / 14.74 % | 0.05 | 2.3 |
| `parakeet_tdt_0_6b_v2_offline` | CC-BY-4.0 | 2025-06-01 | 8.22 % | 3.90 % / 3.45 % / 0.87 % | 8.18 % / 8.18 % | 0.03 | 1.1 | 1.79 % [1.10 %, 2.58 %] | 1.28 % / 0.34 % / 0.17 % | 6.95 % / 9.36 % | 0.03 | 19.0 | 2.67 % [1.62 %, 3.82 %] | 2.23 % / 0.13 % / 0.32 % | 8.53 % / 15.50 % | 0.03 | 0.9 |

_WER cells show the normalized WER with a 95% bootstrap CI. Peak RSS deliberately omitted from cross-runtime tables — MLX/CoreML wired memory is invisible to ``psutil`` so numbers aren't comparable. Per-run RSS lives in ``results/<run_id>/summary.json``._
<!-- TABLE_FINAL_END -->

### Live-pass ASR

<!-- TABLE_LIVE_START -->
| Model | License | Released | WER earnings21 | S/D/I earnings21 | Tail p90/p95 earnings21 | RTF earnings21 | Load(s) earnings21 | WER librispeech_test_clean | S/D/I librispeech_test_clean | Tail p90/p95 librispeech_test_clean | RTF librispeech_test_clean | Load(s) librispeech_test_clean | WER librispeech_test_other | S/D/I librispeech_test_other | Tail p90/p95 librispeech_test_other | RTF librispeech_test_other | Load(s) librispeech_test_other | FirstP p50 earnings21 (ms) | Stab. earnings21 | FirstP p50 librispeech_test_clean (ms) | Stab. librispeech_test_clean | FirstP p50 librispeech_test_other (ms) | Stab. librispeech_test_other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `parakeet_fluid_audio` | CC-BY-4.0 | 2025-06-01 | 11.15 % | 5.30 % / 4.55 % / 1.30 % | — | 0.01 | 1.1 | 1.69 % [0.91 %, 2.58 %] | 1.20 % / 0.32 % / 0.17 % | 6.25 % / 8.90 % | 1.05 | 4.5 | 3.19 % [2.20 %, 4.28 %] | 2.65 % / 0.20 % / 0.34 % | 9.50 % / 17.00 % | 1.05 | 1.1 | 260 | 0.95 | 220 | 0.92 | 205 | 0.91 |
| `moonshine_base` | MIT | 2024-10-01 | 28.27 % | 8.55 % / 5.15 % / 14.57 % | 28.15 % / 28.15 % | 0.02 | 0.8 | 8.87 % [7.20 %, 11.06 %] | 1.58 % / 1.07 % / 6.22 % | 14.97 % / 18.82 % | 1.01 | 38.6 | 11.65 % [8.25 %, 15.24 %] | 5.67 % / 2.16 % / 3.82 % | 21.82 % / 36.92 % | 1.02 | 0.8 | -9813 | 0.04 | 151 | 0.56 | 105 | 0.83 |
| `whisper_live_large_v3` | MIT | 2024-04-01 | 11.29 % | 6.50 % / 3.80 % / 0.99 % | 11.29 % / 11.29 % | 0.12 | 0.5 | 2.01 % [1.18 %, 2.98 %] | 1.40 % / 0.30 % / 0.31 % | 7.10 % / 10.80 % | 1.10 | 5.5 | 3.91 % [2.82 %, 5.10 %] | 3.20 % / 0.40 % / 0.31 % | 10.80 % / 18.20 % | 1.12 | 0.5 | 1480 | 0.96 | 1180 | 0.98 | 1230 | 0.97 |

_WER cells show the normalized WER with a 95% bootstrap CI. Peak RSS deliberately omitted from cross-runtime tables — MLX/CoreML wired memory is invisible to ``psutil`` so numbers aren't comparable. Per-run RSS lives in ``results/<run_id>/summary.json``._
<!-- TABLE_LIVE_END -->

### Diarization

<!-- TABLE_DIAR_START -->
| Model | License | Released | DER+OV ami_subset | DER−OV ami_subset | M/FA/Conf ami_subset |
|---|---|---|---|---|---|
| `diarizen` | MIT | 2024-12-01 | 23.26 % | 18.84 % | 21.59 % / 0.19 % / 1.48 % |
| `pyannote_3_1` | MIT (gated) | 2023-11-01 | 12.58 % | 8.36 % | 8.93 % / 2.23 % / 1.42 % |

_DER+OV = with-overlap (honest); DER−OV = pyannote skip_overlap=True (comparable to many published numbers). M/FA/Conf = missed / false-alarm / confusion split of DER+OV (fractions of reference speech, sum ≈ DER+OV). Confusion is the worst-failure mode for meeting transcripts — mis-attribution survives into the graph. Peak RSS deliberately omitted from cross-runtime tables — MLX/CoreML wired memory is invisible to ``psutil`` so numbers aren't comparable._
<!-- TABLE_DIAR_END -->

---

## Test recordings

Datasets used and acquisition details: see [`DATASETS.md`](./DATASETS.md).

| Dataset                  | Style                             | Hours       | License           | Acquisition                                                                                |
|--------------------------|-----------------------------------|-------------|-------------------|--------------------------------------------------------------------------------------------|
| `librispeech_test_clean` | Read audiobooks (clean)           | ~5.4 h      | CC-BY-4.0         | auto via HF                                                                                |
| `librispeech_test_other` | Read audiobooks (harder)          | ~5.1 h      | CC-BY-4.0         | auto via HF                                                                                |
| `ami_subset`             | Real meetings (3 ES2004 sessions) | ~1.5 h      | CC-BY-4.0 (gated) | auto via HF, needs `HF_TOKEN`                                                              |
| `earnings21`             | Long-form business calls          | ~3 h subset | CC-BY-4.0         | git clone revdotcom/speech-datasets                                                        |
| `chime6_dev`             | Far-field overlapped meetings     | varies      | LDC custom        | **manual** ([CHiME-6 download](https://www.chimechallenge.org/challenges/chime6/download)) |

The challenge's shared test recordings live in `../test-data/`; they are *demo-day exemplars* and are not part of the graded WER matrix in this card (no clean ground-truth transcripts).

## Reproducibility

```bash
# from evals/
make env-all
make prepare-all
make run-all
make report
```

For the Windows + RTX 3060 Ti host, use Docker instead — see [`docker/README.md`](./docker/README.md) and [`RUNBOOK.md`](./RUNBOOK.md). Each `results/<run_id>/meta.json` records git sha, host info, model id, decoding hash, and env hash. Re-running on a different machine regenerates the tables under that machine's `meta.json`; identical decoding hashes are merged across hosts so the report can show one row per (model, dataset) sourced from whichever host had the most samples.
