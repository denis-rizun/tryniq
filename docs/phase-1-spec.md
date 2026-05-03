# Phase 1 — Capture: Implementation Spec

> **Goal:** ship the Chrome extension end-to-end, plus the *minimum* backend needed to prove it works. Everything downstream (ASR, graph builder, UI) is out of scope for this phase.
>
> **Done when:** a real two-person Google Meet call produces two clean per-speaker WAV files in MinIO, each tagged with the correct display name resolved from the Meet DOM, with VAD-gated speech only and no cross-talk between streams.
>
> **Phase mapping:** PRD §6.1 (F1), §7, §9.1, §13 R1/R2/R8, §17.2.

This document is the source of truth for Phase 1. It supersedes the high-level Phase 0/1 sketch in PRD §14 with concrete file layout, contracts, and acceptance tests. Cite section numbers from this file in commits.

---

## 1. Scope

### 1.1 In scope

- Chrome MV3 extension (`extension/`) with WebRTC tap, AudioWorklet + Silero VAD, DOM observer, per-stream WebSocket client, popup UI.
- Minimal FastAPI api process (`src/tryniq/api/`) that terminates WebSockets, persists per-stream PCM as WAV to MinIO, and emits meeting lifecycle events.
- Docker Compose stack with **only** the services Phase 1 needs: `api`, `worker`, `minio`, `redis`, `postgres`. ASR, aggregator, graph-builder, speaker-id, UI are deferred — no stubs, no empty Dockerfiles.
- A static "fake Meet" harness (`tests/fixtures/fake-meet/`) that mirrors the real Google Meet DOM hooks, enabling iteration without scheduling real calls.
- Makefile targets to bring up the stack and load the unpacked extension.

### 1.2 Out of scope (deferred to later phases)

- Any ASR, transcription, diarization. The api process writes raw audio and stops; no TaskIQ tasks are enqueued in Phase 1 except for a smoke-test `ping`.
- Postgres schema population (table is created — see §6.4 — but the api only inserts a `meetings` row to track lifecycle). No utterances yet.
- Speaker re-identification across meetings (F7).
- UI beyond the extension popup. The web UI (`ui/`) is not built in this phase.
- Graph builder, TaskIQ tasks beyond a smoke-test `ping`. The Redis pub/sub channel `meeting:{id}:events` is wired (api-side subscriber + SSE bridge) but emits only the `meeting_lifecycle` event in Phase 1.
- Worker-scope WebRTC patching — see §3.3 for the detection-and-defer strategy.
- Authentication on the api. Localhost / LAN trust assumed.

### 1.3 Deferred but designed-for

These are not built in Phase 1 but the contracts and code shapes here must not paint Phase 2+ into a corner:

- **Lifecycle events:** the api publishes a `meeting_lifecycle` payload to Redis pub/sub on `meeting:{id}:events` (PRD §9.2) and is structured so that adding `transcribe_live` enqueueing in Phase 2 is a one-function change.
- **Postgres `utterances`, `graph_nodes`, `graph_edges` tables** are created at startup (so Phase 2/3 have somewhere to write) but Phase 1 does not insert into them.
- **Per-stream WAV files** in MinIO use the layout from PRD §8.3 so Phase 3's `transcribe_final` task can find them unchanged.
- **TaskIQ broker** is wired in `src/tryniq/tasks/__init__.py` against Redis. A `ping` task is registered to prove enqueue + consume works end-to-end. Adding real tasks in Phase 2 is purely additive.

---

## 2. Repo layout after Phase 1

```
tryniq/
├── README.md
├── Makefile                        # make up / down / ext / fake-meet
├── docker-compose.yml
├── .env.example
├── pyproject.toml                  # workspace root, references services
├── docs/
│   ├── PRD.md
│   ├── phase-1-spec.md             # this file
│   └── google-meet-dom.html
├── extension/
│   ├── manifest.json               # MV3
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── public/
│   │   └── icons/                  # 16/32/48/128 png
│   ├── vendor/
│   │   └── silero_vad.onnx         # committed, ~2 MB (see §3.5)
│   └── src/
│       ├── manifest.ts             # generated manifest helper (optional)
│       ├── background.ts           # service worker; lifecycle, popup ↔ content
│       ├── content.ts              # isolated world; injects main-world script, runs DOM observer, owns WS
│       ├── injected.ts             # MAIN world; RTCPeerConnection monkey-patch
│       ├── audio-worklet.ts        # AudioWorkletProcessor: resample → int16 → VAD → postMessage
│       ├── vad.ts                  # Silero VAD ONNX wrapper (runs in worklet via WASM SIMD)
│       ├── ws-client.ts            # one WebSocket per stream
│       ├── dom-observer.ts         # tile/SSRC/name/active-speaker observer
│       ├── bridge.ts               # postMessage protocol between main world ↔ isolated world
│       ├── types.ts                # shared TS types (mirror backend Pydantic models)
│       └── popup/
│           ├── index.html
│           ├── popup.tsx
│           └── popup.css
├── pyproject.toml                  # tryniq package, python>=3.13, uv-managed
├── Dockerfile                      # one image; api + worker run different commands
├── src/tryniq/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── ingest.py               # WebSocket handler; streams PCM → MinIO
│   │   ├── meetings.py             # POST /meetings, POST /meetings/{id}/end, GET /health
│   │   └── events.py               # SSE bridge from Redis pub/sub (Phase 1: lifecycle only)
│   ├── tasks/
│   │   ├── __init__.py             # exports `broker` (TaskIQ + taskiq-redis)
│   │   └── ping.py                 # smoke-test task (Phase 1)
│   ├── pipeline/                   # empty in Phase 1; populated in Phase 2+
│   ├── storage/
│   │   ├── pg.py                   # asyncpg pool, schema bootstrap
│   │   ├── minio.py                # streaming WAV writer
│   │   └── redis.py                # pub/sub helpers
│   ├── models/
│   │   ├── ws_init.py              # Pydantic init/control message models
│   │   └── lifecycle.py
│   └── config.py                   # pydantic-settings, all from env
├── infra/
│   └── postgres/init.sql           # creates meetings, utterances, persons, graph_nodes, graph_edges (Phase 1 uses meetings only)
└── tests/
    ├── fixtures/
    │   └── fake-meet/
    │       ├── index.html          # static page mirroring real Meet DOM hooks (§5)
    │       ├── peer.html           # opens RTCPeerConnection on each side
    │       ├── audio/
    │       │   ├── alice.wav
    │       │   └── bob.wav
    │       └── serve.py            # tiny static server, runs `python -m http.server` equivalent
    └── e2e/
        └── two_speaker.md          # manual checklist (see §8)
```

> Anything outside this list is **not** part of Phase 1. Don't scaffold empty `services/asr-live/` etc. — when those phases start, they'll add their own structure.

---

## 3. Extension

### 3.1 Manifest (MV3)

`extension/manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "Tryniq Capture (dev)",
  "version": "0.1.0",
  "description": "Per-speaker WebRTC audio capture for Google Meet.",
  "permissions": ["storage", "activeTab", "scripting"],
  "host_permissions": [
    "https://meet.google.com/*",
    "http://localhost/*"
  ],
  "background": { "service_worker": "background.js", "type": "module" },
  "action": { "default_popup": "popup/index.html" },
  "content_scripts": [
    {
      "matches": ["https://meet.google.com/*", "http://localhost/fake-meet/*"],
      "js": ["content.js"],
      "run_at": "document_start",
      "world": "ISOLATED"
    }
  ],
  "web_accessible_resources": [
    {
      "resources": ["injected.js", "audio-worklet.js", "vendor/silero_vad.onnx"],
      "matches": ["https://meet.google.com/*", "http://localhost/*"]
    }
  ]
}
```

Notes:
- `run_at: document_start` is required so the main-world patch lands before Meet constructs `RTCPeerConnection`s.
- `web_accessible_resources` exposes the injected script and the VAD model to page contexts.
- Adding `http://localhost/*` lets the same content script run against the fake-Meet harness (§5).

### 3.2 World separation and bridge

Two scripts run in the page; one in each world:

- **`content.ts` (ISOLATED world)** — has full `chrome.*` API access. Owns WebSocket connections, popup messaging, and the DOM `MutationObserver` (DOM is shared across worlds, so observation works from either side, but state lives here).
- **`injected.ts` (MAIN world)** — injected by `content.ts` via a `<script>` tag with `src=chrome.runtime.getURL('injected.js')`. Has access to the page's `RTCPeerConnection`. Cannot use `chrome.*`.

Cross-world communication is **only** `window.postMessage` with a discriminator: `{ source: 'tryniq', kind: '...', ... }`. `bridge.ts` exports a typed send/recv helper used by both sides. Never use `CustomEvent` (some sites stomp on it) and never `window.tryniq = {}` (page code can read it).

### 3.3 WebRTC tap (`injected.ts`)

This runs in the main world before Meet creates any `RTCPeerConnection`. It:

1. Stores the original constructor: `const _RTCPC = window.RTCPeerConnection`.
2. Replaces it with a wrapper that, on construction, attaches an `addEventListener('track', ...)` to every instance.
3. On `track` event, if `event.track.kind === 'audio'`:
   - Generates a `streamId = crypto.randomUUID()`.
   - Records `{ ssrc, trackId, mid, transceiver }` for later DOM matching. SSRC comes from `event.transceiver.receiver.getSynchronizationSources()[0]?.source` (polled briefly if zero on first call) or via `pc.getStats()` when needed.
   - Posts `{ kind: 'track', streamId, trackId, ssrc, mid, isLocal: false }` to the isolated world.
   - Routes the track into a fresh `AudioContext` → `MediaStreamAudioSourceNode` → `AudioWorkletNode('tryniq-capture')`. The worklet posts back PCM frames; main world re-postMessages them to isolated world.
4. Also wraps `RTCPeerConnection.prototype.addTrack` to intercept the **local** mic track (with `isLocal: true`). This is the user's own audio (R8 in PRD §13). Phase 1 captures it; the popup (§3.7) exposes a toggle to disable.

**Worker scope (PRD R1).** The injected script logs a one-time telemetry line `tryniq.tap.installed { peerConnections: <n>, audioTracks: <n> }` 10 seconds after recording starts. If `audioTracks === 0` while the user is in a call with audible others, the spec is to log an error and surface a toast: *"No audio tracks detected — Meet may be using a Worker. Worker-scope patching is a fast-follow; ping #tryniq."* This is the detect-and-defer behavior agreed for Phase 1. Worker patching is **not** built here; if R1 fires we cut a follow-up issue.

### 3.4 AudioWorklet (`audio-worklet.ts`)

Registered as `tryniq-capture`. Per-track instance.

- Input: native sample rate (browser-decided, usually 48 kHz).
- Resample to **16 kHz mono** using a small polyphase filter (`audio-resampler` lib is overkill; hand-rolled linear-phase resampler is fine — quality matters less than CPU at this stage, and the final ASR pass operates on raw uploaded audio).
- Convert float32 → int16 PCM (saturating).
- Buffer into ~200 ms chunks (3200 samples) before posting to main world.
- Maintain a 200 ms ring-buffer of pre-VAD audio so we can prepend it on `speech_start` (PRD F1: "200ms pre-roll to capture leading consonants").
- Run Silero VAD (§3.5) on each 30 ms or 50 ms window inside the worklet. Maintain a small state machine:
  - `idle` → `speech` on N consecutive speech windows (default 3, ~96 ms).
  - `speech` → `idle` on M consecutive silence windows (default 12, ~384 ms hangover).
- While `speech`: post audio frames to main world tagged `{ kind: 'pcm', t: ctx.currentTime, payload: Int16Array }`.
- On state transitions: post `{ kind: 'vad_speech_start' | 'vad_speech_end', t }`.

The worklet emits **only during speech** (plus pre-roll). This is what gives the api clean audio without us doing diarization.

### 3.5 Silero VAD inside the worklet

Silero VAD is shipped as a 2 MB ONNX file. Running ONNX inside an AudioWorkletProcessor is non-trivial:

- AudioWorklets do **not** have `fetch`, `WebAssembly.compileStreaming`, or DOM. They have `WebAssembly` (instantiate from bytes) and standard JS.
- Strategy: in `content.ts`, fetch `vendor/silero_vad.onnx` and `onnxruntime-web` WASM bytes, then send them via `audioWorkletNode.port.postMessage({ kind: 'init', model: ArrayBuffer, ortWasm: ArrayBuffer })` before connecting nodes. The worklet instantiates the runtime from those bytes.
- We use `onnxruntime-web` with the WASM (not WebGL/WebGPU) backend. SIMD is enabled if available.
- The model is committed under `extension/vendor/silero_vad.onnx`. Source: `snakers4/silero-vad` v5.1, ONNX export. Add a `vendor/README.md` documenting origin, version, and license (MIT).

### 3.6 DOM observer (`dom-observer.ts`, runs in isolated world)

The job: turn `streamId → ssrc` (known from the WebRTC tap) into `streamId → { displayName, participantId, isLocalUser, isActive }`.

Hooks confirmed from the saved Meet DOM (`docs/google-meet-dom.html`):

| Selector / attribute | Meaning | Notes |
|---|---|---|
| `[data-participant-id]` | Stable per-participant tile root | Format: `spaces/{spaceId}/devices/{n}` |
| `[data-tile-media-id]` | Tile↔media binding | Same value as `data-participant-id` for the primary feed |
| `[data-ssrc]` | WebRTC SSRC declared in DOM | **Primary key** for binding a track to a tile |
| `[data-meeting-title]` | Meeting title | Read once at start |
| Animation name `speaker-border-glow-animation` | Active speaker | Detect via `getAnimations()` on the tile or via `animationstart` event |

Algorithm:

1. On content script load, observe `document.body` with `subtree: true, attributes: true, childList: true, attributeFilter: ['data-ssrc', 'data-participant-id', 'class']`.
2. Maintain a map `ssrc -> { participantId, displayName, tileEl, isLocal }`.
3. Display name resolution: walk up from `[data-participant-id]` to the tile root, then query for the visible name node. **Don't hardcode class names.** Strategy:
   - Prefer `[role="img"][aria-label]` inside the tile (avatar with name as label) when present.
   - Fall back to the largest text node in the tile that is not a single character and is not a button label.
   - If nothing, label as `"Speaker N"` (incrementing) and let the user rename in the popup. PRD R2.
4. Local user detection: the tile containing the local mic is identified by combining (a) the SSRC from `addTrack` (local), (b) the tile that has `data-self-view` or equivalent self-only attributes. Fallback: the first tile rendered before any remote `track` event.
5. Active-speaker: listen for `animationstart` events on the document with `e.animationName === 'speaker-border-glow-animation'`; resolve the target's nearest `[data-participant-id]` ancestor; emit `{ kind: 'speaker_active', participantId, active: true, t }`. Reset on `animationcancel` / `animationend`. (Per PRD §5.3, free-from-DOM, no model.)

When a `track` event arrives in the main world with an SSRC that does not yet have a name, the isolated world delays sending `init` over the WebSocket up to **2 s** to wait for the DOM to populate, then commits with the best name available (real or `Speaker N`). PRD F1 acceptance: "Display names appear correctly in the api logs within 2 seconds."

### 3.7 Popup (`src/popup/`)

Minimal, functional UI. React + a single CSS file. Shows:

- **Status line**: `Idle` / `Recording (00:23)` / `Reconnecting…` / `Error: <msg>`.
- **Big toggle button**: Start / Stop recording. Disabled when not on a Meet tab or fake-Meet harness.
- **Connection indicator**: green/red dot to the api URL (from `chrome.storage.local`, default `ws://localhost:8000`).
- **Participant list**: live, derived from messages relayed via `chrome.runtime.sendMessage` from the active content script. Each row shows display name, a mic icon when active speaker, an `[X]` to mute capture for that stream (sends `{ kind: 'mute', streamId }` to content script — content stops forwarding PCM but does not close the WS).
- **Local-mic toggle**: "Capture my mic" checkbox. Default on.
- **Settings link** (collapsible): api URL textbox.

Popup ↔ background ↔ content messaging uses `chrome.runtime.onMessage`. Popup talks only to background; background relays to/from the active tab's content script.

### 3.8 Background service worker (`background.ts`)

Lifecycle owner for the popup ↔ content bridge. MV3 service workers can be killed at any time; treat as stateless. Persistent state lives in `chrome.storage.local`.

Responsibilities:
- Read/write settings (api URL, capture-mic flag).
- On popup → background → content "Start", broadcast to the active Meet tab.
- Keep no in-memory state about meetings — content script is authoritative.

### 3.9 WebSocket client (`ws-client.ts`)

One client per stream. Owns the lifecycle of a single WS to the api:

- URL: `${apiBase}/ingest/{meeting_id}/{stream_id}` (PRD §9.1).
- On open: send the `init` text frame (schema in §6.2).
- On PCM frame from worklet: send as binary.
- On VAD/control event: send as text frame.
- On stream end (track ended, page unload, user stop): send `{ "type": "stream_end" }` then close.
- Reconnect with exponential backoff (1 s → 2 s → 5 s → 10 s, capped) up to 5 attempts. On reconnect, **resend `init`** with the same `stream_id` — the api treats this as a resumed stream and appends to the same WAV file. Audio captured during disconnect is dropped (Phase 1 acceptance does not require gap-free recording on flaky network).
- Backpressure: if `ws.bufferedAmount > 1 MB`, drop incoming PCM frames and log a counter. (Realistic dev-machine load should never hit this on localhost.)

### 3.10 Build (`vite.config.ts`)

- `pnpm` as package manager.
- Vite + `@crxjs/vite-plugin` (or hand-rolled multi-entry — `@crxjs` is fine for MV3 dev with HMR).
- TypeScript strict mode.
- Three separate entries that **must not be bundled together**: `content.ts`, `injected.ts`, `audio-worklet.ts`. Worklets and main-world scripts can't share globals; each is its own bundle.
- Output to `extension/dist/`. `chrome://extensions → Load unpacked` points at `dist/`.
- `pnpm dev` watches; `pnpm build` produces a zippable artifact.

---

## 4. Backend (Phase 1 minimum)

### 4.1 docker-compose.yml services

| Container | Image | Purpose |
|---|---|---|
| `api` | built from repo `Dockerfile`, command `uvicorn tryniq.api.main:app` | FastAPI, WS terminator |
| `worker` | same image, command `taskiq worker tryniq.tasks:broker` | TaskIQ worker (idle in Phase 1; only the `ping` task is registered) |
| `redis` | `redis:7-alpine` | TaskIQ broker + pub/sub for UI events |
| `minio` | `minio/minio:latest` | Object storage; bucket `tryniq` auto-created |
| `postgres` | `pgvector/pgvector:pg16` | Bootstrap schema from `infra/postgres/init.sql` |

No `asr-*`, no `aggregator`, no `graph-builder`, no `ui`. Pipeline modules will be added under `src/tryniq/pipeline/` in their own phase — no new containers.

Health checks on every container (`redis-cli ping` for redis). `make up` blocks until all five are healthy. Target: <60 s on first run (PRD §12.2 target is `<3 minutes` for the full stack; Phase 1 is a subset).

### 4.2 api: FastAPI app

The repo-root `pyproject.toml` declares the `tryniq` package at Python `>=3.13` and uses `uv` for dependency management. Deps:

- `fastapi`, `uvicorn[standard]` (ws support)
- `pydantic`, `pydantic-settings`
- `taskiq`, `taskiq-redis`, `redis`
- `minio` (official client)
- `asyncpg`
- `structlog`

### 4.3 Endpoints

- `WS /ingest/{meeting_id}/{stream_id}` — see §6.2.
- `GET /health` — returns `{ "status": "ok", "minio": bool, "redis": bool, "pg": bool }`.
- `POST /meetings` — body `{ title?: string, meet_url?: string }` → `{ meeting_id }`. Creates the meeting row. The extension calls this when the user clicks **Start** *before* opening any WS. (Yes, this means the popup hits the api via REST first.) Also publishes `meeting_lifecycle` `started` to `meeting:{id}:events`.
- `POST /meetings/{id}/end` — marks status `final`. Called by the extension on user Stop or page unload. Also publishes `meeting_lifecycle` `ended` to `meeting:{id}:events`.
- `GET /meetings/{id}/events` — SSE stream that subscribes to Redis `meeting:{id}:events` and forwards JSON payloads. Phase 1 only carries lifecycle events; Phase 2+ adds transcript and graph patches.

### 4.4 WS handler behavior

1. Accept connection.
2. Wait up to 5 s for the first text frame; parse as `WSInit` (Pydantic model). On invalid → close 1008.
3. Open a streaming WAV writer to MinIO at `tryniq/meetings/{meeting_id}/streams/{stream_id}.wav`. The writer:
   - Holds an in-memory header that is patched on close (RIFF chunk size, data chunk size).
   - Streams body bytes via MinIO multipart upload (5 MB part size). On final close, finalize multipart.
   - On a resumed `init` (same `stream_id`, existing object): append by reading current size, continuing multipart sequence. If multipart is unrecoverable, write a sibling `{stream_id}.part2.wav` and log a warning. Phase 1 accepts the sibling-file fallback.
4. For each binary frame: write raw PCM to the WAV writer.
5. For text frames: validate as a control message (`vad_speech_start`, `vad_speech_end`, `speaker_active`, `speaker_renamed`, `stream_end`). Phase 1 only **logs** these (structured log), does not store them. Phase 2 will use them to drive `transcribe_live` task enqueueing.
6. On `stream_end` or socket close: finalize the WAV, log a summary `{ stream_id, bytes, duration_seconds, speaker_name }`.

### 4.5 Redis pub/sub (UI events) and TaskIQ broker

**Pub/sub.** Only one channel pattern in Phase 1: `meeting:{meeting_id}:events`. Phase 1 emits a single payload `kind`:

```json
{ "kind": "meeting_lifecycle", "event": "started", "meeting_id": "...", "t": "2026-04-30T12:00:00Z", "title": "..." }
{ "kind": "meeting_lifecycle", "event": "ended",   "meeting_id": "...", "t": "2026-04-30T12:30:00Z", "stream_count": 2, "total_bytes": 12345678 }
```

The api's SSE endpoint `GET /meetings/{id}/events` subscribes per client and forwards payloads. Phase 2+ adds `transcript_segment`, `graph_patch`, `transcript_finalized`, etc. on the same channel.

**TaskIQ broker.** Wired in `src/tryniq/tasks/__init__.py`:

```python
from taskiq_redis import ListQueueBroker
broker = ListQueueBroker(url=settings.redis_url)
```

Phase 1 registers a single `ping(payload: str) -> str` task used only as a smoke test in `GET /health` (returns `redis: true` only if `await ping.kiq("ok")` resolves successfully via the worker).

### 4.6 Postgres bootstrap

`infra/postgres/init.sql` creates the full schema from PRD §8.1, but Phase 1 only writes to `meetings`. The `pgvector` extension is enabled (`CREATE EXTENSION IF NOT EXISTS vector`) so future phases don't need a migration.

### 4.7 Configuration (`.env.example`)

```
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8000

POSTGRES_DSN=postgresql://tryniq:tryniq@postgres:5432/tryniq
REDIS_URL=redis://redis:6379/0

MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=tryniq
MINIO_SECRET_KEY=tryniq-secret
MINIO_BUCKET=tryniq
MINIO_SECURE=false

LOG_LEVEL=INFO
```

The extension's api URL is set in the popup; **never** baked into the bundle (PRD F15 acceptance: "No service hardcodes credentials or external URLs").

---

## 5. Fake-Meet harness

Located at `tests/fixtures/fake-meet/`. Served by `python -m http.server 9000` (or a tiny FastAPI; trivial). Visit `http://localhost:9000/`.

### 5.1 What it must mirror

The harness is **not** a clone of Meet. It is the smallest DOM that exercises every selector and event the extension relies on, so we can iterate without scheduling real calls. The contract:

- A `body` with `data-meeting-title="Fake Meet — local test"`.
- A "tile container" element (any tag, any class), inside which N participant tiles render.
- Each tile is a `<div>` with:
  - `data-participant-id="spaces/local/devices/{n}"`
  - `data-tile-media-id="spaces/local/devices/{n}"`
  - `data-ssrc="{ssrcAssignedByLocalRTC}"`
  - A child element containing the visible display name (e.g. `<div class="name">Alice</div>`).
  - A child element styled with a CSS class that runs an animation **named exactly `speaker-border-glow-animation`** when the participant is "actively speaking" (toggled via JS).
- A "self" tile rendered first (matches the local-user heuristic).

### 5.2 Audio path

`tests/fixtures/fake-meet/peer.html` opens two `RTCPeerConnection`s in the same page and pipes `alice.wav` / `bob.wav` (looping) through them as `MediaStreamTrack`s, so the extension's `track` event fires with real SSRCs. After negotiation, JS sets each tile's `data-ssrc` attribute to the SSRC reported by `pc.getStats()`. This mimics Meet's behavior of writing the SSRC into the DOM after the track is plumbed.

A "speaking" simulator toggles the active-speaker animation on a 2-second cadence between the two tiles, so DOM-observer logic (§3.6) is exercised without real voice activity detection.

### 5.3 What this proves

If the extension produces two clean WAV files in MinIO from the fake-Meet harness — one named `Alice.wav`-equivalent (i.e. `init.speaker.display_name === "Alice"`) and one `Bob` — then the WebRTC tap, AudioWorklet, VAD, DOM observer, name resolution, and WebSocket plumbing are all working. We can then go to a real Meet call with confidence, and any failures there are isolated to (a) Worker-scope WebRTC, (b) Meet-specific selector drift, (c) network path. Each of those has a focused mitigation.

---

## 6. Contracts

### 6.1 Bridge protocol (main ↔ isolated world)

```ts
// main → isolated
type FromMain =
  | { source: 'tryniq'; kind: 'tap_installed'; pcCount: number }
  | { source: 'tryniq'; kind: 'track'; streamId: string; trackId: string; ssrc: number; mid: string; isLocal: boolean }
  | { source: 'tryniq'; kind: 'pcm'; streamId: string; t: number; pcm: ArrayBuffer /* int16 LE */ }
  | { source: 'tryniq'; kind: 'vad'; streamId: string; event: 'speech_start' | 'speech_end'; t: number }
  | { source: 'tryniq'; kind: 'track_ended'; streamId: string };

// isolated → main
type FromIsolated =
  | { source: 'tryniq'; kind: 'init_worklet'; streamId: string; modelBytes: ArrayBuffer; ortWasm: ArrayBuffer }
  | { source: 'tryniq'; kind: 'stop'; streamId: string };
```

PCM is transferred via `Transferable` (ArrayBuffer), not copied.

### 6.2 WS init message (api side)

Pydantic model in `src/tryniq/models/ws_init.py`. TS mirror in `extension/src/types.ts`. (Hand-maintained for Phase 1; codegen is a Phase 2 chore.)

```json
{
  "type": "init",
  "meeting_id": "uuid",
  "stream_id": "uuid",
  "speaker": {
    "tile_id": "spaces/Z_yOKR9wZY0B/devices/64",
    "display_name": "Sarah Chen",
    "is_local_user": false
  },
  "audio_format": {
    "sample_rate": 16000,
    "encoding": "pcm_s16le",
    "channels": 1
  },
  "client_started_at": "2026-05-04T14:00:00Z",
  "client_version": "0.1.0"
}
```

Validation rules:
- `meeting_id` must exist in the `meetings` table; reject with close code 1008 if not.
- `display_name` empty → accepted but the api logs a warning; the extension is responsible for sending `Speaker N` in that case (PRD R2 fallback).
- `audio_format` is fixed in Phase 1: 16000 / pcm_s16le / 1. Anything else → 1008.

### 6.3 Storage layout

Per PRD §8.3:

```
tryniq/
  meetings/
    {meeting_id}/
      streams/
        {stream_id}.wav      # 16 kHz mono int16, VAD-gated speech only
```

WAV header is standard RIFF/WAVE. Sample rate 16000, bits 16, channels 1.

### 6.4 Postgres rows written in Phase 1

Only into `meetings`:

```sql
INSERT INTO meetings (id, title, started_at, meet_url, status)
VALUES ($1, $2, NOW(), $3, 'live');

UPDATE meetings SET ended_at = NOW(), status = 'final' WHERE id = $1;
```

No `persons`, no `meeting_participants`, no `utterances`. Those are Phase 2+ work.

---

## 7. Make targets

```
make up           # docker compose up -d, then wait for health
make down         # docker compose down -v
make logs         # tail api + worker logs
make ext-dev      # cd extension && pnpm dev
make ext-build    # cd extension && pnpm build
make fake-meet    # python -m http.server 9000 -d tests/fixtures/fake-meet
make psql         # docker compose exec postgres psql -U tryniq tryniq
make mc           # opens MinIO console (http://localhost:9001)
```

`make up` is the single command in PRD F15. Phase 1 satisfies it for the subset of services in §4.1.

---

## 8. Acceptance tests

These are the gates for declaring Phase 1 done. Each is a manual checklist; we automate later.

### 8.1 Fake-Meet harness — primary gate

1. `make up && make ext-build && make fake-meet`.
2. Load `extension/dist/` as unpacked.
3. Visit `http://localhost:9000/`.
4. Click extension → set api to `ws://localhost:8000` → Start.
5. Within 3 seconds, popup shows two participants: **Alice** and **Bob**, with active-speaker indicator alternating every 2 s.
6. After 30 s, click Stop.
7. In MinIO console (`http://localhost:9001`), `tryniq/meetings/{id}/streams/` contains exactly two WAV files.
8. Download both. In Audacity (or `ffprobe`):
   - Each is 16 kHz mono int16.
   - One contains only Alice's audio; the other only Bob's. **Zero cross-talk.**
   - Each file's duration is roughly the active-speaker share of the 30 s, ±20% (because of VAD gating on looped speech).
9. Postgres `SELECT * FROM meetings` shows the row with `status='final'`.
10. The api logs (and any active SSE client to `GET /meetings/{id}/events`) show `meeting_lifecycle` `started` and `ended` payloads. `redis-cli MONITOR` shows `PUBLISH meeting:{id}:events ...`.

### 8.2 Real Google Meet — confirmation gate

Same flow, but in a real two-person Meet between two laptops. Acceptance is the same as PRD F1:

- Two streams in MinIO, one per participant, with names matching what they joined with.
- Local mic produces a third stream tagged `is_local_user: true`.
- New participant joining mid-call produces a new stream within 3 s.
- Participant leaving stops their stream cleanly (`stream_end` logged).
- WebSocket drop and reconnect resumes capture into the same WAV file (or `.part2.wav` per §4.4).

### 8.3 Worker-scope detection (R1)

If §8.2 produces zero audio tracks, the popup must show the *"No audio tracks detected"* toast within 10 s, the api logs zero ingest connections, and we open a follow-up ticket for Worker patching. **This is an acceptable Phase 1 outcome** as long as the failure mode is observable. We do not block Phase 1 on solving R1.

### 8.4 Reliability spot-checks

- 10-minute fake-Meet run produces a single continuous WAV per speaker, no growth in error logs.
- `chrome://extensions → Errors` is empty after a full run.
- CPU on a 2020 MacBook Air stays under 25% combined for the two AudioWorklets + ONNX VAD.

---

## 9. Open questions / risks specific to Phase 1

These are decisions to revisit during implementation:

1. **`onnxruntime-web` inside an AudioWorkletProcessor.** Confirmed possible in principle (the runtime can be instantiated from raw WASM bytes) but not all builds expose a worklet-compatible entry. If it doesn't work, fallback A: run VAD on the main-world side after PCM postMessage (adds ~5 ms latency, fine). Fallback B: a much smaller hand-rolled energy + zero-crossing-rate VAD. Decide by end of day 1.

2. **SSRC stability across renegotiation.** Meet renegotiates SDP frequently; SSRCs *should* be stable per-track but `getStats()` may report transient zeros. The extension must tolerate `ssrc=0` for up to 2 s before sending `init` with `Speaker N`.

3. **Local-mic echo.** If the local user is unmuted in a quiet room with a remote participant unmuted on the same machine, the local stream may contain echoed remote audio. PRD R8. Phase 1 mitigation: just flag `is_local_user: true` and let downstream (Phase 2 aggregator) de-duplicate. No DSP in Phase 1.

4. **Multipart upload resume after WS drop.** MinIO's Python client supports multipart but mid-upload resumption across processes is awkward. The `.part2.wav` fallback (§4.4) is intentionally dumb. Revisit only if real-Meet runs hit it often.

5. **VAD model warmup time.** Silero's first inference is slow (~50 ms). Pre-warm it with a buffer of zeros during worklet `init` so the first real speech window doesn't drop.

6. **Permissions UX.** MV3 host_permissions for `meet.google.com/*` should auto-grant on install for an unpacked dev extension. For a packaged build later, we'll need to explain the prompt. Out of scope here.

---

## 10. Day-by-day plan

This phase is budgeted at ~2.5 working days. Order is chosen so the highest-risk piece (WebRTC tap) is validated first.

| Day | Morning | Afternoon | Validation |
|---|---|---|---|
| 1 | Repo skeleton, manifest, content + injected scripts, world bridge | WebRTC tap; verify `track` events fire on fake-Meet | Console log shows two tracks with SSRCs |
| 2 | AudioWorklet, resampler, Silero VAD wiring | DOM observer; name resolution; popup MVP | Popup shows Alice/Bob; VAD gates audio (visible in worklet logs) |
| 3 | api (FastAPI WS, MinIO writer, Redis pub/sub lifecycle, PG bootstrap) + worker (TaskIQ + `ping` task) | End-to-end fake-Meet test, then real-Meet test | §8.1 and §8.2 pass |

If §8.2 fails due to R1, we stop, log the detection, and Phase 1 is still "done" per §8.3 — Worker patching gets its own follow-up.

---

*End of Phase 1 spec.*
