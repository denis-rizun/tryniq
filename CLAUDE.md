# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository is in **Phase 1 (Capture)**. See `docs/phase-1-spec.md` for the executable spec. Phase 1 builds the Chrome MV3 extension and the minimal `api` process (FastAPI) needed to persist per-speaker WAVs to MinIO. Downstream pipeline modules (ASR, aggregator, graph builder, UI) are deferred.

Runtime: Python **3.13** for the `tryniq` package (broad wheel coverage), Node 20 + pnpm for the extension and UI.

Target demo: 2026-05-11. Phased plan in PRD §14 (Phase 0 setup → Phase 7 demo rehearsal).

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

One Python codebase (`tryniq/`), two process entry points:

- **`api`** — FastAPI app. REST endpoints for meeting CRUD/history, the WebSocket `/ingest` endpoint that accepts PCM from the extension and streams it into MinIO, an SSE endpoint that bridges Redis pub/sub to the UI, and TaskIQ enqueueing. Async only — no blocking work here.
- **`worker`** — TaskIQ worker consuming the Redis-backed task queue. Owns all CPU/GPU/LLM-bound work: live ASR (Moonshine), final ASR (faster-whisper), aggregator window emission, graph builder LLM extraction + node dedup + graph writes, speaker ID (ECAPA), utterance embedding for RAG.

Both processes import the same modules. They are NOT separate services with API contracts between them — they are two ways of running the same code.

Cross-process communication:
- `api → worker`: TaskIQ tasks (`task.kiq(...)`), Redis-backed.
- `worker → api`: Redis pub/sub on channel `meeting:{id}:events`. The api process forwards to the UI via SSE.
- Audio: api writes PCM to MinIO; worker reads from MinIO by path. **PCM bytes are never passed as task arguments — only object paths and IDs.**

Infra containers (not our code):

| Container | Role |
|---|---|
| Postgres + pgvector | Meetings, utterances, graph nodes & edges, embeddings, speaker profiles |
| MinIO | Per-speaker WAV files; exports |
| Redis | TaskIQ broker AND pub/sub for UI events |
| Ollama (optional) | Local LLM for graph extraction |
| ui (Next.js) | Frontend, separate package |

State stores: **Postgres** (utterances, metadata, graph nodes/edges) + **pgvector** (RAG and topic embeddings) + **MinIO** (audio + exports). Redis is treated as ephemeral.

The graph lives in Postgres in two tables (PRD §8): `graph_nodes(id, meeting_id, type, fields jsonb, status, created_at)` and `graph_edges(id, meeting_id, type, from_id, to_id, created_at)`.

## Where to find what

- `src/tryniq/api/` — FastAPI app, REST endpoints, WS handlers, SSE.
- `src/tryniq/tasks/` — TaskIQ task definitions (`broker = ...`, `@broker.task` functions).
- `src/tryniq/pipeline/` — `asr_live`, `asr_final`, `aggregator`, `graph_builder`, `speaker_id`. Pure modules called from tasks.
- `src/tryniq/storage/` — `pg.py`, `minio.py`, `redis.py` clients.
- `src/tryniq/llm/` — provider abstraction (Anthropic / Ollama / vLLM).
- `src/tryniq/models/` — Pydantic schemas (WS init, lifecycle, graph ops).
- `src/tryniq/config.py` — pydantic-settings, all from env.
- `extension/src/` — Chrome MV3 extension (TS).
- `ui/` — Next.js frontend, separate package.
- `infra/postgres/init.sql` — schema bootstrap.

## How to add a new background task

1. Define the task in `src/tryniq/tasks/` against the shared broker:

   ```python
   from tryniq.tasks import broker
   from tryniq.pipeline import asr_final

   @broker.task
   async def transcribe_final(meeting_id: str, stream_id: str, object_key: str) -> None:
       # worker reads audio from MinIO using object_key, writes results to Postgres,
       # then publishes a Redis pub/sub event on meeting:{meeting_id}:events
       await asr_final.run(meeting_id, stream_id, object_key)
   ```

2. Enqueue from an API endpoint or another task:

   ```python
   from tryniq.tasks.transcribe import transcribe_final
   await transcribe_final.kiq(meeting_id, stream_id, object_key)
   ```

3. **Never pass large binary data through task arguments.** Pass object keys / row IDs and have the worker read from MinIO or Postgres. Tasks must be idempotent — TaskIQ retries on failure.

4. To push UI updates from a task, publish to Redis: `await redis.publish(f"meeting:{meeting_id}:events", json.dumps(payload))`. The api's SSE endpoint forwards subscribers automatically.

## Model defaults

Don't swap these without consulting PRD §10:

- **Live ASR:** Moonshine-base (Moonshine-tiny on CPU-constrained dev boxes).
- **Final ASR:** faster-whisper large-v3, word-level timestamps, language=en.
- **VAD:** Silero VAD ONNX (runs in the browser worklet).
- **Speaker embedding:** SpeechBrain ECAPA-TDNN (192-dim).
- **Graph LLM (default):** Anthropic Claude Haiku 4.5. Self-host alternative: Qwen 2.5 14B Instruct via Ollama/vLLM.
- **Text embedding:** all-MiniLM-L6-v2 (384-dim, used for both RAG and graph node dedup).

The LLM provider must be configurable via `.env` — no hardcoded credentials or external URLs.

## Scope discipline

The PRD is opinionated about what's **out of scope** for MVP (§3.2, §15). When tempted to add Zoom/Teams support, multi-language, mobile, multi-tenancy/RBAC/SSO, real-time translation, a "meeting assistant" that talks back, or HA infrastructure — don't. These are signaled to demo reviewers as next steps, not built.

## Risks worth knowing about

From PRD §13, the ones that change how you should write code:

- **R1 — Worker-scope WebRTC.** If Meet routes audio via Workers, the main-world patch alone misses tracks. Inject into Worker scope too. Resolve in Phase 1.
- **R2 — Brittle Meet DOM selectors.** Prefer ARIA roles and stable `data-*` attributes over CSS classes. Always keep a "Speaker N" fallback labeling path with manual rename.
- **R3 — Malformed LLM output.** Pydantic-validate every response, reject unknown utterance IDs, retry once, then skip the window — never corrupt graph state.
- **R8 — Local-mic echo.** The local user's track is flagged `is_local_user: true`; detect and de-duplicate against remote echo.
- **Worker process crashes mid-task.** TaskIQ retries on the Redis broker; design tasks to be idempotent (check before insert, use stable IDs).

## When in doubt

`docs/PRD.md` is the source of truth. It is comprehensive (1100+ lines) and section-numbered — cite section numbers in commits and PR descriptions when implementing a spec'd feature.
