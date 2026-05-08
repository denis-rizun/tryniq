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
| Production        | `diarizen` (BUTSpeechFIT, EEND-style) | MIT (weights vary) | 2024-12  | torch CUDA preferred |
| Industry baseline | `pyannote_3_1`                        | MIT (gated)        | 2023-11  | torch CPU/CUDA       |
| Modern challenger | `reverb_diarization_v2` (Rev)         | CC-BY-NC-4.0       | 2024-09  | torch CUDA preferred |

`ecapa_speechbrain` is registered as a speaker-embedding component (PRD §10) but excluded from the diarization comparison — it is not the production diarization choice.

## 2. Why these models?

- **Per-speaker WebRTC capture lets us pick streaming ASR by latency, not by diarization quality.** Each track is already isolated, so we benchmark live ASR purely on per-stream WER and time-to-first-partial. Models like Moonshine that would be unusable in a mixed-stream setup are fair game here.
- **Final pass is allowed to be slow.** It runs as a TaskIQ job after the meeting. The Mac picks `faster-whisper large-v3-turbo` because it's already shipping in `backend/`; the CUDA host runs `canary_qwen_2_5b` because it's currently top of the OpenASR leaderboard at ~5.6% avg WER and fits comfortably in 16 GB VRAM at fp16.
- **Diarization is a backstop for the post-MVP "uploaded recording" path, not the live path.** The architecture commits to per-speaker capture; diarization is benchmarked honestly because the challenge rubric weighs it (20 pt) and we want a credible answer when audio arrives without per-speaker tracks.
- **NVIDIA constraint, kept tight.** Any NVIDIA model in this lineup installs via the **NeMo toolkit pip path** (`nemo-toolkit[all]` + `libsndfile1` + `ffmpeg`). No Riva, no NIM, no NGC API keys, no Triton. Canary-Qwen-2.5B is the only NVIDIA-authored entry and it meets that constraint.
- **Everything is open-source and self-hostable.** No commercial ASR APIs in the loop. Reverb v2's CC-BY-NC license is acknowledged but acceptable for the personal/research scope.

## 3. Hardware required?

**Local-first, two hosts, deliberately split by what each runs natively.**

| Host                                                        |   | Role                          | What runs natively                                                                                                                                                      |
|-------------------------------------------------------------|:--|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| MacBook M4, 16 GB unified                                   |   | Mac-native runtime            | `faster_whisper_large_v3_turbo`, `parakeet_tdt_0_6b_v2_offline`, `parakeet_fluid_audio` (Swift + ANE), `moonshine_base`, `pyannote_3_1`, `reverb_diarization_v2` (slow) |
| Ryzen 5 3600X + RTX 3060 Ti 16 GB (Linux or Windows + WSL2) |   | CUDA 12.x runtime, **Docker** | `canary_qwen_2_5b`, `whisper_live_large_v3`, `diarizen`, `reverb_diarization_v2`, `pyannote_3_1` (when GPU is free)                                                     |

Memory budget per family:
- **Live path** at runtime: per-speaker stream → 16 kHz mono int16 → Swift `streamer/` process. Parakeet-TDT v2 via FluidAudio uses CoreML on the Mac's ANE. Memory: <2 GB resident per streamer worker.
- **Final path**: TaskIQ worker on Mac loads `faster-whisper large-v3-turbo` (~3 GB int8) lazily. The CUDA candidate (`canary_qwen_2_5b`) fits in ~5 GB VRAM at fp16.
- **Diarization**: DiariZen and Reverb v2 each fit in ~3–5 GB VRAM; `pyannote_3_1` runs on CPU at ~1 GB.

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
| Model                                | License   | Released   | WER librispeech_test_clean | S/D/I librispeech_test_clean | Tail p90/p95 librispeech_test_clean | RTF librispeech_test_clean | Load(s) librispeech_test_clean |
|--------------------------------------|-----------|------------|----------------------------|------------------------------|-------------------------------------|----------------------------|--------------------------------|
| `faster_whisper_large_v3_turbo`      | MIT       | 2024-10-01 | 0.00 % [0.00 %, 0.00 %]    | 0.00 % / 0.00 % / 0.00 %     | 0.00 % / 0.00 %                     | 1.00                       | 1.3                            |
| `canary_qwen_2_5b`                   | CC-BY-4.0 | 2025-07-01 | —                          | —                            | —                                   | —                          | —                              |
| `faster_whisper_large_v3_turbo_cuda` | MIT       | 2024-10-01 | —                          | —                            | —                                   | —                          | —                              |
| `parakeet_tdt_0_6b_v2_offline`       | CC-BY-4.0 | 2025-06-01 | 0.00 % [0.00 %, 0.00 %]    | —                            | —                                   | 12.61                      | —                              |

_WER cells show the normalized WER with a 95% bootstrap CI. Peak RSS deliberately omitted from cross-runtime tables — MLX/CoreML wired memory is invisible to ``psutil`` so numbers aren't comparable. Per-run RSS lives in ``results/<run_id>/summary.json``._
<!-- TABLE_FINAL_END -->

### Live-pass ASR

<!-- TABLE_LIVE_START -->
_no runs yet_
<!-- TABLE_LIVE_END -->

### Diarization

<!-- TABLE_DIAR_START -->
_no runs yet_
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
