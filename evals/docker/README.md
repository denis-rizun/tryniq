# Docker (Windows + Ryzen + RTX 3060 Ti)

The CUDA-only models (`canary_qwen_2_5b`, `whisper_live_large_v3`, `diarizen`, `reverb_diarization_v2`, `pyannote_3_1`) run inside a single Linux+CUDA image. The Mac-only models (`parakeet_tdt_0_6b_v2_offline`, `parakeet_fluid_audio`) are *not* built here — keep those on the M4.

## Prereqs (Windows host)

- **Docker Desktop 4.x+** with the WSL2 backend.
- **NVIDIA driver for Windows** that supports CUDA on WSL — any modern Studio/Game Ready driver does. No `nvidia-container-toolkit` install needed; Docker Desktop bundles it.
- Verify GPU passthrough works:
  ```powershell
  docker run --rm --gpus all nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 nvidia-smi
  ```
  You should see your 3060 Ti listed.

## Build

```powershell
cd evals\docker
docker compose build
```

Build will pre-warm the `core`, `pyannote`, `cuda`, and `diarizen` envs (each in its own `uv` workspace, fetching its own Python interpreter). First build is slow (~10–20 min); subsequent rebuilds reuse layers.

## HuggingFace auth

Some models/datasets are gated. Set the token before running so it forwards into the container:

```powershell
$env:HF_TOKEN = "hf_xxxxxxxx"
```

The token is mounted into the persistent `hf-cache` volume so model weights survive container restarts.

## Prepare datasets

Datasets live on the host under `tryniq/datasets/` and are bind-mounted into the container at `/datasets`. Easiest is to download them on the Linux side via the container so paths and permissions match:

```powershell
docker compose run --rm evals prepare librispeech_test_clean
docker compose run --rm evals prepare librispeech_test_other
docker compose run --rm evals prepare ami_subset
docker compose run --rm evals prepare earnings21
```

For CHiME-6 (manual): drop the LDC release into `tryniq\datasets\_chime6_raw\` on the host, then:

```powershell
docker compose run --rm evals prepare chime6_dev
```

## Run

Anything you'd type after `uv run eval` goes after `docker compose run --rm evals`. Smoke test:

```powershell
docker compose run --rm evals run canary_qwen_2_5b librispeech_test_clean --limit 5
```

Full bake-off (CUDA-side):

```powershell
docker compose run --rm evals run canary_qwen_2_5b                     librispeech_test_clean --warm
docker compose run --rm evals run canary_qwen_2_5b                     librispeech_test_other --warm
docker compose run --rm evals run canary_qwen_2_5b                     earnings21
docker compose run --rm evals run faster_whisper_large_v3_turbo_cuda   librispeech_test_clean --warm
docker compose run --rm evals run faster_whisper_large_v3_turbo_cuda   librispeech_test_other --warm
docker compose run --rm evals run faster_whisper_large_v3_turbo_cuda   earnings21
docker compose run --rm evals run whisper_live_large_v3 librispeech_test_clean --limit 50
docker compose run --rm evals run whisper_live_large_v3 earnings21              --limit 5
docker compose run --rm evals run diarizen              ami_subset
docker compose run --rm evals run diarizen              chime6_dev
docker compose run --rm evals run reverb_diarization_v2 ami_subset
docker compose run --rm evals run reverb_diarization_v2 chime6_dev
docker compose run --rm evals run pyannote_3_1          ami_subset
docker compose run --rm evals run pyannote_3_1          chime6_dev
```

Or shotgun:

```powershell
docker compose run --rm evals run-family final
docker compose run --rm evals run-family live
docker compose run --rm evals run-family diarization
```

Mac-only models (`parakeet_tdt_0_6b_v2_offline`, `parakeet_fluid_audio`, `moonshine_base`, `faster_whisper_large_v3_turbo`) will be marked failed in `errors.log` from `run-family` — that's expected.

## Consolidate + report

Results land on the host under `evals/results/` (bind-mounted from the container). Once you've finished both Mac and Windows runs, copy the Mac results into the Windows host's `evals/results/` (or vice versa), then:

```powershell
docker compose run --rm evals report
```

Or run `uv run eval report` directly on either host — the report code is platform-agnostic.

## Performance notes

- **Memory.** The compose file leaves `mem_limit` unset; Docker Desktop on Windows has its own WSL2 memory cap (default ~50% of RAM). If `canary_qwen_2_5b` OOMs on first load, raise the WSL2 memory limit in `%USERPROFILE%\.wslconfig`.
- **VRAM.** 3060 Ti 16 GB is enough for all models in the lineup at fp16. If you hit OOM, drop `--beam-size 1` (default already) and ensure no other GPU process is running.
- **Disk.** First build + a full prepare consumes ~30–50 GB inside the WSL2 distro and on the host's `datasets/`. Make sure the WSL2 vhdx isn't capped.

## Troubleshooting

- `docker: Error response from daemon: could not select device driver "" with capabilities: [[gpu]]` — Docker Desktop GPU support not enabled. Settings → Resources → WSL Integration, and ensure the NVIDIA driver is recent.
- `CUDA out of memory` on Canary-Qwen — close other GPU users; if it persists, the WhisperLive server may still be running. Check with `docker compose ps`.
- DiariZen `from_pretrained` complains about HF gate — re-check `HF_TOKEN` and that you accepted the model license on huggingface.co.
- `whisper-live server did not open …` — usually means the upstream server crashed during model load. Check the run's `errors.log` for the underlying stack trace.
