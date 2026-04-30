# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository is at the **pre-implementation stage**. The only artifacts are `docs/PRD.md` (the source of truth), an empty `pyproject.toml` (Python ≥3.14, no deps yet), and an empty `README.md`. There is no code, no Makefile, no docker-compose.yml, no extension scaffold yet — when these are added, this file should be updated with the actual build/lint/test commands.

The codename in the PRD is **Synapse**; the repo is named **tryniq**. Treat them as the same project.

Target demo: 2026-05-11. Phased plan in PRD §14 (Phase 0 setup → Phase 7 demo rehearsal).

## What this project is

An open-source, self-hostable meeting intelligence platform — a tl;dv replacement — built around two non-obvious architectural commitments. Read PRD §5 before making any non-trivial design decision; the rest of the system is downstream of these two ideas.

### Architectural commitment 1: per-speaker audio via WebRTC tap

**We do not run speaker diarization on the live path.** A Chrome extension monkey-patches `RTCPeerConnection` from the page's main world (Manifest V3 isolated worlds cannot see WebRTC objects) to intercept each remote participant's `MediaStreamTrack` *before* the browser mixes them for playback. Each track is routed through its own `AudioWorkletProcessor` (16 kHz mono int16, Silero VAD-gated) and streamed over its own WebSocket to the gateway, tagged with the display name resolved from the Meet DOM.

Consequences that shape the whole codebase:
- One WebSocket per speaker per meeting; never a mixed stream.
- Speaker labels come from the DOM, not from voice matching. ECAPA embeddings (F7) are used only for *cross-meeting* recognition, not for live diarization.
- Active-speaker detection is a `MutationObserver` on Meet's CSS classes, not a model.
- If you find yourself reaching for pyannote/Sortformer/WhisperX on the live path, stop — that's the architecture we're explicitly avoiding. Diarization is acceptable only for the post-MVP "uploaded recording" fallback path.

### Architectural commitment 2: meetings are graphs, not transcripts

The transcript is raw input; the **knowledge graph is the product**. Notes, summaries, search, action items, and cross-meeting memory are all projections of the same Kuzu graph. Node types: `Meeting`, `Person`, `Topic`, `Decision`, `ActionItem`, `OpenQuestion`, `Entity`, `Utterance`. Schemas in PRD §8.

Non-negotiable invariants for the graph builder:
- **Grounding.** Every `Decision` / `ActionItem` / `OpenQuestion` MUST have a `SOURCE` edge to a real `Utterance` from the window. Reject LLM output that references unknown utterance IDs.
- **No hallucinated owners.** `ASSIGNED_TO` only when the speech makes ownership explicit.
- **Idempotent dedup.** Before adding a node, embed its text and check cosine similarity (>0.85) against existing nodes of the same type; merge instead of duplicating.
- **Lifecycle states.** Nodes are `provisional` → `confirmed` (stable across windows or affirmed in speech) → `superseded` (contradicted later). The UI renders these differently; do not collapse them.
- **Window cadence.** Aggregator emits a 30-second sliding window every 15 seconds (or earlier if 50 new words arrived). Don't transcribe or extract on every 200ms VAD chunk — that floods the model.

LLM contract for graph extraction is in PRD §9.4. Output is a JSON array of `add_node` / `add_edge` / `update_node` ops, validated through Pydantic before applying transactionally to Kuzu.

## Service topology

Single Docker Compose stack (no k8s, no service mesh — production hardening is post-MVP). Inter-service comms is **NATS JetStream** (JSON payloads). Browser↔Gateway is WebSocket. Backend→UI is SSE for live, REST for historical.

Services (per PRD §7.2 and §17.2):

| Service                   | Stack                         | Stateful?              |
|---------------------------|-------------------------------|------------------------|
| `extension/`              | Chrome MV3 + TS + Vite        | No                     |
| `services/gateway/`       | FastAPI                       | Writes to MinIO + NATS |
| `services/asr-live/`      | Moonshine-base                | No                     |
| `services/asr-final/`     | faster-whisper large-v3       | No                     |
| `services/aggregator/`    | —                             | Postgres               |
| `services/graph-builder/` | LLM client                    | Kuzu                   |
| `services/speaker-id/`    | SpeechBrain ECAPA-TDNN        | Postgres + pgvector    |
| `ui/`                     | Next.js + Cytoscape + Zustand | No                     |

State stores: **Postgres** (utterances, metadata) + **pgvector** (RAG and topic embeddings) + **Kuzu** (graph) + **MinIO** (audio + exports).

NATS subjects (PRD §9.2): `audio.{meeting}.{stream}`, `transcript.{meeting}`, `timeline.{meeting}.window`, `graph.{meeting}.patch`, `meeting.lifecycle`.

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

## When in doubt

`docs/PRD.md` is the source of truth. It is comprehensive (1100+ lines) and section-numbered — cite section numbers in commits and PR descriptions when implementing a spec'd feature.
