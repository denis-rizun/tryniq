# Tryniq Streamer Constitution

This document is the **mandatory** style and structure guide for `streamer/`. Every agent or contributor MUST read it *before* writing or modifying any Swift in this module. It encodes conventions already present in the codebase — your job is to keep the codebase coherent with what is already here, not to introduce a new flavor.

If a rule below conflicts with `CLAUDE.md` (project root) or `docs/PRD.md`, those documents win on architectural questions; this document wins on code shape. The wire protocol is co-owned with `backend/app/asr/schemas.py` — that file is the source of truth for field names and discriminators.

---

## 0. Read first

Before writing code:

1. Read this file end-to-end.
2. Read `backend/app/asr/schemas.py` and `backend/app/asr/router.py` — the streamer is a wire-protocol peer of the backend's ASR session router.
3. Read `CLAUDE.md` at the repo root for the architectural commitments. **Do not** violate the two non-negotiables (per-speaker audio without live diarization; meetings as graphs).

---

## 1. Language & runtime

- Swift **6.0**, `swift-tools-version: 6.0`. macOS 14+.
- Strict concurrency: every long-lived component is an `actor`; closures crossing actor boundaries are `@Sendable`.
- Single executable target named `streamer`, sources rooted at `src/` (set via `path: "src"` in `Package.swift`).
- Run with `swift run streamer` from this directory.
- The CoreML weights for Parakeet TDT v2 (FluidAudio) are downloaded on first run and cached by FluidAudio. Don't re-download or vendor them.

---

## 2. Module layout

All sources live flat in `src/`. One responsibility per file. **Hard cap: 150 lines per file.** If you cross it, split.

Current shape (mirror it):

```
streamer/
    Package.swift
    Package.resolved
    Makefile
    .env / .env.example
    src/
        main.swift                  # entrypoint: env load → model load → run socket
        EnvLoader.swift             # .env file parser
        BackendSocket.swift         # websocket lifecycle + reconnect loop
        SessionManager.swift        # registry of per-stream transcribers; control-message dispatch
        SpeakerTranscriber.swift    # one speaker's ASR loop (FluidAudio sliding window)
        AsrConfigBuilder.swift      # env → SlidingWindowAsrConfig
        TranscriptTiming.swift      # (t_start, t_end) derivation from updates
        TranscriptPublisher.swift   # encodes & sends partial/final frames
        PCMBufferDecoder.swift      # int16 LE bytes → AVAudioPCMBuffer (Float32)
        BinaryAudioFrame.swift      # 8-byte LE header parser for inbound PCM
        Messages.swift              # all wire-format Codable structs
```

Rules:
- One class/actor/enum per file. Pure data structs (wire messages) may share `Messages.swift` because they have no logic.
- File name == primary type name (`SpeakerTranscriber.swift` defines `SpeakerTranscriber`).
- Don't invent subfolders without precedent.

---

## 3. Concurrency

- Long-lived stateful components are `actor`s (`BackendSocket`, `SessionManager`, `SpeakerTranscriber`, `TranscriptPublisher`).
- Pure helpers are `enum`s with `static` methods (`EnvLoader`, `PCMBufferDecoder`, `AsrConfigBuilder`, `TranscriptTiming`). Never instantiate these.
- Callbacks crossing actors are `@escaping @Sendable (...) async -> Void`.
- Use structured `Task { ... }` for long-lived work owned by an actor; cancel in the actor's teardown method (see `SpeakerTranscriber.finish()`).
- `Task.isCancelled` is the loop exit signal. Don't poll flags.

---

## 4. Wire protocol

The wire protocol must stay byte-for-byte compatible with `backend/app/asr/schemas.py`:

- **Discriminator field is `kind`** (not `type`). Match the backend's `EventKind` enum values literally (`"hello"`, `"stream_open"`, `"stream_close"`, `"partial"`, `"final"`, `"ping"`).
- Field names on wire-format structs are **snake_case** (`stream_id`, `t_start`, `worker_id`) because they map directly to backend Pydantic fields. Do not `CodingKeys`-rename — keep snake_case property names on the structs.
- Outbound messages: `Encodable`. Inbound messages: `Decodable`. `PingMessage` is `Codable` (bidirectional).
- Inbound text frames go through `IncomingMessageEnvelope` first to extract `kind`, then are decoded into the concrete message type — never trust raw JSON.
- Binary inbound frames have an **8-byte little-endian header**: `streamIdx: UInt32`, `sequence: UInt32`, then int16 LE PCM at the sample rate negotiated in `stream_open` (16 kHz mono).
- If you change the wire format, update `backend/app/asr/schemas.py` in the same change. They ship together.

---

## 5. Connection lifecycle

`BackendSocket.runForever()` is the canonical pattern. Preserve its shape:

1. Connect → resume task → send `HandshakeMessage`.
2. Receive loop dispatches `.string` to `SessionManager.handleControlText` and `.data` to `SessionManager.feedPCM`.
3. On error: log to stderr, sleep with exponential backoff (1s, 2s, 4s, …, capped at 30s), reconnect.
4. On reconnect, in-flight stream sessions are dropped; the backend will issue fresh `stream_open` messages. **Reconnect is lossy by design** — `transcribe_final` on the backend recovers the transcript post-meeting. Do not add replay buffers.

---

## 6. Errors & logging

- Errors and lifecycle messages go to **stderr** via `FileHandle.standardError.write(Data("...\n".utf8))`. `print(...)` is for routine startup info only.
- No third-party logging library — match the existing style.
- Don't catch errors silently. The acceptable patterns are:
  - `try? await task.send(...)` for best-effort outbound writes (the receive loop will detect a dead socket).
  - `try? JSONDecoder().decode(...)` for inbound message decode (a malformed frame is dropped, not fatal).
  - Explicit `do { try await ... } catch { stderr.write(...) }` for setup steps that should surface failure but not crash (`SpeakerTranscriber` init, `manager.finish()`).
- `exit(1)` / `exit(2)` only in `main.swift`, only for unrecoverable startup failure (missing token, model load failure).

---

## 7. Configuration

- All runtime config comes from environment variables. Read them in `main.swift` or in a single static helper (`AsrConfigBuilder.fromEnvironment()`).
- `.env` files are loaded by `EnvLoader` from (a) the current working directory and (b) the project root. Existing process env wins over `.env`.
- Required vars: `WORKER_TOKEN`. Optional: `BACKEND_WS_URL` (default `ws://localhost:8000`), `WORKER_ID` (default random UUID), `ASR_CHUNK_S`, `ASR_RIGHT_CTX_S`, `ASR_LEFT_CTX_S`, `ASR_MIN_CONFIRM_S`.
- New env vars are documented in `.env.example` and consumed via `ProcessInfo.processInfo.environment`. Do not read `getenv` directly.
- No hardcoded credentials, hostnames, or model URLs.

---

## 8. ASR specifics

- `FluidAudio.SlidingWindowAsrManager` is the only ASR engine. Do not introduce alternatives on the live path.
- One `SpeakerTranscriber` per speaker stream. Models (`AsrModels`) are loaded **once** in `main.swift` and shared across all transcribers — don't reload per stream.
- Updates from `manager.transcriptionUpdates` map to the wire protocol as:
  - `update.isConfirmed == false` → `partial` (skipped if `text` is empty).
  - `update.isConfirmed == true` → `final`.
- `t_start` / `t_end` come from `tokenTimings` when present, else from cumulative `samplesProcessed / sampleRate` (see `TranscriptTiming`).
- Don't run VAD or diarization here — the extension's audio worklet already gates on Silero VAD, and live diarization is explicitly out of scope (per `CLAUDE.md` architectural commitment 1).

---

## 9. Style & formatting

- No comments. No docstrings. Names and types must carry the meaning.
- No emojis in code or strings.
- Types: `PascalCase`. Functions, methods, variables, properties: `lowerCamelCase`. Wire-format fields keep `snake_case` to match the backend.
- Prefer `enum` namespaces (`enum Foo { static func ... }`) over free functions or singleton classes for stateless helpers.
- Prefer early `guard ... else { return }` over nested `if`.
- Use `actor` whenever there is mutable state shared across `await`-points. Don't reach for `DispatchQueue` or locks.
- File ends with a single trailing newline. No trailing whitespace.

---

## 10. Naming

- File names match the primary type they define.
- Type suffixes: `Message` for wire-format payloads, `Frame` for binary payloads, `Loader` / `Builder` / `Decoder` / `Publisher` / `Manager` / `Transcriber` for behavior types — pick the one that already exists in the module.
- Discriminator field is `kind` (matches backend).
- Async callbacks use verbs in present tense: `onPartial`, `onFinal`. Don't prefix with `did` or `will`.

---

## 11. Doing the right amount

- Do not add error handling, fallbacks, or validation for situations that can't happen. Trust the backend's protocol contract; validate only at the wire boundary (`IncomingMessageEnvelope` decode, `BinaryAudioFrame.parse`).
- Do not introduce new abstractions speculatively. Three similar lines beat a premature helper.
- Do not add backwards-compat shims or `// removed` placeholders. Delete unused code.
- A bug fix is not a refactor. Match the scope of the change to the task.

---

## 12. When you're not sure

1. Find the closest existing example in `src/` and mirror it exactly — names, layout, error handling, actor isolation.
2. Cross-check the wire protocol against `backend/app/asr/schemas.py`. If the two disagree, the backend wins and you update the streamer.
3. If still unclear, ask before inventing.
