# Linux+CUDA image for evals/ — runs the cuda env (Canary-Qwen, WhisperLive),
# the diarizen env (DiariZen), and the pyannote env (pyannote-3.1, Reverb v2).
# Mac-only adapters (parakeet-mlx, parakeet_fluid_audio) are not built here.
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy

# System deps shared by all envs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git ffmpeg libsndfile1 build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (it'll fetch the Python interpreter each env needs — 3.13 for the core,
# 3.10–3.12 for cuda + diarizen).
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app/evals

# Copy source. uv.lock first so layer caches don't bust on adapter edits.
COPY pyproject.toml uv.lock* ./
COPY src ./src
COPY envs ./envs
COPY Makefile README.md DATASETS.md MODEL_CARD.md RESULTS.md RUNBOOK.md ./

# Pre-warm only the envs that make sense on a CUDA host.
# (Don't sync mlx/streamer/faster-whisper/moonshine — those run on the Mac.)
RUN uv sync && \
    cd envs/pyannote && uv sync && cd /app/evals && \
    cd envs/cuda     && uv sync && cd /app/evals && \
    cd envs/diarizen && uv sync && cd /app/evals

# Datasets + results live on the host; mount them at runtime.
ENV TRYNIQ_EVALS_CACHE=/datasets
VOLUME ["/datasets", "/app/evals/results", "/root/.cache/huggingface"]

ENTRYPOINT ["uv", "run", "eval"]
CMD ["--help"]
