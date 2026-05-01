# Tryniq — Product Requirements Document

> **An open-source meeting intelligence platform that replaces tl;dv with a graph-based memory layer and architecturally clean per-speaker audio capture.**

| Field                 | Value                                              |
|-----------------------|----------------------------------------------------|
| **Document version**  | 1.0                                                |
| **Status**            | Draft for hackathon kickoff                        |
| **Last updated**      | 2026-04-30                                         |
| **Target demo date**  | 2026-05-11, 16:00                                  |
| **Project codename**  | Tryniq                                            |
| **Document owner**    | Engineering team                                   |
| **Related challenge** | Open Voice Notetaker Challenge — tl;dv replacement |

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Problem statement](#2-problem-statement)
3. [Goals and non-goals](#3-goals-and-non-goals)
4. [User personas and stories](#4-user-personas-and-stories)
5. [Core architectural insight](#5-core-architectural-insight)
6. [Feature specifications](#6-feature-specifications)
7. [System architecture](#7-system-architecture)
8. [Data model](#8-data-model)
9. [Internal contracts](#9-internal-contracts)
10. [Model selection and comparison](#10-model-selection-and-comparison)
11. [User experience and interface](#11-user-experience-and-interface)
12. [Success metrics](#12-success-metrics)
13. [Risks and mitigations](#13-risks-and-mitigations)
14. [Phased delivery plan](#14-phased-delivery-plan)
15. [Out of scope](#15-out-of-scope)
16. [Open questions](#16-open-questions)
17. [Appendix](#17-appendix)

---

## 1. Executive summary

Tryniq is an open-source meeting intelligence platform designed to replace tl;dv inside the company. Unlike traditional notetakers that produce flat text transcripts and bullet-list summaries, Tryniq is built around two fundamental architectural decisions that set it apart from every existing competitor:

**First, Tryniq captures audio per-speaker, in clean isolated streams, by intercepting WebRTC tracks inside the browser before they are mixed for playback.** This is achieved through a Chrome extension that monkey-patches `RTCPeerConnection` from the page's main world. The result is that every other team's hardest problem — speaker diarization — is solved architecturally rather than algorithmically. We don't need pyannote, Sortformer, or any diarization model for the live path, because we never receive a mixed stream.

**Second, Tryniq models a meeting as a live knowledge graph rather than as a transcript.** Speakers, topics, decisions, action items, open questions, and entities become nodes connected by typed edges. The transcript is the raw input; the graph is the product. Notes, summaries, search, action items, and cross-meeting memory are all projections of the same graph. This makes Tryniq a foundation for an organizational knowledge graph fed by meetings, rather than a single-meeting summarization tool.

The MVP delivers a working Chrome extension for Google Meet, an end-to-end pipeline for live and post-meeting transcription using Moonshine and faster-whisper, a real-time graph builder powered by structured-output LLM extraction, a web UI with synchronized transcript and graph visualization, cross-meeting speaker memory via ECAPA-TDNN embeddings, topic linking between meetings, retrieval-augmented question answering over completed meetings, and full export to Markdown.

Everything is open-source and self-hostable. The only optional cloud dependency is the LLM for graph extraction, which can be swapped for a local Qwen 2.5 model.

---

## 2. Problem statement

### 2.1 The category problem

Meeting notetakers as a category have converged on a similar shape: a bot joins the call, records mixed audio, runs Whisper or a hosted ASR, runs a diarization model, hands the transcript to an LLM, and produces a summary with bullet-point action items. This shape has three structural weaknesses.

**Diarization is fundamentally unreliable.** Every existing tool depends on it, and every existing tool produces visibly bad speaker attribution on overlapping speech, similar voices, short utterances, and noisy audio. Action items get assigned to the wrong person. Quotes get misattributed in summaries. Users learn not to trust speaker labels, which silently kills the value of the entire feature.

**Flat text loses structure.** A meeting is a structured event — topics, decisions, questions, blockers, owners, due dates, references to past discussions. Reducing it to "transcript plus summary" discards almost all of that structure. The result is that searching old meetings, finding when a decision was made, or understanding which question is still open requires re-reading.

**Meetings exist in isolation.** Most tools treat each meeting as an island. There is no memory of who works on what, no awareness that "the deploy issue" was discussed three weeks ago, no continuity. Every summary starts from scratch.

### 2.2 The internal problem

The company currently uses tl;dv. The challenge brief explicitly calls out that we want to replace it with something we own, can self-host, can extend, and can integrate with internal systems. The brief penalizes naive solutions ("just record audio and run Whisper") and rewards architectural clarity, model research depth, diarization quality, active speaker detection, and demonstration of a system that could plausibly become a real internal product.

### 2.3 What success looks like

A reviewer watching the demo should walk away with three impressions:

- "They solved diarization differently than everyone else, and it works."
- "The graph view is a genuinely new shape for meeting data, not just a prettier summary."
- "This could be the foundation of our internal meeting platform — not a hackathon project."

---

## 3. Goals and non-goals

### 3.1 Goals (MVP, by 2026-05-11)

- **G1** — Capture clean per-speaker audio from a live Google Meet session via Chrome extension, with each speaker's display name resolved automatically from the DOM.
- **G2** — Produce a live transcript with sub-3-second latency from speech to text appearing in the UI, with correct speaker attribution.
- **G3** — Refine the live transcript into a high-accuracy final transcript after the meeting ends, using a stronger ASR model on the full per-speaker audio.
- **G4** — Build and visualize a meeting knowledge graph in real time, containing topics, decisions, action items, open questions, and entities, with grounding to source utterances.
- **G5** — Persist speaker identity across meetings via voice embeddings, so a person met in meeting N is recognized in meeting N+1 without re-introduction.
- **G6** — Link topics across meetings, so a recurring discussion is visibly connected to its history.
- **G7** — Allow post-meeting question answering ("Chat with the meeting") via retrieval over the transcript, with timestamped citations.
- **G8** — Export a structured Markdown summary of any meeting, suitable for pasting into a wiki or ticket.
- **G9** — Run entirely on a self-hostable stack with a single `make up` command.
- **G10** — Produce honest, comparative model evaluation across at least three ASR options on shared test recordings.

### 3.2 Non-goals for MVP

- **NG1** — Zoom and Microsoft Teams support. Architecture supports it; implementation is post-MVP.
- **NG2** — Bot-based capture (joining a meeting as a participant). Reserved for v2; the same Chrome extension will run inside a headless Chrome controlled by Puppeteer.
- **NG3** — Multi-language support. English only.
- **NG4** — Mobile applications.
- **NG5** — Multi-tenancy, organization-level RBAC, enterprise SSO. Single-team prototype only.
- **NG6** — Speech-to-speech models (Moshi, etc.). Out of category.
- **NG7** — Real-time translation.
- **NG8** — A "meeting assistant" that participates in the conversation. Tryniq listens; it does not speak.

### 3.3 Long-term goals (post-MVP, signaled in demo)

- **L1** — Headless-Chrome bot deployment, so the same extension runs without a human present.
- **L2** — Cross-platform support (Zoom, Teams).
- **L3** — Live in-meeting interventions ("Mike asked a question 2 minutes ago and no one answered").
- **L4** — Organization-wide knowledge graph fed by all meetings, with privacy controls.
- **L5** — Integrations: Slack notifications, Linear/Jira ticket creation from action items, calendar-based meeting auto-discovery.

---

## 4. User personas and stories

### 4.1 Primary personas

**Persona A — Anna, the engineering manager.** Runs five to eight meetings per week. Needs to remember what was decided, who owns what, and what is still open. Currently uses tl;dv but does not trust the speaker labels and rewrites summaries by hand.

**Persona B — Mike, the engineer.** Joins meetings he wasn't fully present for and needs to know what happened. Currently scrubs through tl;dv recordings or asks colleagues. Reads transcripts maybe once a month.

**Persona C — Sarah, the product lead.** Cares about decision continuity across meetings. Wants to know when "the auth refactor" was last discussed, who pushed back, and what was concluded. Currently maintains a manual decision log.

### 4.2 Core user stories

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-1 | meeting host | install a browser extension and start recording with one click | I don't have to invite a bot or change my workflow |
| US-2 | participant | see who is speaking labeled correctly in real time | I trust the transcript |
| US-3 | meeting host | get a structured summary with decisions, action items, and open questions | I don't have to write notes by hand |
| US-4 | meeting host | see action items with explicit owners and due dates | tasks don't get lost |
| US-5 | participant | jump from any decision in the summary to the exact moment it was said | I can verify context quickly |
| US-6 | participant | be recognized automatically across meetings without re-tagging my voice | the system feels like it remembers people |
| US-7 | product lead | see when a topic was last discussed and link to the previous meeting | I have continuity |
| US-8 | engineer | ask a natural-language question about a meeting I missed | I can catch up in 30 seconds |
| US-9 | meeting host | export a meeting summary as Markdown to paste into Notion or a wiki | the data is portable |
| US-10 | platform owner | run the entire stack on my own infrastructure | meeting audio never leaves the company |
| US-11 | meeting host | correct a mis-attributed speaker name during the meeting | downstream artifacts are accurate |
| US-12 | engineer | edit transcript text after the meeting and have the graph re-extract | I can fix ASR errors without losing structure |

---

## 5. Core architectural insight

This section exists because it is the single most important idea in the project and must be communicated in the demo. Everything else follows from it.

### 5.1 The standard approach (what we are not doing)

Conventional notetakers receive a single mixed audio stream containing all participants. They then run a diarization model (pyannote, Sortformer, WhisperX) to separate speakers, attempt to assign labels, and produce a transcript with speaker tags. Diarization is the bottleneck for quality, the source of most user-facing errors, and the hardest part of the pipeline to improve.

### 5.2 The Tryniq approach

Inside a Google Meet browser tab, audio is delivered through `RTCPeerConnection` objects. Each remote participant arrives as a separate `MediaStreamTrack` of kind `audio`, with its own SSRC and track ID, before any client-side mixing. The browser only mixes these streams at the final playback step.

Tryniq intercepts these tracks at the source. A content script injects a script into the page's main world (Manifest V3 isolated worlds cannot see WebRTC objects), which monkey-patches `RTCPeerConnection.prototype.addTrack` and the `track` event. Each incoming audio track is routed into a separate `AudioWorkletProcessor`, downsampled to 16kHz, gated through Silero VAD, and streamed over a dedicated WebSocket to the api process, tagged with the speaker's display name resolved from the participant tile in the DOM.

### 5.3 Consequences

- **Diarization is not needed for the live path.** Each WebSocket carries a single speaker's audio. There is no mixed stream to separate.
- **Speaker identity is free.** Display names come from the DOM — they are the names participants entered when joining the meeting. No voice-print matching is required to label them.
- **Active speaker detection is free.** Google Meet already adds a CSS class to the actively speaking participant's tile. A `MutationObserver` reports it.
- **Audio quality is higher.** Each stream contains only one voice, so ASR has no cross-talk to fight through.
- **Overlapping speech is handled correctly.** When two people talk simultaneously, both streams are transcribed in parallel.
- **The bot deployment path remains open.** A headless Chrome instance loaded with the same extension (post-MVP) gets the same per-speaker streams the user does, because WebRTC delivers them whether or not the browser is rendering UI.

### 5.4 Tradeoffs we accept

- **Distribution requires extension installation.** This is acceptable for an internal company tool where extensions can be deployed via MDM. It is also resolvable post-MVP via the bot path.
- **Selectors against Google Meet's DOM are brittle.** We mitigate by preferring ARIA roles and stable `data-*` attributes over CSS classes, and by maintaining a fallback labeling scheme (Speaker 1, Speaker 2) with manual rename in the UI.
- **The pipeline is browser-bound.** Native desktop apps would offer system-level audio capture, but at the cost of OS-specific code, app installation friction, and worse audio quality (mixed system audio).

---

## 6. Feature specifications

This section enumerates every feature in the MVP, with detailed behavior, acceptance criteria, and dependencies.

### 6.1 F1 — Browser extension capture

**Description.** A Chrome extension (Manifest V3) that activates on `meet.google.com` URLs. Users see a popup with a Start/Stop recording button, a connection-status indicator, and a participant list with current speaker highlighted.

**Behavior.**
- On page load, the content script injects a main-world script that monkey-patches `RTCPeerConnection`.
- When the user clicks "Start recording", the extension begins streaming all currently-active audio tracks plus future tracks as they appear.
- For each track, a separate `AudioContext` and `AudioWorkletNode` resamples to 16 kHz mono int16 PCM.
- Silero VAD (loaded as ONNX in the worklet) gates the stream — audio is sent only when the model reports speech, with a 200ms pre-roll to capture leading consonants.
- A separate WebSocket per track is opened to the api process, beginning with an `init` message and continuing with binary PCM frames.
- A `MutationObserver` on the participant container resolves track IDs to display names and detects active-speaker class changes.
- On "Stop recording" or page unload, all streams emit `stream_end` and the meeting is marked ended on the backend.

**Acceptance criteria.**
- A two-person Meet produces exactly two WebSocket streams in the api, each containing only one voice when saved as WAV.
- The local user's microphone is captured on a track flagged `is_local_user: true`.
- Display names appear correctly in the api logs within 2 seconds of a participant joining.
- The extension survives mid-meeting participant joins/leaves without restart.
- The extension recovers gracefully if a WebSocket drops, with exponential backoff reconnect.

**Out of scope for F1.** Zoom, Teams, video capture, screen-share capture.

---

### 6.2 F2 — Live transcription

**Description.** A streaming ASR pipeline (running as a TaskIQ task in the worker process) transcribes incoming audio per-speaker with low latency, producing transcript segments visible in the UI within 1–3 seconds of speech.

**Behavior.**
- The api process accumulates PCM frames per stream into MinIO and enqueues a `transcribe_live(meeting_id, stream_id, object_key, t_start, t_end)` task at each VAD speech-end (or every 3 s of continuous speech).
- The worker reads the audio segment from MinIO, transcribes it, and writes utterances to Postgres. We do not transcribe every 200ms chunk — that floods the model.
- Moonshine-base (or Moonshine-tiny on CPU-constrained environments) is the live model.
- Each transcript segment is published with `is_final: false`, indicating it may be revised by the post-meeting pass.
- Segments include word-level timestamps where the model supports them.

**Acceptance criteria.**
- End-to-end latency from speech to UI display is under 3 seconds at the 95th percentile on a developer laptop.
- Word error rate on a clean English test recording is under 12% with Moonshine-base.
- Multiple speakers transcribed in parallel without interference.

**Dependencies.** F1.

---

### 6.3 F3 — Post-meeting transcription refinement

**Description.** After the meeting ends, a final-quality ASR pass runs on each speaker's full audio using faster-whisper large-v3, replacing live segments with refined versions.

**Behavior.**
- On `POST /meetings/{id}/end`, the api enqueues a `transcribe_final(meeting_id, stream_id)` task per stream.
- The worker loads audio from MinIO (object storage), where the api has been persisting it during the meeting.
- faster-whisper large-v3 runs with word-level timestamps, language=en.
- Resulting segments are matched to existing live segments by time-overlap and replace them in Postgres.
- The graph builder task is re-run on the full refined transcript to produce a cleaner final graph.
- The UI receives a `transcript_finalized` event and switches display to the final version, with a toggle to view the live version for comparison.

**Acceptance criteria.**
- A 30-minute meeting completes final transcription within 5 minutes on GPU or 15 minutes on CPU.
- Final transcript word error rate is at least 30% lower than the live transcript on the same audio.
- Speaker attribution is preserved (because the per-speaker audio files are already separated).

**Dependencies.** F1, F2.

---

### 6.4 F4 — Meeting knowledge graph

**Description.** A live-updating knowledge graph extracted from the transcript by an LLM, containing typed nodes and edges. This is the central differentiator of Tryniq.

**Node types.** `Meeting`, `Person`, `Topic`, `Decision`, `ActionItem`, `OpenQuestion`, `Entity`, `Utterance`. Full schema in section 8.

**Edge types.** `PARTICIPATED_IN`, `DISCUSSED_IN`, `MADE_DECISION`, `ASSIGNED_TO`, `BLOCKS`, `ABOUT`, `MENTIONS`, `SOURCE`, `RELATES_TO`. Full schema in section 8.

**Behavior.**
- The aggregator (a periodic TaskIQ task in the worker process) emits a sliding window of the last 30 seconds of transcript every 15 seconds, or earlier if 50 new words have been added, by enqueueing a `build_graph(meeting_id, window)` task.
- The graph builder task sends the window plus a summary of the existing graph to an LLM with a structured-output prompt.
- The LLM returns a JSON array of graph operations: `add_node`, `add_edge`, `update_node`.
- Operations are validated against a Pydantic schema and applied to the Postgres `graph_nodes` / `graph_edges` tables in a transaction.
- A graph patch is published to Redis on `meeting:{id}:events`; the api forwards it to the UI over Server-Sent Events.
- Idempotency: before adding a node, the builder computes a text embedding and checks similarity (cosine > 0.85) with existing nodes of the same type. If similar, it merges instead of duplicating.
- Every `Decision`, `ActionItem`, and `OpenQuestion` node MUST have a `SOURCE` edge to the `Utterance` it was extracted from. This is non-negotiable — it is the grounding mechanism that prevents hallucination and enables jump-to-time.

**Node lifecycle.** Each extractable node has a status: `provisional` (LLM proposed, low confidence), `confirmed` (stable across windows or explicitly affirmed in speech), `superseded` (contradicted later in the meeting). The UI renders these differently.

**Acceptance criteria.**
- Across a 10-minute test meeting with scripted decisions and action items, precision and recall on extracted decisions are both above 70%.
- Every extracted decision links to a real utterance.
- Duplicate nodes do not appear when the same topic is discussed across multiple windows.
- The graph builder task recovers from LLM failures (timeout, malformed JSON) without corrupting state — failed windows are retried via TaskIQ or skipped, and the meeting continues.

**Dependencies.** F2.

---

### 6.5 F5 — Live graph visualization

**Description.** A Cytoscape-based visual graph rendered alongside the transcript, updating in real time as nodes and edges are added.

**Behavior.**
- Frontend subscribes to graph patches via SSE.
- A Zustand store holds the local graph state and applies patches incrementally.
- Cytoscape.js renders the graph with a force-directed layout (cose-bilkent).
- Nodes are color-coded by type: Topic blue, Decision green, ActionItem yellow, OpenQuestion orange, Person gray, Entity purple.
- Status is rendered visually: `provisional` is dashed outline, `confirmed` is solid, `superseded` is gray with strikethrough.
- Clicking a node opens a side panel with full content, source utterance(s), and a "Jump to time" link that scrolls the transcript to the matching moment.
- A timeline scrubber at the bottom lets users replay the graph as it grew, useful for understanding meeting flow.

**Acceptance criteria.**
- Layout remains readable up to 100 nodes.
- Patches apply within 200ms of receipt.
- Clicking a node successfully jumps the transcript view to the source utterance.

**Dependencies.** F4.

---

### 6.6 F6 — Structured notes panel

**Description.** A Markdown-rendered, structured view of the meeting derived from the graph. This is what users will copy-paste into Notion or a ticket.

**Behavior.**
- Renders sections: Topics, Decisions, Action Items (grouped by owner), Open Questions, Participants, Related past meetings.
- Each section is a projection of corresponding graph nodes.
- Action items show owner, deadline (if extracted), and source link.
- Open questions are visually flagged if unanswered (no `answered: true` in the meeting).
- Decisions show who proposed them and when.
- Updates live as the graph grows.

**Acceptance criteria.**
- All extracted nodes appear in the appropriate section.
- Owner-less decisions and action items are visibly flagged.
- Markdown copy-to-clipboard reproduces the panel content faithfully.

**Dependencies.** F4.

---

### 6.7 F7 — Speaker memory across meetings

**Description.** Persistent voice-print embeddings allow speakers to be recognized across meetings without manual tagging.

**Behavior.**
- After a meeting ends, the api enqueues a `compute_speaker_embeddings(meeting_id)` task. For each speaker the worker extracts ~30 seconds of clean audio from MinIO and computes an ECAPA-TDNN embedding.
- The embedding is stored in Postgres with a foreign key to the `Person` node, keyed by display name.
- When a new meeting starts and a new track appears with a previously-unknown name, a `match_speaker(stream_id)` task computes a temporary embedding and queries the database for nearest neighbor (cosine similarity).
- If a match exists with similarity > 0.7, the system flags this as "this voice matches Sarah Chen from previous meetings" and offers to link the identities.
- Manual override is always available.

**Acceptance criteria.**
- Across two test meetings with the same three participants, all three speakers are auto-recognized in meeting 2.
- False positive rate (recognizing a different speaker as a known one) is below 5% on a small test set.
- Embeddings are updated incrementally as more audio of a person is collected.

**Dependencies.** F1, F3.

---

### 6.8 F8 — Cross-meeting topic linking

**Description.** Topics discussed in a current meeting are automatically linked to similar topics from past meetings, building a continuity layer.

**Behavior.**
- Each `Topic` node has an embedding computed from its title and summary.
- When a new topic is created, the graph builder task queries pgvector for nearest neighbors (cosine similarity > 0.8) among all historical topics.
- Matches are connected via `RELATES_TO` edges.
- The notes panel surfaces this as "Related discussion from [date]" with a link to the previous meeting.
- The graph view shows ghosted nodes from past meetings as faded outlines, clickable to open the historical context.

**Acceptance criteria.**
- A topic discussed in meeting 1 and re-raised in meeting 2 is linked automatically.
- The link is surfaced in both the graph view and the notes panel.
- Cross-meeting links do not pollute the current meeting's graph (rendered as separate visual layer).

**Dependencies.** F4, F7.

---

### 6.9 F9 — Chat with the meeting

**Description.** Post-meeting natural-language question answering over the transcript, with cited sources and timestamps.

**Behavior.**
- After meeting end, all utterances are embedded and stored in pgvector.
- The UI exposes a "Ask about this meeting" input.
- Queries are processed by retrieving the top 5 most relevant utterances and passing them to an LLM with a structured prompt.
- Responses include inline citations to the source utterances, rendered as clickable timestamps.
- Clicking a citation jumps the transcript to that moment.
- Queries can also reference graph nodes ("when did we decide to roll back?" → grounded in the Decision node and its source utterance).

**Acceptance criteria.**
- A factual question about a topic explicitly discussed yields an answer with at least one correct citation.
- Citations are clickable and accurate.
- The system declines to answer when the meeting does not contain relevant information ("I couldn't find this discussed in the meeting").

**Dependencies.** F3, F4.

---

### 6.10 F10 — Open question detection

**Description.** Questions raised in the meeting that go unanswered are detected and flagged.

**Behavior.**
- The graph builder identifies `OpenQuestion` nodes during extraction.
- A node is considered answered if a subsequent utterance is determined to address it (via LLM judgment in a follow-up window).
- If a question remains unanswered for more than 2 minutes of meeting time, the UI surfaces a soft notification: "This question hasn't been addressed."
- In the post-meeting summary, unanswered questions are listed prominently.

**Acceptance criteria.**
- A scripted unanswered question is correctly flagged in test meetings.
- Answered questions are not falsely flagged.
- Notifications are unobtrusive (no modals, just a subtle UI signal).

**Dependencies.** F4.

---

### 6.11 F11 — Owner-less decision warnings

**Description.** Decisions made without a clear owner for execution are flagged for follow-up.

**Behavior.**
- When a `Decision` node is created without an `ASSIGNED_TO` edge to a `Person`, it is flagged in the notes panel.
- The graph view renders such nodes with a red border.
- The Markdown export includes a dedicated "⚠️ Decisions without owners" section if any exist.

**Acceptance criteria.**
- Decisions explicitly assigned to a person ("Mike will handle that") are not flagged.
- Decisions without explicit ownership ("we should roll back") are flagged.

**Dependencies.** F4.

---

### 6.12 F12 — Confidence-aware transcript

**Description.** Words with low ASR confidence are visually distinguished, so users know what to verify.

**Behavior.**
- The final ASR pass returns word-level confidence scores from faster-whisper.
- In the UI, words with confidence < 0.5 are rendered in a lighter gray.
- Hovering shows the confidence value.
- The graph builder receives confidence in its prompt and is instructed not to extract decisions or action items based primarily on low-confidence text.

**Acceptance criteria.**
- Low-confidence words are visually distinct.
- Graph extraction stability improves on noisy audio because the LLM sees confidence signals.

**Dependencies.** F3.

---

### 6.13 F13 — Inline transcript editing

**Description.** Users can edit transcript text after the meeting; corrections are persisted and the graph re-extracts.

**Behavior.**
- After meeting end, transcript text becomes editable in the UI.
- Saving an edit updates the `Utterance` record in Postgres and triggers a localized graph re-extraction over the affected window.
- Speaker labels can also be corrected via dropdown.
- A change history is preserved for audit.

**Acceptance criteria.**
- Edits persist across page reloads.
- Graph nodes derived from edited text update accordingly.
- Edits do not interfere with live recording of subsequent meetings.

**Dependencies.** F3, F4.

---

### 6.14 F14 — Markdown export

**Description.** Any meeting can be exported as a single Markdown file containing the structured summary, full transcript, and metadata.

**Behavior.**
- `GET /api/meetings/{id}/export.md` returns a Markdown file.
- Structure: metadata header, executive summary, decisions, action items, open questions, topics, full transcript with speakers and timestamps, related past meetings.
- Direct download from the UI via a button.

**Acceptance criteria.**
- Exported file renders correctly in GitHub, Notion, and Obsidian.
- All graph content is preserved in the export.
- File size is reasonable (under 1 MB for a 1-hour meeting).

**Dependencies.** F3, F4.

---

### 6.15 F15 — Self-hostable deployment

**Description.** The entire stack runs on a developer's laptop or a single server via Docker Compose.

**Behavior.**
- A single `docker-compose.yml` defines all services with `cpu` and `gpu` profiles.
- A `make up` command brings up the stack; `make down` tears it down.
- Default LLM is configurable: Anthropic Claude Haiku via API or local Qwen 2.5 14B via Ollama or vLLM.
- All other models (ASR, VAD, speaker embedding) run locally.
- A `.env.example` documents all configuration.

**Acceptance criteria.**
- A new developer can clone the repo and run `make up` successfully on macOS, Linux, and WSL2.
- The CPU profile works on a laptop without a GPU, with degraded but functional ASR.
- No service hardcodes credentials or external URLs.

**Dependencies.** All.

---

### 6.16 F16 — Honest model comparison report

**Description.** A written, evidence-based comparison of ASR models, included in the demo deliverables, addressing the challenge brief's explicit requirement.

**Behavior.**
- Three ASR models are evaluated: Moonshine-base, faster-whisper large-v3, NVIDIA Parakeet-TDT-0.6B.
- Each is run on at least three shared test recordings (clean English, noisy English, multi-speaker English).
- Metrics reported: word error rate, real-time factor, peak memory, GPU vs CPU viability.
- A model card (Markdown table) is included in the deliverables, answering the questions enumerated in the challenge brief.
- Reasoning for the final selection (Moonshine for live, faster-whisper for final) is documented.

**Acceptance criteria.**
- All three models successfully transcribe the test recordings.
- Numbers in the model card reflect actual measurements, not specs.
- The team can answer "why didn't you use Parakeet for live?" with data.

**Dependencies.** F2, F3.

---

## 7. System architecture

The backend is **one Python codebase** (`tryniq/`) run as **two processes** — `api` and `worker` — backed by three infrastructure containers (Postgres, MinIO, Redis). Both processes import the same modules; they are not separate services with API contracts between them, just two ways of running the same code.

### 7.1 High-level diagram

```
┌─────────────────────────────────────────────────────────────┐
│  BROWSER                                                    │
│  ┌──────────┐  ┌────────────┐  ┌──────────────┐             │
│  │ Content  │→ │ WebRTC tap │→ │ AudioWorklet │             │
│  │ script   │  │ (main world)│ │ + Silero VAD│             │
│  └──────────┘  └────────────┘  └───────┬──────┘             │
│       │                                 │                    │
│       ▼                                 ▼                    │
│  ┌──────────────┐               ┌─────────────┐              │
│  │ DOM observer │               │ WS clients  │              │
│  │ (names + AS) │               │ (per stream)│              │
│  └──────────────┘               └──────┬──────┘              │
└──────────────────────────────────────────┼───────────────────┘
                                           │ WebSocket(s)
                                           ▼
┌──────────────────────────────────────────────────────────────┐
│  BACKEND (Docker Compose)                                    │
│                                                              │
│   ┌──────────────────────┐                                   │
│   │  api  (FastAPI)      │  async only                       │
│   │  - REST              │                                   │
│   │  - WS /ingest        │──── streams PCM ──▶ MinIO         │
│   │  - SSE /events       │                                   │
│   │  - enqueues tasks    │                                   │
│   └──┬───────────────┬───┘                                   │
│      │               ▲                                       │
│      │ task.kiq()    │ pub/sub                               │
│      ▼               │ meeting:{id}:events                   │
│   ┌─────────────────────┐                                    │
│   │       Redis         │  TaskIQ broker + UI pub/sub        │
│   └──┬───────────────▲──┘                                    │
│      │ consume       │ publish                               │
│      ▼               │                                       │
│   ┌──────────────────┴───┐                                   │
│   │  worker (TaskIQ)     │  CPU/GPU/LLM-bound work           │
│   │  - asr_live          │                                   │
│   │  - asr_final         │  reads PCM ──▶ MinIO              │
│   │  - aggregator        │                                   │
│   │  - graph_builder     │  writes ──▶ Postgres              │
│   │  - speaker_id        │                                   │
│   └──────────────────────┘                                   │
│                                                              │
│   ┌──────────────┐  ┌──────────┐  ┌──────────┐               │
│   │  Postgres    │  │  MinIO   │  │  Redis   │               │
│   │  + pgvector  │  │  (audio) │  │ (broker  │               │
│   │  meetings,   │  │          │  │  + p/sub)│               │
│   │  utterances, │  │          │  │          │               │
│   │  graph_nodes,│  │          │  │          │               │
│   │  graph_edges,│  │          │  │          │               │
│   │  embeddings  │  │          │  │          │               │
│   └──────────────┘  └──────────┘  └──────────┘               │
└──────────────────────────────────────────────────────────────┘
            │ SSE
            ▼
   ┌─────────────────┐
   │ Web UI (Next.js)│  separate frontend container
   │ - transcript    │
   │ - graph         │
   │ - notes         │
   │ - chat          │
   └─────────────────┘
```

### 7.2 Process responsibilities

| Process / container | Responsibility | Stateful? |
|---|---|---|
| Extension | Capture, VAD, name resolution | No |
| `api` | WebSocket termination, audio persistence to MinIO, REST, SSE bridge from Redis pub/sub, task enqueueing | No (writes only) |
| `worker` | Live ASR, final ASR, aggregator window emission, graph builder LLM extraction, speaker ID, embeddings | Writes to Postgres / MinIO |
| Postgres + pgvector | Meetings, utterances, `graph_nodes`, `graph_edges`, embeddings, speaker profiles | Yes |
| MinIO | Per-speaker WAVs and exports | Yes |
| Redis | TaskIQ broker; pub/sub channel for UI events | Ephemeral |
| UI (Next.js) | Web frontend | No |

Pipeline modules (`asr_live`, `asr_final`, `aggregator`, `graph_builder`, `speaker_id`) are pure Python modules in `src/tryniq/pipeline/`, called from TaskIQ tasks in `src/tryniq/tasks/`. They are not separate services.

### 7.3 Communication patterns

- **Browser ↔ api:** WebSocket. One per audio stream. SSE for live UI updates.
- **api → worker:** TaskIQ tasks (`task.kiq(...)`), Redis-backed broker. Tasks receive object keys / row IDs only — never raw PCM.
- **worker → api:** Redis pub/sub on channel `meeting:{id}:events`. The api process subscribes per active SSE connection and forwards JSON payloads to the UI.
- **worker → state:** direct Postgres / MinIO writes.
- **UI → api:** REST for queries and corrections; SSE for live updates.

### 7.4 Deployment topology (MVP)

Single Docker Compose stack on a developer machine or single server. Three infra containers (Postgres, MinIO, Redis) plus two app containers (`api`, `worker`) built from the same image. Scale workers horizontally by running additional `worker` containers against the same Redis. No Kubernetes, no service mesh, no production infrastructure. Production hardening is post-MVP.

---

## 8. Data model

### 8.1 Postgres schema

```sql
-- Meetings
CREATE TABLE meetings (
    id UUID PRIMARY KEY,
    title TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    meet_url TEXT,
    status TEXT CHECK (status IN ('live', 'finalizing', 'final', 'failed'))
);

-- Persons (canonical identity across meetings)
CREATE TABLE persons (
    id UUID PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Voice embeddings (ECAPA, 192-dim)
CREATE TABLE voice_embeddings (
    id UUID PRIMARY KEY,
    person_id UUID REFERENCES persons(id),
    embedding VECTOR(192),
    extracted_from_meeting_id UUID REFERENCES meetings(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Per-meeting participants
CREATE TABLE meeting_participants (
    meeting_id UUID REFERENCES meetings(id),
    person_id UUID REFERENCES persons(id),
    stream_id UUID,
    is_local_user BOOLEAN,
    PRIMARY KEY (meeting_id, person_id)
);

-- Utterances (transcript segments)
CREATE TABLE utterances (
    id UUID PRIMARY KEY,
    meeting_id UUID REFERENCES meetings(id),
    person_id UUID REFERENCES persons(id),
    t_start FLOAT NOT NULL,  -- seconds from meeting start
    t_end FLOAT NOT NULL,
    text TEXT NOT NULL,
    confidence FLOAT,
    is_final BOOLEAN DEFAULT FALSE,
    model TEXT,  -- 'moonshine' or 'whisper-large-v3'
    edited_by_user BOOLEAN DEFAULT FALSE,
    word_timings JSONB  -- [[word, start, end, conf], ...]
);
CREATE INDEX idx_utterances_meeting ON utterances(meeting_id, t_start);

-- Utterance embeddings for RAG
CREATE TABLE utterance_embeddings (
    utterance_id UUID PRIMARY KEY REFERENCES utterances(id),
    embedding VECTOR(384)  -- e.g. all-MiniLM-L6-v2
);

-- Topic embeddings for cross-meeting linking
CREATE TABLE topic_embeddings (
    topic_id UUID PRIMARY KEY,
    meeting_id UUID REFERENCES meetings(id),
    embedding VECTOR(384)
);

-- Knowledge graph: nodes
-- type ∈ {Meeting, Person, Topic, Decision, ActionItem, OpenQuestion, Entity, Utterance}
-- fields holds type-specific attributes (title, text, t_start, t_end, due_date, etc.)
-- status ∈ {provisional, confirmed, superseded} (NULL for non-extractable types)
CREATE TABLE graph_nodes (
    id UUID PRIMARY KEY,
    meeting_id UUID REFERENCES meetings(id),
    type TEXT NOT NULL,
    fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_graph_nodes_meeting ON graph_nodes(meeting_id);
CREATE INDEX idx_graph_nodes_type ON graph_nodes(meeting_id, type);

-- Knowledge graph: edges
-- type ∈ {PARTICIPATED_IN, DISCUSSED_IN, MADE_DECISION, ASSIGNED_TO,
--         BLOCKS, ABOUT_TOPIC, MENTIONS, SOURCE, RELATES_TO}
CREATE TABLE graph_edges (
    id UUID PRIMARY KEY,
    meeting_id UUID REFERENCES meetings(id),
    type TEXT NOT NULL,
    from_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    to_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_graph_edges_meeting ON graph_edges(meeting_id);
CREATE INDEX idx_graph_edges_from ON graph_edges(from_id);
CREATE INDEX idx_graph_edges_to ON graph_edges(to_id);
```

### 8.2 Graph node and edge types

The graph lives in the two Postgres tables above. Logical schema:

**Node types** (`graph_nodes.type`):

| Type | Notable `fields` keys |
|---|---|
| `Meeting` | `title`, `started_at` |
| `Person` | `display_name` |
| `Topic` | `title`, `summary`, `t_start`, `t_end` |
| `Decision` | `text`, `t`, `confidence` |
| `ActionItem` | `text`, `t`, `due_date` |
| `OpenQuestion` | `text`, `t`, `answered` |
| `Entity` | `name`, `kind` |
| `Utterance` | `t_start`, `t_end`, `text` |

**Edge types** (`graph_edges.type`): `PARTICIPATED_IN` (Person→Meeting), `DISCUSSED_IN` (Topic→Meeting), `MADE_DECISION` (Person→Decision), `ASSIGNED_TO` (ActionItem→Person), `BLOCKS` (OpenQuestion→Decision), `ABOUT_TOPIC` (Decision/ActionItem→Topic), `MENTIONS` (Utterance→Entity/Person), `SOURCE` (Decision/ActionItem/OpenQuestion→Utterance), `RELATES_TO` (Topic→Topic, including cross-meeting).

The graph builder validates type compatibility (allowed `from_type → to_type` pairs) at the application layer before insertion.

### 8.3 Object storage layout (MinIO)

```
tryniq-bucket/
  meetings/
    {meeting_id}/
      streams/
        {stream_id}.wav         # full per-speaker audio
      exports/
        summary.md
```

---

## 9. Internal contracts

### 9.1 Extension → api WebSocket

**URL:** `wss://api/ingest/{meeting_id}/{stream_id}`

**Init message** (text frame, must be first):
```json
{
  "type": "init",
  "meeting_id": "uuid",
  "stream_id": "uuid",
  "speaker": {
    "tile_id": "google-meet-internal-id",
    "display_name": "Sarah Chen",
    "is_local_user": false
  },
  "audio_format": {
    "sample_rate": 16000,
    "encoding": "pcm_s16le",
    "channels": 1
  },
  "client_started_at": "2026-05-04T14:00:00Z"
}
```

**Audio frames:** binary WebSocket frames containing raw PCM int16, ~200ms per frame (3200 samples = 6400 bytes).

**Control messages** (text frames):
```json
{ "type": "vad_speech_start", "t": 12.4 }
{ "type": "vad_speech_end", "t": 15.7 }
{ "type": "speaker_active", "active": true, "t": 12.4 }
{ "type": "speaker_renamed", "new_name": "Sarah C." }
{ "type": "stream_end" }
```

### 9.2 TaskIQ tasks and Redis channels

There is no message bus. Cross-process communication is (a) TaskIQ tasks for api→worker work dispatch, and (b) Redis pub/sub for worker→api UI events.

**TaskIQ task signatures** (defined in `src/tryniq/tasks/`, all coroutines):

| Task | Args | Producer | Purpose |
|---|---|---|---|
| `transcribe_live` | `(meeting_id, stream_id, object_key, t_start, t_end)` | api (on VAD speech-end) | Stream-to-text with Moonshine; writes `utterances` with `is_final=false` |
| `transcribe_final` | `(meeting_id, stream_id)` | api (on meeting end) | Whisper large-v3 on the full per-speaker WAV; replaces live segments |
| `aggregate_window` | `(meeting_id,)` | self-scheduled (every 15 s while live) | Builds 30 s sliding window; enqueues `build_graph` if changed |
| `build_graph` | `(meeting_id, window_id)` | aggregator | LLM extraction; node dedup; writes `graph_nodes` / `graph_edges` |
| `compute_speaker_embeddings` | `(meeting_id,)` | api (on meeting end) | ECAPA per speaker; updates `voice_embeddings` |
| `match_speaker` | `(meeting_id, stream_id)` | api (on new stream) | Nearest-neighbor against historical voice embeddings |
| `embed_utterances` | `(meeting_id,)` | api (on meeting end) | Populates `utterance_embeddings` for RAG |
| `rebuild_window` | `(meeting_id, t_start, t_end)` | api (on transcript edit) | Localized graph re-extraction over an edited region |

All tasks are **idempotent** (use deterministic IDs / upsert semantics) so TaskIQ retries on the Redis broker are safe.

**Redis pub/sub channels** (worker → api → UI via SSE):

| Channel | Payloads |
|---|---|
| `meeting:{meeting_id}:events` | `{ "kind": "transcript_segment", ... }`, `{ "kind": "graph_patch", "ops": [...] }`, `{ "kind": "meeting_lifecycle", "event": "started" \| "ended" }`, `{ "kind": "transcript_finalized" }`, `{ "kind": "speaker_match", ... }` |

The api process maintains one Redis subscription per active SSE client and forwards JSON payloads unchanged. Payload schemas are Pydantic models in `src/tryniq/models/`.

### 9.3 REST API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/meetings` | List meetings |
| `GET` | `/api/meetings/{id}` | Meeting metadata |
| `GET` | `/api/meetings/{id}/transcript` | Full transcript |
| `GET` | `/api/meetings/{id}/graph` | Full graph state |
| `GET` | `/api/meetings/{id}/events` | SSE stream for live updates |
| `POST` | `/api/meetings/{id}/ask` | Chat with the meeting |
| `PATCH` | `/api/utterances/{id}` | Edit transcript text |
| `PATCH` | `/api/persons/{id}` | Rename / link speaker identity |
| `GET` | `/api/meetings/{id}/export.md` | Markdown export |

### 9.4 LLM prompt contract for graph extraction

```
You are a meeting graph builder. You receive a 30-second window of transcript
and the current state of the meeting graph. Output ONLY a JSON array of
operations to update the graph.

Operations:
- add_node: { "op": "add_node", "node_type": "...", "fields": {...}, "temp_id": "..." }
- add_edge: { "op": "add_edge", "edge_type": "...", "from": "...", "to": "..." }
- update_node: { "op": "update_node", "id": "...", "fields": {...} }

Rules:
- Every Decision/ActionItem/OpenQuestion MUST have a SOURCE edge to an utterance_id present in the window.
- Mark new nodes 'provisional' unless explicitly affirmed in speech.
- Promote to 'confirmed' if the speaker said "let's do X", "agreed", "yes" in response.
- Set existing nodes to 'superseded' if contradicted by current window.
- Do NOT invent owners. ASSIGNED_TO only when speech makes it explicit.
- Do NOT extract action items from hypothetical speech ("we could", "maybe").

Current graph summary:
{graph_summary}

Recent transcript window (with utterance ids):
{window}

Output (JSON array only, no prose):
```

Response is parsed, validated against a Pydantic schema, and applied transactionally to the Postgres `graph_nodes` / `graph_edges` tables.

---

## 10. Model selection and comparison

### 10.1 Final selections

| Role | Model | Rationale |
|---|---|---|
| Live ASR | Moonshine-base | Designed for streaming, low latency on short chunks |
| Final ASR | faster-whisper large-v3 | Best WER, mature ecosystem, CTranslate2-optimized |
| VAD | Silero VAD (ONNX) | 2 MB, browser-runnable, accurate |
| Speaker embedding | SpeechBrain ECAPA-TDNN | Standard, robust, fast inference |
| Graph LLM (default) | Anthropic Claude Haiku 4.5 | Strong structured output, low latency, cheap |
| Graph LLM (self-host) | Qwen 2.5 14B Instruct | Best open structured-output model in size class |
| Text embedding | all-MiniLM-L6-v2 | Small, fast, good enough for RAG |

### 10.2 Comparison plan

For the model card deliverable, three ASR models are benchmarked:

| Model | Size | Latency target | WER target | Hardware |
|---|---|---|---|---|
| Moonshine-base | 60M | <200ms per 1s | <12% | CPU |
| faster-whisper large-v3 | 1.5B | <0.3 RTF | <5% | GPU preferred |
| Parakeet-TDT-0.6B | 600M | <0.1 RTF | <5% | GPU only |

Test set: three recordings (clean, noisy, multi-speaker), each ~5 minutes of English, with hand-curated reference transcripts.

The model card will answer the explicit questions from the challenge brief: which models, why, hardware requirements, local/cloud/hybrid, what worked, what didn't, recommendation for v2.

---

## 11. User experience and interface

### 11.1 Extension popup

Compact popup with:
- Recording status indicator (red circle when recording)
- Start / Stop button
- Connection status to api
- Participant list with active-speaker highlight
- Link to "Open meeting view" (opens web UI)

### 11.2 Meeting web UI

Single-page layout with three panels:

**Left panel — live transcript.**
- Speakers color-coded.
- Timestamps clickable to jump in audio playback (post-meeting).
- Final segments rendered black, live segments lighter.
- Low-confidence words rendered gray.
- Edit-on-click in post-meeting mode.

**Center panel — graph view.**
- Cytoscape canvas with force-directed layout.
- Legend with node types and colors.
- Click node → side panel with details.
- Timeline scrubber at the bottom for replaying graph growth.

**Right panel — structured notes.**
- Sections: Topics, Decisions, Action Items, Open Questions.
- "Copy as Markdown" button.
- "Download .md" button.
- "Ask about this meeting" input (post-meeting only).
- "Related past meetings" if cross-meeting links exist.

### 11.3 Visual conventions

| Element | Color / Style | Meaning |
|---|---|---|
| Topic node | Blue | Discussion theme |
| Decision node | Green | Resolution reached |
| ActionItem node | Yellow | Task created |
| OpenQuestion node | Orange | Question raised |
| Person node | Gray | Participant or mentioned person |
| Entity node | Purple | Project, system, document, metric |
| Provisional status | Dashed outline | LLM proposed, not yet stable |
| Confirmed status | Solid outline | Stable across windows |
| Superseded status | Gray + strikethrough | Contradicted later |
| Owner-less decision | Red border | Needs follow-up |
| Unanswered question | Pulsing orange | Open >2 minutes |

---

## 12. Success metrics

### 12.1 Hackathon-evaluation metrics

These map directly to the challenge rubric:

| Rubric criterion | Weight | How we score |
|---|---|---|
| Architecture quality | 20 | WebRTC tap + per-speaker streams + graph data model |
| Speaker separation | 20 | Per-stream isolation; demo with overlapping speech |
| Active speaker detection | 15 | DOM-based, demonstrated live |
| Transcription quality | 15 | Live + final pass; confidence-aware UI |
| Model research quality | 15 | Comparison report on three ASR models |
| Notes usefulness | 10 | Graph-derived structured notes; cross-meeting links |
| Demo quality | 5 | Rehearsed 5-minute scenario |

### 12.2 Functional metrics (verified in testing)

| Metric | Target |
|---|---|
| End-to-end live latency (speech → UI) | <3s p95 |
| Speaker attribution accuracy | >98% (DOM-based) |
| Live ASR WER (clean English) | <12% |
| Final ASR WER (clean English) | <5% |
| Decision extraction precision | >70% |
| Decision extraction recall | >70% |
| Cross-meeting speaker recognition accuracy | >90% on test set |
| `make up` to working stack | <3 minutes on first run |

---

## 13. Risks and mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Google Meet runs WebRTC in a Worker scope; main-world patch misses tracks | Medium | High | Inject patches into Worker scope as well; have fallback DOM-based audio capture via `getDisplayMedia` with system audio |
| R2 | Meet DOM selectors break during the week | High | Medium | Use ARIA roles and stable `data-*` attributes; maintain Speaker N fallback labeling |
| R3 | LLM returns malformed JSON or hallucinates non-existent utterance IDs | Medium | Medium | Pydantic validation; reject unknown IDs; retry once; otherwise skip window and continue |
| R4 | Graph deduplication threshold too aggressive — merges distinct topics | Medium | Medium | Tune threshold on test meetings; allow manual split in UI |
| R5 | Live ASR latency exceeds 3s on developer hardware | Medium | Medium | Use Moonshine-tiny if needed; reduce window size; ensure GPU available for demo |
| R6 | Postgres / Redis / MinIO dependency conflicts in Docker | Low | High | Lock all images by digest; CI run on clean machine |
| R6b | Worker process crashes mid-task (LLM hang, OOM on Whisper, Python fault) | Medium | Medium | TaskIQ retries on the Redis-backed broker; tasks are designed idempotent (deterministic IDs, upsert semantics) so retries do not double-write |
| R7 | Demo-day Meet audio path differs from dev environment | Low | High | Rehearse from clean machines; record backup video |
| R8 | Self-track (local mic) creates duplicate transcript with remote echo | Medium | Low | Detect and flag local track; allow toggle in popup |
| R9 | Graph builder LLM costs exceed budget during testing | Medium | Low | Cache results; use Haiku not Opus; rate-limit window emission |
| R10 | Participants object to recording without consent | Low | High | Extension popup shows clear "Recording" badge; UI disclaimer; document team consent process |

---

## 14. Phased delivery plan

Seven daily phases, each ending with a working end-to-end milestone in its own scope.

### Phase 0 — Setup (day 0, ~4 hours)
- Single-package monorepo (`src/tryniq/`), Docker Compose with health checks (postgres, redis, minio, api, worker), Makefile, lint config, empty extension. TaskIQ broker wired to Redis; one trivial `ping` task end-to-end.
- **Done when:** `docker compose up` brings up all containers with green health checks; `task.kiq()` from api runs in worker; extension logs in Meet.

### Phase 1 — Capture (day 1)
- WebRTC tap, AudioWorklet, Silero VAD, DOM name resolution, WebSocket streaming. The api process streams PCM to MinIO.
- **Done when:** two-person Meet produces two clean per-speaker WAV files in MinIO with correct names.

### Phase 2 — Transcription (day 2)
- `transcribe_live` and `transcribe_final` tasks, aggregator scaffolding, minimal UI showing live transcript via SSE bridged from Redis pub/sub.
- **Done when:** speech in Meet appears in UI within 3 seconds with correct speaker labels; final pass refines the transcript after meeting end.

### Phase 3 — Graph builder core (day 3)
- Postgres `graph_nodes` / `graph_edges` schema, `aggregate_window` + `build_graph` tasks, LLM prompt with structured output, idempotency, source edges.
- **Done when:** a 5-minute scripted meeting produces a graph with correct decisions and action items, all grounded to utterances.

### Phase 4 — Graph UI and notes (day 4)
- Cytoscape graph view, structured notes panel, transcript-graph cross-linking, manual corrections.
- **Done when:** graph and notes update live; clicking a decision jumps the transcript to its source.

### Phase 5 — Cross-meeting memory and post-processing (day 5)
- `compute_speaker_embeddings`, `match_speaker`, `embed_utterances` tasks; topic embedding linking, full-meeting graph re-extraction after final ASR, Markdown export.
- **Done when:** two consecutive test meetings show speaker recognition and topic linking; export produces clean Markdown.

### Phase 6 — Killer features and polish (day 6)
- Two of: open question pings, owner-less warnings, chat with the meeting, confidence-aware transcript, inline editing.
- Polish: extension popup, error toasts, README, empty states.
- **Done when:** demo flow runs end-to-end without manual intervention.

### Phase 7 — Demo rehearsal (day 7)
- Three full demo runs.
- Backup recording.
- Slides for architecture and model card.
- FAQ preparation.
- **Done when:** team is confident demo will land.

---

## 15. Out of scope

The following are explicitly excluded from MVP. They are signaled as "next steps" in demo Q&A.

- Headless Chrome bot deployment (Puppeteer-driven, same extension).
- Zoom and Microsoft Teams support.
- Any language other than English.
- Native desktop or mobile apps.
- Multi-tenancy, organization-level RBAC, SSO.
- Production-grade observability (tracing, metrics, alerting beyond logs).
- High availability deployment (k8s, replication, failover).
- Speech generation, text-to-speech, voice cloning.
- Real-time machine translation.
- A meeting assistant that participates in conversation.
- Automatic creation of Linear/Jira tickets from action items.
- Slack / Teams notification delivery of summaries.
- Calendar integration for auto-discovery of meetings to record.

---

## 16. Open questions

These are decisions deferred until implementation reveals more:

1. **Worker-scope WebRTC.** If Google Meet routes audio through Workers (likely), do we patch in worker scope as well, or fall back to a different capture mechanism? — Resolve in Phase 1, day 1.

2. **Cross-meeting graph rendering.** Do related past topics appear inline in the current meeting's graph, or only in a separate panel? UX decision based on visual clutter testing. — Resolve in Phase 4.

3. **LLM choice for self-host story.** Qwen 2.5 14B vs Llama 3.3 70B vs DeepSeek 14B for graph extraction — tradeoff between local-friendliness and structured-output quality. — Resolve in Phase 3 with prompt comparison.

4. **Confidence threshold for low-confidence rendering.** 0.5 is a starting point; may need tuning per Whisper version. — Resolve in Phase 6 polish.

5. **Topic similarity threshold for cross-meeting linking.** 0.8 cosine is a starting point; may produce false links on common phrases like "the deploy". — Resolve in Phase 5 testing.

6. **Idempotency embedding model.** Use the same all-MiniLM-L6-v2 used for RAG, or something larger for graph node dedup? — Resolve in Phase 3.

---

## 17. Appendix

### 17.1 Glossary

- **WebRTC tap.** The technique of intercepting `RTCPeerConnection` audio tracks before they are mixed for playback.
- **Diarization.** The process of separating "who spoke when" from a mixed audio recording. Tryniq avoids this for the live path.
- **Active speaker detection.** Identifying which participant is currently speaking. Tryniq derives this from Meet's DOM CSS classes.
- **Grounding.** The practice of linking every extracted artifact (decision, action item) back to a specific source utterance, preventing hallucination.
- **Provisional / confirmed / superseded.** Lifecycle statuses for graph nodes that may change as the meeting evolves.
- **Sliding window.** The 30-second moving slice of transcript fed to the graph LLM every 15 seconds.

### 17.2 Repository structure

Single Python package; `api` and `worker` are two entry points into the same code.

```
tryniq/
├── README.md
├── Makefile
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── src/tryniq/
│   ├── api/                     # FastAPI app: REST, WS /ingest, SSE
│   │   ├── main.py
│   │   ├── ingest.py            # WS handler, streams PCM → MinIO
│   │   ├── meetings.py          # REST endpoints
│   │   └── events.py            # SSE bridge from Redis pub/sub
│   ├── tasks/                   # TaskIQ task definitions
│   │   ├── __init__.py          # exports `broker`
│   │   ├── transcribe.py        # transcribe_live, transcribe_final
│   │   ├── aggregate.py         # aggregate_window
│   │   ├── graph.py             # build_graph, rebuild_window
│   │   ├── speaker.py           # compute_speaker_embeddings, match_speaker
│   │   └── embed.py             # embed_utterances
│   ├── pipeline/                # pure modules called from tasks
│   │   ├── asr_live.py
│   │   ├── asr_final.py
│   │   ├── aggregator.py
│   │   ├── graph_builder.py
│   │   └── speaker_id.py
│   ├── storage/
│   │   ├── pg.py
│   │   ├── minio.py
│   │   └── redis.py
│   ├── llm/                     # provider abstraction (Anthropic / Ollama / vLLM)
│   ├── models/                  # Pydantic schemas (WS init, lifecycle, graph ops)
│   └── config.py
├── extension/                   # Chrome MV3 extension, separate package
│   ├── manifest.json
│   ├── src/
│   │   ├── background.ts
│   │   ├── content.ts
│   │   ├── injected.ts          # main world: WebRTC tap
│   │   ├── audio-worklet.ts
│   │   ├── popup/
│   │   └── ws-client.ts
│   ├── vendor/silero_vad.onnx
│   └── vite.config.ts
├── ui/                          # Next.js, separate package
│   ├── app/
│   │   └── m/[meetingId]/page.tsx
│   ├── components/
│   │   ├── LiveTranscript.tsx
│   │   ├── MeetingGraph.tsx
│   │   ├── NotesPanel.tsx
│   │   └── MeetingChat.tsx
│   └── store/
├── infra/
│   └── postgres/init.sql
└── tests/
    ├── fixtures/
    └── e2e/
```

### 17.3 Demo script (5 minutes)

| Time | Action |
|---|---|
| 0:00 – 0:30 | Open Meet with three participants. Click extension. Click Start. |
| 0:30 – 2:30 | Run scripted dialogue: deploy issue, decision to roll back, owner assignment, unanswered question about payment flow. Show live transcript and graph growing in real time. |
| 2:30 – 3:30 | Highlight three "moments": correct speaker labels, owner-less decision flagged, unanswered question pulsing orange. |
| 3:30 – 4:30 | Open a previously-recorded meeting. Show automatic speaker recognition. Show topic linked to past discussion via `RELATES_TO` edge. |
| 4:30 – 5:00 | End meeting. Use "Chat with the meeting": "Why did we decide to roll back?" → cited answer with timestamp. Download Markdown. |

### 17.4 Architecture talking points (3 minutes)

1. "Other teams are solving diarization. We avoided needing it."
2. "The extension intercepts WebRTC tracks before mixing — clean audio per speaker, real names from the DOM, active speaker for free."
3. "We modeled meetings as a graph, not a transcript. Decisions, action items, questions, topics — all typed nodes with grounded sources."
4. "Cross-meeting memory: ECAPA voice embeddings recognize people. Topic embeddings link discussions across time."
5. "Adaptive transcription: Moonshine for live latency, Whisper large-v3 refines after the meeting. UI shows the diff."
6. "Fully self-hostable: every model can run locally. Single `make up`."
7. "Bot deployment via headless Chrome is the next step — same extension, no architectural changes."

### 17.5 Anticipated Q&A

**Q: How do you handle Zoom and Teams?**
A: Architecture is identical. WebRTC tap needs adaptation to each platform's track structure. Post-MVP.

**Q: What if a participant doesn't have the extension installed?**
A: Two answers. Today: only participants with the extension produce clean per-speaker streams; we fall back to mixed-audio with diarization for unknown speakers. Tomorrow: a bot (headless Chrome with our extension) joins on behalf of anyone, capturing all per-speaker streams without requiring installation.

**Q: Privacy — where does audio go?**
A: Self-hosted MinIO inside Docker Compose. LLM is configurable to a local model. Nothing leaves the company unless explicitly configured.

**Q: How accurate is graph extraction?**
A: We measured precision/recall above 70% on scripted test meetings for decisions and action items. Every extracted node is grounded — users can verify.

**Q: Why not pyannote for diarization as a backup?**
A: We use it for the upload-recording fallback path. It's the right tool for that job. For live capture from a Meet tab, we don't need it because we never have a mixed stream.

**Q: What's missing for production?**
A: Multi-tenancy, RBAC, SSO, observability, HA. The MVP is a working internal prototype, not a product. Roadmap is documented.

---

*End of document.*