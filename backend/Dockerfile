# ============================================
# Stage 1: Build stage
# ============================================
FROM python:3.13-slim-bookworm AS builder

ARG COMPILE_BYTECODE=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=${COMPILE_BYTECODE} \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_HTTP_TIMEOUT=300

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && pip install --no-cache-dir uv==0.11.8

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --python python3

# DiariZen ships its own pyannote-audio fork (in-tree at pyannote-audio/). Upstream
# pyannote PyPI does NOT work — its SpeakerDiarization signature differs from what
# DiariZen subclasses. Pin numpy<2 (the fork uses np.NaN) and torch 2.6 (cp313 + arm64
# wheels exist; older tags don't ship cp313 wheels for our dev env).
ARG DIARIZEN_REF=main
RUN --mount=type=cache,target=/root/.cache/uv \
    git clone --depth 1 --branch "${DIARIZEN_REF}" https://github.com/BUTSpeechFIT/DiariZen /tmp/DiariZen \
    && uv pip install --python /opt/venv/bin/python \
        "torch==2.6.0" "torchaudio==2.6.0" "numpy<2" "accelerate" "toml" \
        "/tmp/DiariZen/pyannote-audio" "/tmp/DiariZen" \
    && rm -rf /tmp/DiariZen

COPY . .

# ============================================
# Stage 2: Runtime stage
# ============================================
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ffmpeg

RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser \
    && install -d -o appuser -g appgroup /home/appuser/.cache /home/appuser/.cache/huggingface

ENV HF_HOME=/home/appuser/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/home/appuser/.cache/huggingface/hub \
    XDG_CACHE_HOME=/home/appuser/.cache

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv
COPY --from=builder --chown=appuser:appgroup /app /app
COPY --chown=appuser:appgroup entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://127.0.0.1:${API_PORT:-8000}/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["api"]
