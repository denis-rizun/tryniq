# Tryniq

## What makes it different

Most notetakers receive a mixed audio stream and rely on diarization models to guess who said what. Tryniq doesn't.

- **Per-speaker audio via WebRTC tap.** A Chrome extension monkey-patches `RTCPeerConnection` from the page's main world to intercept each participant's `MediaStreamTrack` *before* the browser mixes them. Each speaker gets their own WebSocket, their own ASR pass, and their display name straight from the Meet DOM. Diarization is solved architecturally, not algorithmically.
- **Meetings as graphs, not transcripts.** Topics, decisions, action items, open questions, and entities are typed nodes in a graph (stored in Postgres), each grounded to the source utterance. Notes, summaries, search, and cross-meeting memory are projections of the same graph.

## Capabilities (MVP)

- Live transcription with sub-3s latency (Moonshine-base) and post-meeting refinement (faster-whisper large-v3).
- Live-updating knowledge graph with Cytoscape visualization and structured Markdown notes.
- Cross-meeting speaker memory via ECAPA-TDNN voice embeddings.
- Cross-meeting topic linking via text embeddings.
- "Chat with the meeting" RAG over transcripts with cited timestamps.
- Markdown export for Notion / wiki / tickets.
- Single `docker compose up` brings up the whole stack.

## Architecture

One Python codebase (`tryniq/`) runs as **two processes**:

- **`api`** — FastAPI: REST + WebSockets (extension ingest) + SSE (UI live updates). Async, non-blocking only.
- **`worker`** — TaskIQ worker: ASR (Moonshine + faster-whisper), aggregator windows, graph builder LLM extraction, speaker ID, embeddings. Anything CPU/GPU/LLM-bound runs here.

Three infra containers: **Postgres** (with pgvector — meetings, utterances, graph nodes/edges, embeddings, speaker profiles), **MinIO** (per-speaker WAVs), **Redis** (TaskIQ broker + UI pub/sub). Optional Ollama for local LLM. The Next.js UI is a separate frontend container.

```
  Browser (extension)
        │ WebSocket PCM
        ▼
  ┌─────────┐    enqueue    ┌──────────┐
  │   api   │──────────────▶│  worker  │
  │ FastAPI │   TaskIQ/Redis│ TaskIQ   │
  └────┬────┘◀──────────────└────┬─────┘
       │   Redis pub/sub          │
       │ (meeting:{id}:events)    │
       ▼                          ▼
   SSE → UI                  reads PCM,
                             writes graph
       │                          │
       └─────────┬────────────────┘
                 ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ Postgres │  │  MinIO   │  │  Redis   │
   │ pgvector │  │ (audio)  │  │ broker + │
   │  graph   │  │          │  │ pubsub   │
   └──────────┘  └──────────┘  └──────────┘
```

Audio bytes are never task arguments — `api` streams PCM into MinIO and enqueues object paths/IDs; the worker reads from MinIO.

LLM defaults to Anthropic Claude Haiku 4.5 with a self-host fallback to Qwen 2.5 14B via Ollama/vLLM. All other models run locally.

## Running locally

Full stack via Docker Compose:

```
cp .env.example .env
docker compose up -d --build
```

Brings up `postgres`, `minio`, `redis`, `api`, and `worker`. The API listens on `:8000`. MinIO console on `:9101`.

For dev with hot reload (run from repo root with the package installed):

```
uvicorn tryniq.api.main:app --reload --port 8000
taskiq worker tryniq.tasks:broker --reload
```

Extension build:

```
cd extension && pnpm install && pnpm build
# load extension/dist/ as unpacked in chrome://extensions
```

## Dependencies

Backend: `fastapi`, `uvicorn`, `taskiq`, `taskiq-redis`, `redis`, `asyncpg`, `pgvector`, `minio`, `pydantic`, `pydantic-settings`, `structlog`. Plus model deps in the worker (`onnxruntime`, `faster-whisper`, `speechbrain`, etc.).

## Status

Pre-implementation — see [`docs/PRD.md`](docs/PRD.md) for the full product requirements. Target demo: 2026-05-11.
