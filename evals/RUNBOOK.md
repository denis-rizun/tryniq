# Runbook — what to run where, end-to-end

How to drive the bake-off across a MacBook M4 and a Ryzen + RTX 3060 Ti box. Read [`README.md`](./README.md) for the *what* and [`DATASETS.md`](./DATASETS.md) for dataset acquisition; this file is the *how*.

## Where each model runs

### MacBook M4 (16 GB unified)

|   | Model                           | Family      | Why Mac                                            |
|:--|---------------------------------|-------------|----------------------------------------------------|
|   | `faster_whisper_large_v3_turbo` | final       | CTranslate2 int8, CPU/Metal                        |
|   | `parakeet_tdt_0_6b_v2_offline`  | final       | MLX (Apple Silicon only)                           |
|   | `parakeet_fluid_audio`          | live        | Swift `streamer` binary uses CoreML/ANE — Mac-only |
|   | `moonshine_base`                | live        | ONNX, runs anywhere but light enough for Mac       |
|   | `pyannote_3_1`                  | diarization | CPU OK                                             |
|   | `reverb_diarization_v2`         | diarization | CPU OK (slow); GPU preferred                       |

### Ryzen + RTX 3060 Ti 16 GB (Linux + CUDA 12.x)

| Model                   | Family                 | Why CUDA                                  |
|-------------------------|------------------------|-------------------------------------------|
| `canary_qwen_2_5b`      | final                  | NeMo, ~5 GB VRAM fp16, leaderboard topper |
| `whisper_live_large_v3` | live                   | faster-whisper backend, fp16 streaming    |
| `diarizen`              | live (post-MVP) / diar | EEND model, GPU preferred                 |
| `reverb_diarization_v2` | diarization            | runs on either; faster on GPU             |

### Cross-platform

`pyannote_3_1`, `moonshine_base`, `reverb_diarization_v2` — pick the host that's idle.

`ecapa_speechbrain` is registered (`in_comparison=False`) but excluded from the comparison; don't run it for the model card.

---

## End-to-end flow

### 1. One-time host setup

#### On the Mac

```bash
cd evals
make env                       # core CLI/report env
make env-faster-whisper
make env-mlx
make env-moonshine
make env-pyannote
make env-streamer              # WS wrapper for the Swift binary

# Build & install the streamer binary on $PATH (one-time):
cd ../streamer && swift build -c release
ln -s "$(pwd)/.build/release/streamer" /usr/local/bin/streamer
# OR: export TRYNIQ_STREAMER_BIN=$(pwd)/.build/release/streamer
cd ../evals
```

#### On the Ryzen + 3060 Ti box

**On Windows (recommended): use Docker.** Docker Desktop with WSL2 + a recent NVIDIA Windows driver gives GPU passthrough out of the box, and the image bakes in all three CUDA-side envs. See [`docker/README.md`](./docker/README.md) for the full Windows flow:

```powershell
cd evals\docker
docker compose build
docker compose run --rm evals run canary_qwen_2_5b librispeech_test_clean --limit 5
```

**On native Linux** (no Docker):

```bash
# Prereqs: NVIDIA driver + CUDA 12.x runtime, ffmpeg, libsndfile1
cd evals
make env
make env-cuda                  # NeMo + WhisperLive
make env-diarizen              # DiariZen + bundled pyannote-audio
make env-pyannote              # for pyannote_3_1 + Reverb v2
```

#### HuggingFace auth (both hosts, once)

```bash
huggingface-cli login          # writes token to ~/.cache/huggingface
```

Accept the gates for:

- `pyannote/speaker-diarization-3.1`
- `edinburghcstr/ami`
- `BUTSpeechFIT/diarizen-wavlm-large-s80-md`
- `Revai/reverb-diarization-v2`

### 2. Prepare datasets

Datasets land under `<repo>/datasets/` (gitignored). Easiest is to prepare on the Linux box (faster CPU + disk) and `rsync` the `datasets/` folder to the Mac.

```bash
cd evals

# Auto-download:
uv run eval prepare librispeech_test_clean
uv run eval prepare librispeech_test_other
uv run eval prepare ami_subset                 # needs HF_TOKEN
uv run eval prepare earnings21 --max-meetings 4

# CHiME-6 — manual: drop the LDC release under <repo>/datasets/_chime6_raw/
# then:
uv run eval prepare chime6_dev
```

Copy datasets between hosts:

```bash
rsync -a --partial datasets/ user@mac:/path/to/tryniq/datasets/
```

### 3. Smoke test

Run a tiny limit on the lightest model to confirm wiring:

```bash
# Mac:
uv run eval run faster_whisper_large_v3_turbo librispeech_test_clean --limit 5

# CUDA box:
uv run eval run canary_qwen_2_5b librispeech_test_clean --limit 5
```

If both produce a `results/<run_id>/summary.json` with non-null `wer_normalized`, you're good.

### 4. Full bake-off

#### On the Mac

```bash
cd evals
# Final-pass ASR (Mac-runnable models)
uv run eval run faster_whisper_large_v3_turbo librispeech_test_clean --warm
uv run eval run faster_whisper_large_v3_turbo librispeech_test_other --warm
uv run eval run faster_whisper_large_v3_turbo earnings21
uv run eval run parakeet_tdt_0_6b_v2_offline   librispeech_test_clean --warm
uv run eval run parakeet_tdt_0_6b_v2_offline   librispeech_test_other --warm
uv run eval run parakeet_tdt_0_6b_v2_offline   earnings21

# Live-pass ASR (Mac models)
uv run eval run parakeet_fluid_audio librispeech_test_clean --limit 50
uv run eval run parakeet_fluid_audio earnings21              --limit 5
uv run eval run moonshine_base       librispeech_test_clean --warm

# Diarization (Mac)
uv run eval run pyannote_3_1 ami_subset
uv run eval run pyannote_3_1 chime6_dev
```

#### On the Ryzen + 3060 Ti

```bash
cd evals
# Final
uv run eval run canary_qwen_2_5b                     librispeech_test_clean --warm
uv run eval run canary_qwen_2_5b                     librispeech_test_other --warm
uv run eval run canary_qwen_2_5b                     earnings21
uv run eval run faster_whisper_large_v3_turbo_cuda   librispeech_test_clean --warm
uv run eval run faster_whisper_large_v3_turbo_cuda   librispeech_test_other --warm
uv run eval run faster_whisper_large_v3_turbo_cuda   earnings21

# Live
uv run eval run whisper_live_large_v3 librispeech_test_clean --limit 50
uv run eval run whisper_live_large_v3 earnings21              --limit 5

# Diarization
uv run eval run diarizen              ami_subset
uv run eval run diarizen              chime6_dev
uv run eval run reverb_diarization_v2 ami_subset
uv run eval run reverb_diarization_v2 chime6_dev
```

#### Or shotgun (per host)

```bash
uv run eval run-family final
uv run eval run-family live
uv run eval run-family diarization
```

This runs every model in the family. Models that can't run on this host will be marked as failed in `errors.log` — that's fine; the run-family command exits non-zero so you can see what didn't run.

### 5. Generate the model card

After all runs land, on either host (consolidate results into one `evals/results/` directory):

```bash
# If you ran on both hosts, rsync results to one place first:
rsync -a user@cuda-box:/path/to/tryniq/evals/results/ ./results/

uv run eval report
```

This regenerates the tables in `MODEL_CARD.md` and `RESULTS.md`. Per-host results coexist — `_collect()` picks the bucket with the most samples per (model, dataset) so smoke runs don't clobber full runs.

---

## Useful flags

| Flag                                                                           | Effect                                                       |
|--------------------------------------------------------------------------------|--------------------------------------------------------------|
| `--limit N`                                                                    | First N samples (smoke / debugging).                         |
| `--warm`                                                                       | Keep adapter alive across samples; fair RTF.                 |
| `--no-warm` (default)                                                          | Fresh subprocess per sample; honest first-utterance latency. |
| `--beam-size`, `--temperature`, `--language`, `--vad-aggressiveness`, `--pace` | Fairness knobs across all models.                            |
| `--timeout 1800`                                                               | Bump per-sample timeout for long Earnings-21 clips.          |

---

## Recommended operating order

1. Both hosts: `make env` + family-specific envs + HF login.
2. CUDA box: prepare all datasets (faster CPU + disk), `rsync` to Mac.
3. Both hosts: smoke test with `--limit 5` per family.
4. Both hosts: full runs (warm mode for ASR, default for diarization).
5. Consolidate results, `uv run eval report`, read `MODEL_CARD.md`.
