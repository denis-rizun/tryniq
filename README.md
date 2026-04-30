# Tryniq

> Codename **Synapse** — an open-source, self-hostable meeting intelligence platform. A tl;dv replacement built around per-speaker audio capture and a graph-based memory layer.

## What makes it different

Most notetakers receive a mixed audio stream and rely on diarization models to guess who said what. Tryniq doesn't.

- **Per-speaker audio via WebRTC tap.** A Chrome extension monkey-patches `RTCPeerConnection` from the page's main world to intercept each participant's `MediaStreamTrack` *before* the browser mixes them. Each speaker gets their own WebSocket, their own ASR pass, and their display name straight from the Meet DOM. Diarization is solved architecturally, not algorithmically.
- **Meetings as graphs, not transcripts.** Topics, decisions, action items, open questions, and entities are typed nodes in a Kuzu graph, each grounded to the source utterance. Notes, summaries, search, and cross-meeting memory are projections of the same graph.

## Capabilities (MVP)

- Live transcription with sub-3s latency (Moonshine-base) and post-meeting refinement (faster-whisper large-v3).
- Live-updating knowledge graph with Cytoscape visualization and structured Markdown notes.
- Cross-meeting speaker memory via ECAPA-TDNN voice embeddings.
- Cross-meeting topic linking via text embeddings.
- "Chat with the meeting" RAG over transcripts with cited timestamps.
- Markdown export for Notion / wiki / tickets.
- Single `make up` brings up the whole stack via Docker Compose.

## Stack

Chrome MV3 extension (TS + Vite) → FastAPI gateway → NATS JetStream → ASR / aggregator / graph-builder / speaker-id workers → Postgres + pgvector + Kuzu + MinIO → Next.js UI.

LLM defaults to Anthropic Claude Haiku 4.5 with a self-host fallback to Qwen 2.5 14B via Ollama/vLLM. All other models run locally.

## Status

Pre-implementation — see [`docs/PRD.md`](docs/PRD.md) for the full product requirements. Target demo: 2026-05-11.
