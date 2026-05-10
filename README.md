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
- Markdown export for Notion / wiki / tickets. *Done.*
- Cross-meeting search (full-text over meetings, participants, utterances) backing the command palette. *Done.*
- Uploaded-recording fallback path: ffmpeg normalize + DiariZen diarization (BUT-FIT `wavlm-large-s80-md-v2`) + final ASR + graph extraction, with a single-cluster fallback if DiariZen is not installed. *Done.*
- LLM observability and prompt management via self-hosted **Langfuse v3** (langfuse-web + langfuse-worker + ClickHouse, sharing the existing Postgres + MinIO). *Done.*
- Cross-meeting speaker memory via ECAPA-TDNN voice embeddings + inline transcript editing with localized graph re-extraction. *Phase 7 — deferred to post-demo.*
- Self-hostable: backend stack (api + worker + Postgres/pgvector + Redis + MinIO + ClickHouse + Langfuse web/worker) runs via Docker Compose; the streamer runs natively on a Mac.

## Architecture

Three processes (plus the browser extension and the Next.js UI):

- **`backend/api`** — FastAPI under `/api/v1`, organised into 12 feature modules (`meeting`, `ingest`, `transcript`, `participant`, `asr`, `graph`, `metadata`, `chat`, `export`, `audio`, `search`, `upload`) plus `core`. REST + ingest WebSocket (`/meetings/{m}/streams/{s}`) + the streamer registration WebSocket (`/asr/sessions`) + SSE (`/meetings/{id}/events`) + global lifecycle WS (`/events/ws`) + `GET /models` + `GET /health`. Async, non-blocking only — never imports torch / faster-whisper.
- **`backend/worker`** — TaskIQ worker (same Docker image, different command). Owns post-meeting CPU/GPU/LLM work: `transcribe_final` (faster-whisper large-v3-turbo), `aggregate_window` + `build_graph` (graph extraction), `extract_meeting_metadata` (title / summary / decisions / action items / open questions / topics / related meetings), `embed_utterances` (RAG indexing), and `process_upload` (ffmpeg + DiariZen + final ASR for the uploaded-recording fallback path). Speaker ID and inline-edit `rebuild_window` are the deferred Phase 7 additions.
- **`streamer/`** — Swift 6 process running live ASR (Parakeet-TDT v2 via `fluid_audio`, CoreML on Apple Silicon). Connects to the api as a WebSocket worker on `/asr/sessions`; the api forwards per-speaker PCM frames and the streamer publishes `partial` / `final` transcript events back. Multiple streamer instances may register; the api round-robins streams by lowest load. Not containerized — runs natively on a Mac.

Infra containers (all in `backend/compose.yml`): **Postgres + pgvector** (meetings, participants, utterances, graph nodes/edges, embeddings, chat sessions/messages, with pgvector indexes on 1536-dim embeddings), **MinIO** (per-speaker WAVs + exports + langfuse media bucket), **Redis** (TaskIQ broker + meeting/global pub/sub), **ClickHouse** (Langfuse v3 trace/event store), **Langfuse web + worker** (`langfuse/langfuse:3` / `langfuse-worker:3` — prompt management, LLM trace/cost observability, auto-bootstrapped against the same Postgres on a `langfuse` database), plus **redis-insight** for dev. LLM provider is OpenAI (configurable): `gpt-5.5` for graph / chat / metadata extraction, `text-embedding-3-small` (1536-dim) for both RAG and graph node dedup. The diarization pipeline used on the uploaded-recording path is DiariZen (`BUT-FIT/diarizen-wavlm-large-s80-md-v2`), installed manually because it ships its own forked `pyannote-audio`; without it the uploader falls back to a single-cluster pass-through.

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
       │   │ meeting:{id}:events + global lifecycle
       │   │
       │   │ TaskIQ enqueue (post-meeting)
       │   ▼
       │  ┌──────────┐
       │  │  worker  │  transcribe_final · aggregate_window · build_graph ·
       │  └────┬─────┘  extract_meeting_metadata · embed_utterances · process_upload
       │       │
       ▼       ▼
   SSE / global WS → UI       writes ──▶ Postgres / MinIO

   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌────────────┐
   │ Postgres │  │  MinIO   │  │  Redis   │  │ ClickHouse │  │  Langfuse  │
   │ pgvector │  │ per-spk  │  │ broker + │  │ (Langfuse  │  │  web +     │
   │ (1536-d) │  │  WAVs    │  │ pub/sub  │  │  events)   │  │  worker v3 │
   └──────────┘  └──────────┘  └──────────┘  └────────────┘  └────────────┘
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

## Models

| Role                     | Provider / runtime               | Model                                         | Where it runs                            |
|--------------------------|----------------------------------|-----------------------------------------------|------------------------------------------|
| Live ASR                 | `fluid_audio` (Swift, CoreML)    | Parakeet-TDT v2                               | `streamer/` on Apple Silicon             |
| Final ASR                | faster-whisper (CTranslate2)     | `large-v3-turbo` (cpu/int8 default)           | `worker` (`transcribe_final`)            |
| VAD                      | onnxruntime-web (WASM)           | Silero VAD                                    | Browser AudioWorklet                     |
| Graph extraction LLM     | OpenAI (configurable)            | `gpt-5.5`                                     | `worker` (`build_graph`)                 |
| Metadata extraction LLM  | OpenAI                           | `gpt-5.5`                                     | `worker` (`extract_meeting_metadata`)    |
| Chat (RAG) LLM           | OpenAI                           | `gpt-5.5` (streaming)                         | `api` (chat router → `core/client.py`)   |
| Text embeddings          | OpenAI                           | `text-embedding-3-small` (1536-dim)           | RAG + graph node dedup (cosine ≥ 0.85)   |
| Diarization (upload only)| DiariZen (BUT-FIT) / pyannote-fork | `BUT-FIT/diarizen-wavlm-large-s80-md-v2`    | `worker` (`process_upload`)              |
| Speaker embedding (Phase 7)| SpeechBrain ECAPA-TDNN         | 192-dim                                       | `worker` (deferred, schema reserved)     |
| LLM observability        | Langfuse v3 SDK (`langfuse>=4.5`)| Self-hosted Langfuse web + worker images `:3`| `langfuse-web` / `langfuse-worker`       |

The `GET /api/v1/models` endpoint reports the active configuration at runtime.

## Dependencies

- **Backend** (`backend/pyproject.toml`): `fastapi`, `uvicorn`, `taskiq`, `taskiq-redis`, `redis`, `asyncpg`, `psycopg`, `sqlmodel`, `pgvector`, `aioboto3`, `pydantic`, `pydantic-settings`, `structlog`, `faster-whisper`, `numpy`, `onnxruntime`, `openai`, `python-multipart`, `langfuse`. No Python live-ASR deps — live ASR is in the streamer. DiariZen + its forked `pyannote-audio` are installed manually for the upload path (see comment in `pyproject.toml`).
- **Streamer** (`streamer/Package.swift`): `fluid_audio` (Parakeet-TDT v2 via CoreML).
- **Frontend** (`frontend/package.json`): Next.js 16 App Router, React 19, TanStack Query, Zustand, Biome, Cytoscape (graph view).
- **Extension** (`extension/package.json`): Vite 8 + TypeScript 5.7, React 19 (popup only), `onnxruntime-web` (Silero VAD inside the AudioWorklet). Manifest V3, `MAIN`-world `injected.js` (WebRTC patch) + `ISOLATED`-world `content.js` (DOM observer + per-stream WebSocket clients).

## Status

Phases 1–6 are **done**: capture (extension), live transcription (Swift streamer), graph builder + metadata projection, graph + notes UI, post-processing + chat RAG + Markdown export + cross-meeting search + uploaded-recording fallback, and demo-week polish. Phase 7 (cross-meeting speaker memory via ECAPA, inline transcript editing with localized re-extraction) is **deferred to post-demo**. See [`docs/PRD.md`](docs/PRD.md) §14. Target demo: 2026-05-11.
