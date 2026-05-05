# Tryniq

## What makes it different

Most notetakers receive a mixed audio stream and rely on diarization models to guess who said what. Tryniq doesn't.

- **Per-speaker audio via WebRTC tap.** A Chrome extension monkey-patches `RTCPeerConnection` from the page's main world to intercept each participant's `MediaStreamTrack` *before* the browser mixes them. Each speaker gets their own WebSocket, their own ASR pass, and their display name straight from the Meet DOM. Diarization is solved architecturally, not algorithmically.
- **Meetings as graphs, not transcripts.** Topics, decisions, action items, open questions, and entities are typed nodes in a graph (stored in Postgres), each grounded to the source utterance. Notes, summaries, search, and cross-meeting memory are projections of the same graph.

## Capabilities (MVP)

- Per-speaker capture from Google Meet via the Chrome extension (WebRTC tap, Silero VAD-gated). *Phase 1 — done.*
- Live transcription with sub-3s latency (Parakeet-TDT v2 in a native Swift streamer on Apple Silicon) and post-meeting refinement (faster-whisper large-v3-turbo in the Python worker). *Phase 2 — done.*
- Knowledge graph built per meeting: typed nodes (`Meeting`, `Person`, `Topic`, `Decision`, `ActionItem`, `OpenQuestion`, `Entity`, `Utterance`) with grounded `SOURCE` edges, idempotent dedup via embeddings, lifecycle states (`provisional` / `confirmed` / `superseded`). *Phase 3 — done.*
- Post-meeting metadata projection: summary, decisions, action items, open questions, topics, and related past meetings — derived from the graph and exposed at `GET /meetings/{id}/metadata`. *Done.*
- Cross-meeting topic linking via 384-dim text embeddings (pgvector cosine search). *Done.*
- "Chat with the meeting" — RAG over utterance + graph embeddings with cited timestamps, scoped to a single meeting or all meetings, streamed via SSE. *Phase 6 — done.*
- LLM observability and prompt management via self-hosted Langfuse v2 (single container, sharing the existing Postgres). *Done.*
- Cross-meeting speaker memory via ECAPA-TDNN voice embeddings. *Phase 5 — pending.*
- Markdown export for Notion / wiki / tickets. *Phase 5 — pending.*
- Self-hostable: backend stack (api + worker + Postgres/pgvector + Redis + MinIO + Langfuse) runs via Docker Compose; the streamer runs natively on a Mac.

## Architecture

Three processes (plus the browser extension and the Next.js UI):

- **`backend/api`** — FastAPI under `/api/v1`. REST + ingest WebSocket (`/meetings/{m}/streams/{s}`) + the streamer registration WebSocket (`/asr/sessions`) + SSE (`/meetings/{id}/events`) + global lifecycle WS (`/events/ws`). Async, non-blocking only.
- **`backend/worker`** — TaskIQ worker (same Docker image, different command). Owns post-meeting CPU/GPU/LLM work: `transcribe_final` (faster-whisper), graph extraction, utterance + graph embeddings, metadata projection, chat retrieval indexing. Speaker ID is the remaining Phase 5 addition.
- **`streamer/`** — Swift 6 process running live ASR (Parakeet-TDT v2 via `fluid_audio`, CoreML on Apple Silicon). Connects to the api as a WebSocket worker on `/asr/sessions`; the api forwards per-speaker PCM frames and the streamer publishes `partial` / `final` transcript events back. Multiple streamer instances may register; the api round-robins streams by lowest load. Not containerized — runs natively on a Mac.

Four infra containers: **Postgres + pgvector** (meetings, utterances, participants, graph nodes/edges, embeddings), **MinIO** (per-speaker WAVs + exports), **Redis** (TaskIQ broker + UI pub/sub), **Langfuse v2** (prompt management + LLM trace/cost observability, sharing the same Postgres). LLM provider is OpenAI (`gpt-4o-mini` for graph / chat / metadata, `text-embedding-3-small` for retrieval).

```
  Browser (extension)
        │ WS /meetings/{m}/streams/{s}  (PCM + control)
        ▼
  ┌─────────┐                         ┌──────────────────┐
  │   api   │◀── WS /asr/sessions ───│ streamer (Swift) │
  │ FastAPI │   PCM out / events in   │ Parakeet-TDT v2  │
  └────┬────┘                         │  fluid_audio     │
       │   ▲                          └──────────────────┘
       │   │ Redis pub/sub
       │   │ meeting:{id}:events
       │   │
       │   │ TaskIQ enqueue (post-meeting)
       │   ▼
       │  ┌──────────┐
       │  │  worker  │  transcribe_final (faster-whisper); Phase 3+: graph
       │  └────┬─────┘
       │       │
       ▼       ▼
   SSE / global WS → UI       writes ──▶ Postgres / MinIO

   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ Postgres │  │  MinIO   │  │  Redis   │
   │ pgvector │  │ per-spk  │  │ broker + │
   │          │  │  WAVs    │  │ pub/sub  │
   └──────────┘  └──────────┘  └──────────┘
```

Audio bytes are never task arguments. The api buffers PCM straight to MinIO via `WavWriter` and forwards a copy to the assigned streamer over its WebSocket; PCM never goes through TaskIQ or Redis.

## Repository layout

```
backend/    FastAPI api + TaskIQ worker (Python 3.13). See backend/CONSTITUTION.md.
streamer/   Swift 6 live-ASR worker (Parakeet-TDT v2). See streamer/CONSTITUTION.md.
frontend/   Next.js 16 App Router UI (TS strict, pnpm). See frontend/CONSTITUTION.md.
extension/  Chrome MV3 extension (TS, pnpm).
docs/       PRD.md (source of truth), phase-1-spec.md, etc.
CLAUDE.md   Top-level guidance for agents and maintainers.
```

Each package has its own **CONSTITUTION.md** that is binding for code shape inside that package — agents and maintainers must read the relevant constitution before editing. `CLAUDE.md` and `docs/PRD.md` win on architectural questions; constitutions win on code shape.

## Running locally

Backend stack (Postgres, MinIO, Redis, api, worker, migrations) via Docker Compose:

```
cp backend/.env.example backend/.env
make bc                 # cd backend && docker compose up --build -d
```

The API listens on `:8000` (root path `/api/v1`); MinIO console on `:9101`; redis-insight on `:5540`.

Frontend dev server:

```
cp frontend/.env.example frontend/.env
make fr                 # cd frontend && pnpm dev
```

Extension build (load `extension/dist/` as unpacked in `chrome://extensions`):

```
make ext-build          # or `make ext-dev` for watch mode
```

Streamer (live ASR — requires Apple Silicon for CoreML):

```
cd streamer
cp .env.example .env    # set ASR_LIVE_AUTH_TOKEN and api URL
swift run streamer
```

Without a streamer connected, meetings still record cleanly to MinIO and `transcribe_final` produces the post-meeting transcript — only the live transcript is missing.

## Dependencies

- **Backend** (`backend/pyproject.toml`): `fastapi`, `uvicorn`, `taskiq`, `taskiq-redis`, `redis`, `asyncpg`, `sqlmodel`, `pgvector`, `minio`, `pydantic`, `pydantic-settings`, `structlog`, `faster-whisper`. No Python live-ASR deps — live ASR is in the streamer.
- **Streamer** (`streamer/Package.swift`): `fluid_audio` (Parakeet-TDT v2 via CoreML).
- **Frontend** (`frontend/package.json`): Next.js 16, React 19, TanStack Query, Zustand, Biome.
- **Extension** (`extension/package.json`): Vite + TypeScript, Silero VAD ONNX.

## Status

Phase 1 (capture), Phase 2 (live transcription), Phase 3 (graph builder + metadata projection), and Phase 6 (chat RAG) are **done**. Phase 5 (cross-meeting speaker memory via ECAPA, Markdown export) is next — see [`docs/PRD.md`](docs/PRD.md) §14. Target demo: 2026-05-11.
