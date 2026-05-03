# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Phase 1 (Capture) and Phase 2 (live transcription) are done. The Chrome MV3 extension captures per-speaker audio, the FastAPI `api` persists per-stream WAVs to MinIO, a separate **Swift streamer** process (in `streamer/`) connects to `api` over a WebSocket and runs live ASR (Parakeet-TDT v2 via `fluid_audio`), publishing partials and committed segments back through the api's pub/sub. The TaskIQ `worker` runs `transcribe_final` after meeting end to refine the transcript. Phase 3 (graph builder) and Phase 5 (cross-meeting memory) are next; see PRD §14.

Runtime: Python **3.13** for the backend (`backend/`), Swift 6 for the live ASR streamer (`streamer/`), Node 20 + pnpm for the frontend (`frontend/`) and the Chrome extension (`extension/`).

Target demo: 2026-05-11.

## Before you edit anything — read the constitution

Each package has its own **CONSTITUTION.md** that is the mandatory code-shape guide for that package. They are *binding*: an agent or maintainer must read the relevant constitution end-to-end **before** writing or modifying code in that package, and must keep the codebase coherent with what is already there rather than introducing a new flavor.

| Package        | Constitution                  | Covers                                                                                                  |
|----------------|-------------------------------|---------------------------------------------------------------------------------------------------------|
| `backend/`     | `backend/CONSTITUTION.md`     | Python 3.13 / FastAPI / TaskIQ / SQLModel; module layout (`router.py` / `service.py` / `schemas.py` / …), imports, exceptions, dependency wiring. |
| `streamer/`    | `streamer/CONSTITUTION.md`    | Swift 6 / strict concurrency / actors; flat `src/` layout, **150-line cap per file**, wire protocol co-owned with `backend/app/asr/schemas.py`. |
| `frontend/`    | `frontend/CONSTITUTION.md`    | TypeScript strict / Next.js 16 App Router / React 19 / pnpm; `src/{app,components,lib}` layout, server-vs-client rules, `@/` import alias, biome formatting. |

Conflict-resolution order: `CLAUDE.md` (this file) and `docs/PRD.md` win on **architectural** questions; the package's CONSTITUTION wins on **code shape**. Wire-format types are co-owned across packages — `backend/app/asr/schemas.py` is the source of truth for streamer wire fields, and `backend/app/*/schemas.py` is the source of truth for frontend `lib/api/types.ts`.

## What this project is

An open-source, self-hostable meeting intelligence platform — a tl;dv replacement — built around two non-obvious architectural commitments. Read PRD §5 before making any non-trivial design decision; the rest of the system is downstream of these two ideas.

### Architectural commitment 1: per-speaker audio via WebRTC tap

**We do not run speaker diarization on the live path.** A Chrome extension monkey-patches `RTCPeerConnection` from the page's main world (Manifest V3 isolated worlds cannot see WebRTC objects) to intercept each remote participant's `MediaStreamTrack` *before* the browser mixes them for playback. Each track is routed through its own `AudioWorkletProcessor` (16 kHz mono int16, Silero VAD-gated) and streamed over its own WebSocket to the api process, tagged with the display name resolved from the Meet DOM.

Consequences that shape the whole codebase:
- One WebSocket per speaker per meeting; never a mixed stream.
- Speaker labels come from the DOM, not from voice matching. ECAPA embeddings (F7) are used only for *cross-meeting* recognition, not for live diarization.
- Active-speaker detection is a `MutationObserver` on Meet's CSS classes, not a model.
- If you find yourself reaching for pyannote/Sortformer/WhisperX on the live path, stop — that's the architecture we're explicitly avoiding. Diarization is acceptable only for the post-MVP "uploaded recording" fallback path.

### Architectural commitment 2: meetings are graphs, not transcripts

The transcript is raw input; the **knowledge graph is the product**. Notes, summaries, search, action items, and cross-meeting memory are all projections of the same graph (stored in Postgres tables `graph_nodes` and `graph_edges`). Node types: `Meeting`, `Person`, `Topic`, `Decision`, `ActionItem`, `OpenQuestion`, `Entity`, `Utterance`. Schemas in PRD §8.

Non-negotiable invariants for the graph builder:
- **Grounding.** Every `Decision` / `ActionItem` / `OpenQuestion` MUST have a `SOURCE` edge to a real `Utterance` from the window. Reject LLM output that references unknown utterance IDs.
- **No hallucinated owners.** `ASSIGNED_TO` only when the speech makes ownership explicit.
- **Idempotent dedup.** Before adding a node, embed its text and check cosine similarity (>0.85) against existing nodes of the same type; merge instead of duplicating.
- **Lifecycle states.** Nodes are `provisional` → `confirmed` (stable across windows or affirmed in speech) → `superseded` (contradicted later). The UI renders these differently; do not collapse them.
- **Window cadence.** The aggregator (a TaskIQ task in the worker process) emits a 30-second sliding window every 15 seconds (or earlier if 50 new words arrived). Don't transcribe or extract on every 200ms VAD chunk — that floods the model.

LLM contract for graph extraction is in PRD §9.4. Output is a JSON array of `add_node` / `add_edge` / `update_node` ops, validated through Pydantic before applying transactionally to the `graph_nodes` / `graph_edges` tables.

## Topology

Three processes:

- **`api`** (`uvicorn app.main:app`, in `backend/`) — FastAPI under root path `/api/v1`. REST endpoints, the ingest WebSocket `/meetings/{meeting_id}/streams/{stream_id}` that accepts PCM from the extension, the Swift-worker WebSocket `/asr/sessions` that accepts a registered live-ASR worker, the SSE `/meetings/{id}/events` and the global lifecycle WebSocket `/events/ws` that bridge Redis pub/sub to the UI, and TaskIQ enqueueing. Async only — no blocking work here.
- **`worker`** (`taskiq worker app.tasks:broker`, same backend image) — TaskIQ worker. Owns CPU/GPU/LLM-bound *post-meeting* work: today only `transcribe_final` (faster-whisper). Phase 3+ will add aggregator window emission, graph builder LLM extraction, speaker ID, utterance embedding for RAG.
- **`streamer`** (Swift, in `streamer/`) — Live ASR worker. Connects to the api as a WebSocket client at `/asr/sessions?token=...`, advertises a capacity, and accepts per-speaker audio frames the api forwards to it. Runs Parakeet-TDT v2 via `fluid_audio` (Apple Silicon / CoreML). Emits partial / committed transcript events back over the same WebSocket; the api persists committed segments and republishes everything to the meeting's pub/sub channel. Multiple streamer instances can register; the api round-robins streams by lowest load.

The api and worker import the same Python modules (one Docker image, different `entrypoint.sh` commands — `api` / `worker` / `migrate`). They are NOT separate services with API contracts between them — they are two ways of running the same code. The streamer is a separate codebase with its own protocol over the `/asr/sessions` WebSocket (see `app/asr/schemas.py` and `app/asr/session.py`).

Cross-process communication:
- `api → worker` (post-meeting control): TaskIQ tasks (`task.kiq(...)`), Redis-backed broker.
- `api ↔ streamer` (live audio + live transcript): single WebSocket per streamer connection at `/asr/sessions`. JSON envelopes use the `kind` discriminator with values `hello` / `stream_open` / `stream_close` / `partial` / `final` / `ping` (see `app/asr/constants.EventKind` and `app/asr/schemas.py` — the canonical wire schema, mirrored by `streamer/src/Messages.swift`). The api → streamer direction also carries binary `(stream_idx, seq) + PCM` audio frames (header format `AUDIO_FRAME_HEADER_FMT`). **PCM is never passed as a TaskIQ task argument and never goes through Redis.**
- `worker → api` (and `streamer → api → ui`): Redis pub/sub on `meeting:{meeting_id}:events`. A separate global channel publishes meeting lifecycle events for the directory UI. The api SSE endpoint and the global-events WS endpoint forward to the UI.
- Audio at rest: the api buffers PCM to MinIO in real time via `WavWriter` (`tryniq/meetings/{meeting_id}/streams/{stream_id}.wav`); `transcribe_final` reads from there.

Data lifetime invariant (don't blur this):
- **Postgres** = durable state (utterances, meetings, participants; graph nodes/edges + embeddings in Phase 3+).
- **Redis pub/sub** = ephemeral UI state (partial hypotheses, lifecycle events, transcript segments).
- **Redis key with TTL** = recovery state for late-joining SSE subscribers (`live:partial:{stream_id}`, see `app/meeting/constants.py`).
- **MinIO** = audio at rest + exports.
- **In-process queues on the api** (`asyncio.Queue` per stream, `WorkerSession.audio_queue`) = live PCM in flight to the Swift streamer.

Infra containers (in `backend/compose.yml`):

| Container           | Role                                                                    |
|---------------------|-------------------------------------------------------------------------|
| Postgres + pgvector | Meetings, utterances, participants, graph nodes & edges, embeddings     |
| MinIO               | Per-speaker WAV files; exports                                          |
| Redis               | TaskIQ broker, pub/sub for UI events                                    |
| redis-insight       | Dev-only Redis browser                                                  |

The Swift streamer is **not** containerized — it runs natively on a Mac (CoreML). The graph lives in Postgres in two tables (PRD §8): `graph_nodes(id, meeting_id, type, fields jsonb, status, created_at)` and `graph_edges(id, meeting_id, type, from_id, to_id, created_at)`. (Tables created in Phase 3.)

## Where to find what

Backend (`backend/app/`):
- `main.py` — FastAPI app, lifespan, router registration.
- `config.py` — pydantic-settings root (`config.api`, `.database`, `.minio`, `.redis`, `.asr`).
- `db.py` — async SQLAlchemy engine + `async_session` + `SessionDep`.
- `tasks.py` — shared TaskIQ broker (Redis-backed).
- `meeting/`, `participant/`, `transcript/`, `ingest/` — feature modules with `router.py` (or `routers/` package) / `service.py` / `schemas.py` / `models.py` / `dependencies.py` / `client.py` / `config.py` / `constants.py` / `exceptions.py` as needed. Routers are included from `main.py`.
- `meeting/client.py` — `RedisClient` singleton (`redis_client`): `publish_meeting_event`, `publish_meeting_lifecycle`, `publish_partial_transcript`, `publish_transcript_segment`, `subscribe`, plus the partial cache TTL helpers. Channel/key templates live in `meeting/constants.py`.
- `meeting/routers/event.py` — SSE `/meetings/{id}/events` and global lifecycle WebSocket `/events/ws`.
- `meeting/routers/meeting.py` — REST `/meetings` CRUD.
- `meeting/stream.py` — SSE/WS subscriber plumbing.
- `ingest/router.py` — `/meetings/{meeting_id}/streams/{stream_id}` ingest WebSocket.
- `ingest/service.py` — accepts PCM frames, persists to MinIO via `WavWriter`, forwards to the assigned Swift streamer via `LiveASRClient`. Handles `speaker_renamed`, `discard`, `stream_end` control messages.
- `asr/router.py` — `/asr/sessions` WebSocket where Swift streamers register (auth via `ASR_LIVE_AUTH_TOKEN`).
- `asr/clients/live.py` — `LiveASRClient`: registry of connected `WorkerSession`s, assigns streams to the worker with the lowest load.
- `asr/clients/final.py` — faster-whisper wrapper for the post-meeting refine pass.
- `asr/services/final.py` — `FinalASRService` orchestrating `transcribe_final`.
- `asr/session.py` — `WorkerSession` for one connected Swift streamer (per-stream sender loop, audio frame packing, stream lifecycle).
- `asr/schemas.py` — pydantic events on the `/asr/sessions` socket (`StreamOpenEvent`, `StreamCloseEvent`, transcript events).
- `asr/tasks.py` — `transcribe_final` TaskIQ task only.
- `asr/constants.py` — binary audio frame header layout, queue caps, drop-warn cadence.
- `asr/config.py` — `ASRSettings` (`LIVE_PROVIDER`/`LIVE_MODEL`/`LIVE_AUTH_TOKEN`/idle timeout, `FINAL_*`).
- `core/` — `base_schema.py`, `database.py` mixins, `exceptions.py`, `config.py` (`BASE_MODEL_CONFIG`), `decorators.py`.
- `alembic/` — migrations.
- `CONSTITUTION.md` — mandatory backend code-shape guide; read it before adding files.

Streamer (`streamer/`, Swift 6, single executable target named `streamer`, sources flat in `src/`; **read `streamer/CONSTITUTION.md` before editing**):
- `Package.swift` / `Package.resolved` / `Makefile` / `.env` / `.env.example` at the package root.
- `src/main.swift` — entrypoint: env load → model load → run socket.
- `src/EnvLoader.swift` — `.env` parser (pure `enum`, static methods).
- `src/BackendSocket.swift` — actor: `/asr/sessions` WebSocket lifecycle + reconnect loop.
- `src/SessionManager.swift` — actor: registry of per-stream transcribers; control-message dispatch.
- `src/SpeakerTranscriber.swift` — actor: one speaker's ASR loop (FluidAudio sliding window).
- `src/AsrConfigBuilder.swift` — env → `SlidingWindowAsrConfig` (pure helper).
- `src/TranscriptTiming.swift` — `(t_start, t_end)` derivation from updates (pure helper).
- `src/TranscriptPublisher.swift` — actor: encodes & sends partial/final frames.
- `src/PCMBufferDecoder.swift` — int16 LE bytes → `AVAudioPCMBuffer` Float32 (pure helper).
- `src/BinaryAudioFrame.swift` — 8-byte LE header parser for inbound PCM.
- `src/Messages.swift` — wire-format `Codable` structs only (no logic). Discriminator field is `kind`; values mirror `EventKind` in `backend/app/asr/constants.py` (`hello`, `stream_open`, `stream_close`, `partial`, `final`, `ping`). Field names stay snake_case to match the backend Pydantic models — do not rename via `CodingKeys`.

Hard rule from the streamer constitution: one responsibility per file, **150-line cap per file**, file name == primary type name, no subfolders without precedent.

Frontend (`frontend/`, Next.js 16 App Router + React 19 + TS strict + pnpm; **read `frontend/CONSTITUTION.md` before editing**):
- `src/app/` — Next.js App Router pages. Server Components by default; client islands opt in with `'use client'`. A page that splits server/client uses `page.tsx` (entry) + `<name>-client.tsx`.
- `src/components/` — `ui/` (primitives), `shell/` (app chrome), and one folder per feature (`meeting/`, `people/`, `chat/`, …).
- `src/lib/api/` — typed backend client: `client.ts` (fetch wrapper + `ApiError`), `meetings.ts` (one file per backend feature), `events.ts` (SSE + global WS), `types.ts` (mirrors backend Pydantic, snake_case fields), `adapters.ts` (backend → UI types), `query-client.tsx` (React Query provider), `global-events-provider.tsx` (global lifecycle WS provider).
- `src/lib/config.ts` — centralised env access (`config.apiBaseUrl`). Any new `NEXT_PUBLIC_*` goes here, not `process.env` directly.
- `src/lib/hooks/use-live-transcript.ts` — SSE-driven live transcript state.
- `src/lib/store.ts` (Zustand UI store), `src/lib/types.ts` (UI domain types), `src/lib/format.ts`, `src/lib/utils.ts`.
- `src/lib/mock/` — placeholder data for surfaces the backend does not yet serve (graph, decisions, people directory, chat). Flagged with `TODO(api):` at call sites.

Hard rules from the frontend constitution: path alias `@/*` → `src/*` (never relative `../../`), no `any`, soft cap 200 lines/file, kebab-case filenames, no new top-level folders under `src/`.

Extension (`extension/src/`) — Chrome MV3, TypeScript.

Docs:
- `docs/PRD.md` — source of truth (~1100 lines, section-numbered).

## How to add a new background task

1. Define the task against the shared broker:

   ```python
   # backend/app/asr/tasks.py (or a new module's tasks.py)
   from uuid import UUID

   from app.asr.services.final import FinalASRService
   from app.db import async_session
   from app.tasks import broker

   @broker.task(retry_on_error=True, max_retries=2)
   async def transcribe_final(meeting_id: str, stream_id: str) -> None:
       async with async_session() as session:
           service = FinalASRService(...)
           await service.run(UUID(meeting_id), UUID(stream_id))
   ```

2. Enqueue from an endpoint or another task:

   ```python
   from app.asr.tasks import transcribe_final
   await transcribe_final.kiq(str(meeting_id), str(stream_id))
   ```

   To avoid module-cycle imports, do this as a *local* import inside the function (see `MeetingService._enqueue_finalization`). This pattern is intentional — preserve it.

3. **Never pass large binary data through task arguments.** Pass object keys / row IDs. Tasks must be idempotent — TaskIQ retries on failure.

4. To push UI updates, publish via the `redis_client` helpers instead of raw redis:

   ```python
   from app.meeting.client import redis_client
   await redis_client.publish_meeting_lifecycle(meeting_id, LifecycleEvent.ENDED)
   ```

   The api's SSE and global-WS endpoints forward subscribers automatically.

## Model defaults

Don't swap these without consulting PRD §10:

- **Live ASR:** Parakeet-TDT v2 (`parakeet-tdt-v2`) via the [`fluid_audio`](https://github.com) Swift package, running in the standalone `streamer/` process on Apple Silicon (CoreML). The streamer connects to the api at `/asr/sessions` as a worker; auth via `ASR_LIVE_AUTH_TOKEN`. Multiple streamer instances may register; the api assigns each per-speaker stream to the worker with the lowest current load. There is no Python live-ASR path anymore — earlier Moonshine/`moonshine-voice` and Python streaming code have been removed.
- **Final ASR:** faster-whisper large-v3-turbo, word-level timestamps, language=en (configurable via `ASR_FINAL_*` env). Runs in the TaskIQ worker.
- **VAD:** Silero VAD ONNX (runs in the browser worklet).
- **Speaker embedding:** SpeechBrain ECAPA-TDNN (192-dim). [Phase 5]
- **Graph LLM (default):** Anthropic Claude Haiku 4.5. Self-host alternative: Qwen 2.5 14B Instruct via Ollama/vLLM. [Phase 3]
- **Text embedding:** all-MiniLM-L6-v2 (384-dim, used for both RAG and graph node dedup). [Phase 3+]

The LLM provider must be configurable via `.env` — no hardcoded credentials or external URLs.

## Code-shape guides (binding)

Editing any file under one of these packages requires reading and following the matching constitution first. They cover module layout, imports, naming, file-size caps, concurrency rules, and exception handling — none of that is repeated here.

- **Backend** (`backend/`) → `backend/CONSTITUTION.md`. Highlight: no `from __future__ import annotations` (Python 3.13 is native PEP 604/585/695); local imports between feature modules to avoid cycles.
- **Streamer** (`streamer/`) → `streamer/CONSTITUTION.md`. Highlight: actors for stateful components, pure `enum`s for helpers, 150-line cap per file, wire protocol byte-for-byte compatible with `backend/app/asr/schemas.py`.
- **Frontend** (`frontend/`) → `frontend/CONSTITUTION.md`. Highlight: Server Components default, client islands minimal, types mirror backend Pydantic verbatim.

## Scope discipline

The PRD is opinionated about what's **out of scope** for MVP (§3.2, §15). When tempted to add Zoom/Teams support, multi-language, mobile, multi-tenancy/RBAC/SSO, real-time translation, a "meeting assistant" that talks back, or HA infrastructure — don't. These are signaled to demo reviewers as next steps, not built.

## Risks worth knowing about

From PRD §13, the ones that change how you should write code:

- **R1 — Worker-scope WebRTC.** If Meet routes audio via Workers, the main-world patch alone misses tracks. The extension logs `tryniq.tap.installed { audioTracks }`; if it's 0 in a real call, fall through to a Worker-scope patch (still TODO). Phase 1 acceptance allows the detect-and-defer outcome.
- **R2 — Brittle Meet DOM selectors.** Prefer ARIA roles and stable `data-*` attributes over CSS classes. Always keep a "Speaker N" fallback labeling path with manual rename.
- **R3 — Malformed LLM output.** Pydantic-validate every response, reject unknown utterance IDs, retry once, then skip the window — never corrupt graph state.
- **R8 — Local-mic echo.** The local user's track is flagged `is_local_user: true`; detect and de-duplicate against remote echo.
- **No Swift streamer connected.** If `LiveASRClient` has no registered workers when a stream opens, `assign_stream` returns `None` and the meeting proceeds with WAV capture only — live transcript is silently disabled for that stream. Code paths must handle this gracefully (already do; see `IngestService._assign_swift_worker`).
- **Streamer disconnects mid-meeting.** `WorkerSession.shutdown` tears down all of its assigned streams; the api drops queued PCM. The browser keeps streaming and MinIO persistence is unaffected, so `transcribe_final` can still recover the transcript after meeting end.
- **Worker process crashes mid-task.** TaskIQ retries on the Redis broker; design tasks to be idempotent (check before insert, use stable IDs).

## When in doubt

`docs/PRD.md` is the source of truth on architecture and product scope. The per-package CONSTITUTION.md files (`backend/`, `streamer/`, `frontend/`) are the source of truth on code shape inside each package — read the relevant one before editing. Cite section numbers in commits and PR descriptions when implementing a spec'd feature.
