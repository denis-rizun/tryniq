# `evals/` — model-card harness

Reproducible benchmark for the **Open Voice Notetaker challenge** (demo 2026-05-11). Compares ASR + diarization models on a fixed set of public English datasets and generates the challenge-required model card.

This module is **standalone** — `cd evals && make env-all && make prepare-all && uv run eval run …` works without `backend/`, `frontend/`, or `streamer/` source on disk. The single exception is `parakeet_fluid_audio`, which expects a prebuilt `streamer` binary on `$PATH` (or `TRYNIQ_STREAMER_BIN=…`).

## Hardware tiers

| Tier | Host                                     | What runs natively                                                                                                        |
|------|------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| A    | MacBook M4, 16 GB unified                | `faster_whisper_large_v3_turbo`, `parakeet_tdt_0_6b_v2_offline`, `parakeet_fluid_audio`, `moonshine_base`, `pyannote_3_1` |
| B    | Ryzen 5 3600X + RTX 3060 Ti (16 GB VRAM) | `canary_qwen_2_5b`, `whisper_live_large_v3`, `diarizen`, `reverb_diarization_v2`                                          |

Each adapter runs in its own `uv` env, so dependency conflicts (CTranslate2 vs MLX vs NeMo vs CUDA wheels) don't cross-contaminate.

## Layout

```
evals/
├── MODEL_CARD.md     # Challenge submission: which models, why, hardware, …
├── DATASETS.md       # Dataset registry, licenses, acquisition (manual)
├── RESULTS.md        # Auto-generated comparison tables
├── pyproject.toml    # Core uv env (CLI + report)
├── Makefile          # `make env-<family>`, `make run-<family>`, `make report`
├── envs/             # One isolated uv env per model family
└── src/eval/         # CLI, runner, adapters, dataset loaders, metrics
```

Datasets land under `<repo>/datasets/` (override via `TRYNIQ_EVALS_CACHE`). The whole `datasets/` directory is in `.gitignore` — never commit audio.

## Quickstart

```bash
# 1. Bootstrap the core env + the lightest model env
make env
make env-faster-whisper

# 2. Prepare a dataset (downloads or normalizes into <repo>/datasets/)
uv run eval prepare librispeech_test_clean --max-utterances 50

# 3. Run one model × one dataset (canonical entrypoint)
uv run eval run faster_whisper_large_v3_turbo librispeech_test_clean --limit 50

# 4. Regenerate the comparison tables
uv run eval report
```

Cold vs warm:

* `--no-warm` (default) spawns one adapter subprocess per sample. Honest first-utterance load latency.
* `--warm` reuses one subprocess across the whole dataset. Fair steady-state RTF.

## CLI

```bash
uv run eval list                                       # registered models + datasets
uv run eval prepare <dataset> [--max-utterances N]
uv run eval run <model> <dataset> [--limit N] [--warm] [--beam-size 1] [--pace realtime]
uv run eval run-family final|live|diarization [--warm]  # exits non-zero on any failure
uv run eval report                                      # regenerate RESULTS.md + MODEL_CARD.md tables
```

The `DecodingConfig` (`beam_size`, `temperature`, `language`, `vad_aggressiveness`, `pace`) is passed to every adapter for fairness; per-model overrides live in `Model.extra_args` in the registry.

## Model lineup (3 per family)

### Final-pass ASR
| Slot          | Model                                | License   | Hardware            |
|---------------|--------------------------------------|-----------|---------------------|
| Mac default   | `faster_whisper_large_v3_turbo`      | MIT       | M4 CPU/Metal (int8) |
| Same on CUDA  | `faster_whisper_large_v3_turbo_cuda` | MIT       | RTX 3060 Ti (fp16)  |
| CUDA accuracy | `canary_qwen_2_5b`                   | CC-BY-4.0 | 16 GB VRAM (NeMo)   |
| Compact       | `parakeet_tdt_0_6b_v2_offline`       | CC-BY-4.0 | M4 (MLX)            |

### Live-pass ASR
| Slot           | Model                   | License   | Hardware                            |
|----------------|-------------------------|-----------|-------------------------------------|
| Production     | `parakeet_fluid_audio`  | CC-BY-4.0 | M4 (Swift binary on `$PATH`)        |
| Reference      | `moonshine_base`        | MIT       | Anywhere (ONNX)                     |
| CUDA reference | `whisper_live_large_v3` | MIT       | 16 GB VRAM (faster-whisper backend) |

### Diarization
| Slot              | Model                   | License            | Hardware       |
|-------------------|-------------------------|--------------------|----------------|
| Production        | `diarizen`              | MIT (weights vary) | CUDA preferred |
| Industry baseline | `pyannote_3_1`          | MIT (gated)        | CPU/CUDA       |
| Modern challenger | `reverb_diarization_v2` | CC-BY-NC-4.0       | CUDA preferred |

`ecapa_speechbrain` is registered as a speaker-embedding component (PRD §10) but excluded from the diarization comparison via `in_comparison=False`.

## Datasets

| Dataset                  | License    | Acquisition                                                                                                                                                          |
|--------------------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `librispeech_test_clean` | CC-BY-4.0  | `uv run eval prepare librispeech_test_clean` (HF)                                                                                                                    |
| `librispeech_test_other` | CC-BY-4.0  | `uv run eval prepare librispeech_test_other` (HF)                                                                                                                    |
| `ami_subset`             | CC-BY-4.0  | `uv run eval prepare ami_subset` (HF, requires `HF_TOKEN` for the gated dataset)                                                                                     |
| `earnings21`             | CC-BY-4.0  | `uv run eval prepare earnings21` (clones revdotcom/speech-datasets)                                                                                                  |
| `chime6_dev`             | LDC custom | **Manual.** Drop the official release under `<repo>/datasets/_chime6_raw/` (or `CHIME6_ROOT=…`). Source: <https://www.chimechallenge.org/challenges/chime6/download> |

See [`DATASETS.md`](./DATASETS.md) for full acquisition + manifest-format details.

## Adding a model

1. Pick or create `envs/<env>/` (`pyproject.toml` + `adapter/`).
2. Add `envs/<env>/adapter/<name>.py` exporting `transcribe_one(audio_path) -> dict` and using `_base.serve(args, transcribe_one)` to support cold + warm modes.
3. Register it in `src/eval/registry.py` with `license` and `release_date`.
4. `make env-<env>` then `uv run eval run <name> <dataset>`.

Wire contract for adapters:

* On stdout, emit a single line `---HYPOTHESIS-JSON---`, then a single JSON line conforming to `eval.types.Hypothesis`. Anything else on stdout/stderr is chatter and ignored.
* Live adapters fill `partials` (per `eval.types.Partial`) so streaming metrics (stability ratio, real-time lag) light up.
* Decoding flags (`--beam-size`, `--temperature`, `--language`, `--vad-aggressiveness`, `--pace`) must be accepted via `parse_known_args`; honor what you can, log deviations.

## Adding a dataset

1. Create `src/eval/datasets/<name>.py` exposing `prepare(...)` (writes `manifest.jsonl`).
2. Register it in `src/eval/registry.py` with `license` and `description`.
3. Document license + acquisition in `DATASETS.md`.

## Why isolated envs

`faster-whisper` (CTranslate2), `parakeet-mlx` (MLX), NeMo (CUDA), DiariZen (its own pinned `pyannote-audio` fork), and the prebuilt Swift `streamer` binary all want different `torch` / `numpy` constraints. Forcing them into one env creates resolver hell and silent ABI mismatches. Each adapter runs in its own `uv` subprocess; the parent runner pipes a sentinel-tagged JSON Hypothesis back over stdout. This is what makes the harness honest: every model runs in the env you'd ship it in.
