# Tryniq Backend Constitution

This document is the **mandatory** style and structure guide for `backend/`. Every agent or contributor MUST read this file *before* writing or modifying any Python in this repo. It encodes conventions already present in the codebase — your job is to keep the codebase coherent with what is already here, not to introduce a new flavor.

If a rule below conflicts with `CLAUDE.md` (project root) or `docs/PRD.md`, those documents win on architectural questions; this document wins on code shape.

---

## 0. Read first

Before writing code:

1. Read this file end-to-end.
2. Skim the feature module nearest to your task (`app/<feature>/`) — match its shape exactly.
3. Read `pyproject.toml` for the linter ruleset and pinned line length (`ruff`, line-length 120, selected: `F E W C N I B Q T UP`).
4. Read `CLAUDE.md` at the repo root for the architectural commitments. **Do not** violate the two non-negotiables (per-speaker audio without live diarization; meetings as graphs).

---

## 1. Language & runtime

- Python **3.13**. Use native PEP 604 unions (`X | Y`), PEP 585 generics (`list[int]`, `dict[str, X]`), and PEP 695 `type` aliases.
- **Never** add `from __future__ import annotations`. Remove it if you find it.
- Async-only in the API process. No blocking I/O on the request path; CPU/GPU/LLM work belongs in the worker via TaskIQ tasks.
- Use new generic syntax for decorators/functions when generics are needed: `def f[T](...) -> T: ...` and `def deco[**P, R](func: Callable[P, Awaitable[R]]) -> ...`. See `app/core/decorators.py`.

---

## 2. Module layout

Each feature lives under `app/<feature>/` and uses **only** these filenames (omit any that are not needed):

```
app/<feature>/
    __init__.py
    router.py          # FastAPI router (or routers/ package if multiple)
    service.py         # business logic; class <Feature>Service
    schemas.py         # Pydantic request/response models
    models.py          # SQLModel ORM tables
    dependencies.py    # FastAPI Depends wiring + *Dep aliases
    client.py          # external client wrappers (Redis, MinIO, HTTP, etc.)
    config.py          # pydantic-settings sub-block for this feature
    constants.py       # enums, regexes, channel/key templates
    exceptions.py      # feature-specific subclasses of app.core.exceptions
    tasks.py           # TaskIQ task definitions
```

If a feature has multiple routers, use `routers/` package (see `app/meeting/routers/`). Do **not** invent new top-level filenames without precedent.

`__init__.py` files stay empty unless there is a deliberate public API to re-export.

---

## 3. Imports

- Absolute imports, always rooted at `app.` — never relative (`from .service import ...`).
- Order (ruff `I` enforces this): stdlib → third-party → `app.*`. One blank line between groups.
- Import sorting is alphabetical within each group.
- **Do not** import from another feature's internals to avoid a cycle — instead, do a *local* import inside the function (see `MeetingService._enqueue_finalization` importing `transcribe_final` from `app.asr.tasks`). This pattern is intentional; preserve it.

---

## 4. FastAPI routers

- One `APIRouter` per `router.py`, named `router`. Set `prefix` and `tags` at construction.
- Endpoints are thin: validate input → call service → return `Schema.model_validate(...)`. No business logic here.
- Always specify `response_model`, `status_code` (use `starlette.status` constants), `summary`, `description`, and `responses=` for documented errors. Match the verbosity of `app/meeting/routers/meeting.py`.
- Endpoint signatures use `*Dep` annotated dependencies and a Pydantic body parameter named `body`. Path parameters keep their semantic name (`id`, not `meeting_id`).
- Return Pydantic response models built via `Model.model_validate(orm_instance)` — never return ORM rows directly.
- Health/utility endpoints live in `main.py`.
- `main.py` is the only place that calls `app.include_router(...)`, sets middleware, and registers the lifespan and exception handler.

---

## 5. Dependencies

- Every service is wired through a small factory function and an `Annotated[..., Depends(...)]` alias suffixed `Dep`:

  ```python
  def get_meeting_service(session: SessionDep) -> MeetingService:
      return MeetingService(session)

  MeetingServiceDep = Annotated[MeetingService, Depends(get_meeting_service)]
  ```

- Resource-loading dependencies (e.g. `get_meeting`) raise the feature's `NotFoundError` from inside the service; do not put 404 logic in the dependency.
- Process-wide singletons (clients with state, e.g. `LiveASRClient`) use `@lru_cache(maxsize=1)` on the factory (see `app/asr/dependencies.py`). Plain module-level singletons (`redis_client = RedisClient()`) are also acceptable for stateless wrappers.

---

## 6. Services

- One class per `service.py`, named `<Feature>Service`.
- Constructor takes its dependencies (typically `AsyncSession` + sibling services) and stores them on `self.session` / `self.<dep>`. Use a leading underscore (`self._session`) only when the service hides the session from callers (see `IngestService`); otherwise keep it public.
- Public methods are verbs in present tense: `create`, `retrieve`, `list`, `update`, `get_by_stream`, `mark_no_audio`. Avoid `get_or_*` unless the operation truly is upsert-shaped (`get_or_create_room`).
- Private helpers prefixed `_`. `@staticmethod` for pure helpers that don't touch `self`.
- Persistence pattern (canonical, copy this):

  ```python
  async def _save(self, instance: Model) -> Model:
      self.session.add(instance)
      await self.session.commit()
      await self.session.refresh(instance)
      return instance
  ```

- Queries: prefer `sqlmodel.select` + `await self.session.exec(query)`; terminate with `.one()`, `.one_or_none()`, or `.all()`. Use `sqlalchemy.dialects.postgresql.insert` for `ON CONFLICT`.
- Use `selectinload` for explicit relationship loading; `Relationship(sa_relationship_kwargs={"lazy": "raise"})` is the project default — code MUST opt in to loads.
- Raise feature-specific errors (`MeetingNotFoundError()`) instead of `HTTPException` — the global handler converts them.
- Never construct `HTTPException` in a service. Never call `logger.exception` for expected control-flow errors.

---

## 7. Schemas (Pydantic)

- Inherit from `app.core.base_schema.BaseSchema` (sets `from_attributes=True`). Update payloads inherit from `UpdateSchema` (which enforces "at least one field provided").
- One file per feature, named `schemas.py`. Group request/response/event types here.
- Naming: `<Noun>CreateRequest`, `<Noun>UpdateRequest`, `<Noun>Response`, `<Noun>Event`.
- Discriminated unions use `type X = Annotated[A | B | C, Field(discriminator="kind")]` and a sibling `TypeAdapter` named `<NAME>_ADAPTER` (see `app/asr/schemas.py`, `app/meeting/schemas.py`). Use the PEP 695 `type` keyword, not `TypeAlias`.
- Wire-format event schemas (those exchanged with workers/extension) inherit from a small `_BaseEvent` with `model_config = {"extra": "forbid"}` and a `kind: Literal[EnumValue] = EnumValue` field. Do **not** mix `extra="forbid"` into general response schemas.
- Do not subclass `BaseModel` directly in feature code — go through `BaseSchema` (or `_BaseEvent` for wire formats).

---

## 8. Models (SQLModel)

- One table per class. Always set:

  ```python
  __tablename__ = "snake_case"
  model_config = SQLModelConfig(extra="allow")
  ```

- Use the mixins in `app/core/database.py`: `IDMixin` (UUID PK with `uuid4` default) and `TimestampMixin` (created_at / updated_at, timezone-aware, with auto-update event listener). MRO: `class Foo(IDMixin, TimestampMixin, SQLModel, table=True): ...`.
- Datetimes are timezone-aware UTC: `Field(default_factory=lambda: datetime.now(tz=UTC), sa_type=DateTime(timezone=True))`. Never use naive datetimes.
- Foreign keys: `Field(foreign_key="<table>.id", index=True)`. JSONB columns: `Field(sa_column=Column(JSONB, nullable=True))`.
- Relationships default to `lazy="raise"`. Loading is explicit at the query site.
- Schema migrations live in `alembic/`. Never edit a committed migration; create a new one.

---

## 9. Configuration

- All settings flow through `pydantic-settings`. Each feature owns a `<Feature>Settings(BaseSettings)` class in `<feature>/config.py` with:

  ```python
  model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="<FEATURE>_")
  ```

  using `BASE_MODEL_CONFIG` from `app/core/config.py`.
- The root `Settings` aggregator lives in `app/config.py` and is exposed as `config = Settings.get_instance()` (`@lru_cache`-cached). All code reads `from app.config import config` and accesses `config.api.*`, `config.asr.*`, etc.
- Field names are **UPPER_SNAKE_CASE** inside settings classes (matches env var names). Sub-block attribute names on the root `Settings` are **lowercase** (`api`, `asr`, `redis`).
- Secrets use `pydantic.SecretStr`. Read with `.get_secret_value()` only at the point of use.
- Do **not** read `os.environ` directly. Add a setting instead.

---

## 10. Logging

- Always: `import structlog` then `logger = structlog.get_logger()` at module top.
- Structured key/value logging only — never f-strings as the message:

  ```python
  logger.debug("meeting is created", id=meeting.id, room_id=room.id)
  ```

- Levels:
  - `debug` — routine state changes, control-flow checkpoints.
  - `info` — lifecycle milestones (startup, promotions, completed long-running jobs).
  - `warning` — recoverable anomalies (bad client payload, missing optional resource).
  - `exception` — unexpected exceptions you caught; use only inside `except`.
- Logging is configured once via `app.logger.configure_logging()` from the lifespan. Don't reconfigure elsewhere.

---

## 11. Exceptions

- Base hierarchy in `app/core/exceptions.py`: `AppError` → `NotFoundError`, `BadRequestError`, `ForbiddenError`, `UnauthorizedError`, `ConflictError`. The global handler in `register_exception_handler` maps these to JSON.
- Feature-specific exceptions live in `<feature>/exceptions.py`, subclass the appropriate `AppError` child, take no arguments, and pass a fixed `detail` string:

  ```python
  class MeetingNotFoundError(NotFoundError):
      def __init__(self) -> None:
          super().__init__("Meeting not found")
  ```

- Do not catch `Exception` broadly. Catch the narrowest set you actually expect (e.g. `(RedisError, SQLAlchemyError)`, `(ValidationError, json.JSONDecodeError)`). The one acceptable broad catch is around best-effort cleanup (see `IngestService._finalise`), and it must log at `debug`/`warning` and continue.

---

## 12. Background tasks (TaskIQ)

- Tasks live in `<feature>/tasks.py`, decorated with `@broker.task(retry_on_error=True, max_retries=...)` from `app.tasks`.
- **Task arguments are primitives only** (str, int, IDs as strings). No bytes, no Pydantic models, no large blobs. Pass Redis Stream keys / object keys / row IDs.
- Tasks must be idempotent — TaskIQ retries on failure. Check-before-insert, use stable IDs, and persist resumable state (e.g. XREAD cursors via `redis_store.set_cursor`) for long-lived coroutines.
- Task body opens its own `async_session()` and constructs services explicitly:

  ```python
  @broker.task(retry_on_error=True, max_retries=2)
  async def transcribe_final(meeting_id: str, stream_id: str) -> None:
      async with async_session() as session:
          service = FinalASRService(ParticipantService(session), ...)
          await service.run(UUID(meeting_id), UUID(stream_id))
  ```

- Enqueue with `await some_task.kiq(...)` from the API process.

---

## 13. Redis & messaging

- Channel/key names are templates declared in `<feature>/constants.py` (`EVENT_CHANNEL`, `PARTIAL_KEY`, …). Never inline `f"meeting:{id}:events"` at call sites.
- Publish via the `RedisClient` helpers (`publish_meeting_lifecycle`, `publish_partial_transcript`, `publish_transcript_segment`). Do not call `client.publish` ad-hoc from services.
- Keep the data-lifetime contract:
  - Postgres = durable.
  - Redis pub/sub = ephemeral UI.
  - Redis Stream = in-flight audio.
  - Redis key+TTL = recovery.
  - MinIO = audio at rest + exports.
- Never put PCM bytes in TaskIQ task arguments — use the Redis Stream `audio:{stream_id}`.

---

## 14. WebSockets

- Accept first (`await ws.accept()`), then validate handshake / first message with `asyncio.wait_for(...)` if a timeout matters, then enter the consume loop.
- Reject malformed clients with `await ws.close(code=status.WS_1008_POLICY_VIOLATION)` and a `logger.warning`.
- Wrap top-level handlers with `@suppress_ws_disconnect` from `app/core/decorators.py` when a clean disconnect is normal.
- Validate every inbound text frame through a `TypeAdapter` (`CONTROL_ADAPTER`, `CLIENT_MESSAGE_ADAPTER`) — never `json.loads` and trust the result.

---

## 15. Style & formatting

- `ruff` is the source of truth. Run `ruff check` and `ruff format` before declaring work complete. Line length 120.
- Every function and method has a return type annotation. Parameters are annotated. `-> None` is explicit, not implied.
- No docstrings, let names and types speak.
- No comments.
- No emojis in code.
- String quoting: double quotes are the norm (ruff `Q` rule). Single quotes only inside an f-string when needed.
- Prefer `pathlib.Path` over `os.path`. Prefer `enum.StrEnum` over string literals for closed sets.
- Prefer early returns over nested `else` branches.
- Truthy checks for non-numeric / non-string types: prefer `if not x` / `if x` over `if x is None` / `if x is not None` for objects, models, collections, UUIDs, datetimes, and other reference types — it reads cleaner. Reserve `is None` for primitives where a falsy non-None value (`0`, `0.0`, `""`, `False`) is a meaningful, distinct case from absence.
- Inject collaborators via `__init__`; do not instantiate them inside the class. Constructor parameters are required and typed; no `dep: Foo | None = None` "optional" placeholders that fall back to `Foo()`. The composition root (FastAPI dependency factories in `<feature>/dependencies.py`, or the task body) owns construction. This keeps classes testable and the wiring explicit.
- Per-function size cap: keep functions under ~80 lines of code. If you cross that, split into helpers; method names paired with `_StreamResult`-style local dataclasses are preferable to long inline state.

---

## 16. Naming

- Modules: `lower_snake_case.py`. Packages: `lower_snake_case/`.
- Classes: `PascalCase`. Functions/methods/variables: `lower_snake_case`. Constants/enum members/settings fields: `UPPER_SNAKE_CASE`.
- Dependency aliases end in `Dep` (e.g. `MeetingServiceDep`).
- TypeAdapter constants end in `_ADAPTER`.
- Schema suffixes: `Request`, `Response`, `Event`. Discriminator field is named `kind`.
- Enums: `<Domain>Status`, `<Domain>EventKind`, `<Domain>Event` (lifecycle).

---

## 17. Doing the right amount

- Do not add error handling, fallbacks, or validation for situations that can't happen. Trust internal callers; validate only at boundaries (HTTP, WS, external services).
- Do not introduce new abstractions speculatively. Three similar lines beat a premature helper.
- Do not add backwards-compat shims, feature flags, or `# removed` placeholders. Delete what is unused.
- Match the scope of the change to the task. A bug fix is not a refactor.

---

## 18. When you're not sure

1. Find the closest existing example in the codebase (the modules under `app/meeting/`, `app/participant/`, `app/transcript/`, `app/ingest/`, `app/asr/` are the canonical references).
2. Mirror it exactly — names, layout, helpers, log style.
3. If still unclear, ask before inventing. Do not "improve" patterns that are already consistent across the codebase.
