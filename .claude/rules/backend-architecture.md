---
paths:
  - "backend/**/*.py"
---

# Backend Architecture

Binding rules for module layout, imports, FastAPI routers, dependencies, and services. Mirror the shape of the nearest existing feature module — do not introduce new flavors.

## Foundational principles (must-have)

- **Organized by domain** — code that changes together lives together.
- **Follows [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) conventions.**

## Module layout

Each feature lives under `app/<feature>/` and uses **only** these filenames (omit any that are not needed):

```
app/<feature>/
    __init__.py
    router.py          # FastAPI router (or routers/ package if multiple)
    service.py         # business logic; class <Feature>Service
    tasks.py           # TaskIQ task entrypoints
    schemas.py         # Pydantic request/response models
    models.py          # SQLModel ORM tables
    dependencies.py    # FastAPI Depends wiring + *Dep aliases
    client.py          # external client wrappers (Redis, MinIO, HTTP, etc.)
    config.py          # pydantic-settings sub-block for this feature
    constants.py       # enums, regexes, channel/key templates
    exceptions.py      # feature-specific subclasses of app.core.exceptions
```

If a feature has multiple routers, use `routers/` package. Features with several external-client wrappers may use a `clients/` package (for example, upload and asr); do not keep both `client.py` and `clients/`. Features with several service collaborators may use a `services/` package, with the primary `<Feature>Service` in `services/<feature>.py` (for example, metadata). Keep one top-level responsibility per file. Producer-owned DTO dataclasses live with their producer, not in `constants.py`. Do **not** invent new top-level filenames without precedent.

`__init__.py` files stay empty unless there is a deliberate public API to re-export.

## Imports

- Absolute imports, always rooted at `app.` — never relative (`from .service import ...`).
- Order (ruff `I` enforces this): stdlib → third-party → `app.*`. One blank line between groups.
- Import sorting is alphabetical within each group.

## FastAPI routers

- One `APIRouter` per `router.py`, named `router`. Set `prefix` and `tags` at construction.
- Endpoints are thin: validate input → call service → return `Schema.model_validate(...)`. No business logic here.
- Always specify `response_model`, `status_code` (use `starlette.status` constants), `summary`, `description`, and `responses=`.
- **`responses=` must enumerate every error status the endpoint can produce**, even when the error originates upstream (`permission_required`, a resource-loader `*Dep`, a service raising its feature `AppError`). Each entry uses the shared `app.core.base_schema.ErrorResponse` and a one-line `description` of the trigger — this is the OpenAPI contract; if it isn't listed, it shouldn't happen. 422 is documented automatically by FastAPI — do not repeat it. Write each endpoint's dict explicitly inline — do not extract shared `_UNAUTHORIZED`-style module constants. Checklist when writing an endpoint:
  - `400` whenever the service may raise a `BadRequestError` (invalid input, unresolvable reference, ungrounded extraction)
  - `401` whenever `CurrentUserDep` / `permission_required(...)` is in the dependency chain
  - `403` whenever a `permission_required(...)` could fail
  - `404` whenever a resource-loader `*Dep` is used or the service may raise a `NotFoundError`
  - `409` whenever the service may raise a `ConflictError` (unique violation, FK conflict, business rule)

  > **Auth/RBAC is planned, not yet built.** There is no `CurrentUserDep`, `permission_required`, or `Permission` enum in the codebase today. The `401`/`403` guidance and the `dependencies=[...]` in the example below are the **target pattern** for when auth lands — wire them through `<feature>/dependencies.py` (see the Dependencies section) and drop the `401`/`403` rows from any endpoint left public. Until then, real endpoints carry only `400`/`404`/`409`.

  ```python
  @router.get(
      "/sessions/{id}",
      response_model=ChatSessionDetailResponse,
      status_code=status.HTTP_200_OK,
      summary="Get chat session",
      description="Get a chat session with all its messages.",
      responses={
          401: {"model": ErrorResponse, "description": "Not authenticated"},
          403: {"model": ErrorResponse, "description": "Insufficient permissions"},
          404: {"model": ErrorResponse, "description": "Session not found"},
      },
      dependencies=[Depends(permission_required(Permission.CHATS_READ))],
  )
  async def get_session(session: ChatSessionDep, service: ChatServiceDep) -> ChatSessionDetailResponse:
      return await service.retrieve_with_messages(session)
  ```
- Endpoint signatures use `*Dep` annotated dependencies and a Pydantic body parameter named `body`. Path parameters keep their semantic name (`id`, not `meeting_id`).
- Return Pydantic response models built via `Model.model_validate(orm_instance)` — never return ORM rows directly.
- **No-content endpoints return `None`**, with `status_code=status.HTTP_204_NO_CONTENT` and `response_model=None` declared on the decorator. Never construct and return `Response(status_code=...)` from a handler.
- Health/utility endpoints live in `main.py`.
- `main.py` is the only place that calls `app.include_router(...)`, sets middleware, and registers the lifespan and exception handler.
- **Path naming**: lowercase, plain words. Prefer nested sub-resources (`/meetings/{id}/graph`, `/meetings/{id}/streams`) over kebab-cased compound nouns (`/meeting-graph`). Only fall back to kebab-case when the noun itself is genuinely a multi-word concept with no clean parent (`/action-items`). Never `snake_case` or `camelCase` in paths.
- **Query params**: only wrap in `Annotated[..., Query(...)]` when the `Query(...)` carries actual configuration — validation (`ge`, `le`, `min_length`, `max_length`, `pattern`), an `alias`, a non-default `description`, or `deprecated`. An empty `Query()` carries no configuration, so `param: Annotated[T | None, Query()] = None` is exactly `param: T | None = None` — drop the wrapper. Without config, FastAPI already infers the param as a query string from the function signature, and the `Query()` wrapper is dead weight. Plain `param: T | None = None` (or `param: T = <default>`) is the norm — this holds for enum-typed params (`scope: ChatScope | None = None`) too; reach for `Annotated[..., Query(...)]` only for the params that actually need it. Example:

  ```python
  async def list_meetings(
      service: MeetingServiceDep,
      room_id: str | None = None,
      limit: Annotated[int, Query(ge=1, le=1000)] = 100,
      offset: Annotated[int, Query(ge=0)] = 0,
  ) -> list[MeetingResponse]:
      ...
  ```

## Dependencies

- **All FastAPI dependency wiring lives in `<feature>/dependencies.py`** — service factories, `*Dep` aliases, resource-loader deps, and (once auth lands) any auth/RBAC dep factories such as `permission_required`. `service.py` defines the class only; `router.py` imports `*Dep` aliases. Never declare a `Depends(...)` at module scope outside `dependencies.py`.
- Every service is wired through a small factory function and an `Annotated[..., Depends(...)]` alias suffixed `Dep`:

  ```python
  def get_any_service(session: SessionDep) -> AnyService:
      return AnyService(session)

  AnyServiceDep = Annotated[AnyService, Depends(get_any_service)]
  ```

- Resource-loading dependencies are named `get_<entity>` with an `<Entity>Dep` alias — never `get_<entity>_by_id` / `<Entity>ByIdDep`. They call the service's `retrieve` and let it raise the feature's `NotFoundError`. Endpoints that operate on a single resource declare the loader `*Dep` directly so the path-param lookup happens once per request, not in every handler:

  ```python
  async def get_meeting(id: UUID, service: MeetingServiceDep) -> Meeting:
      return await service.retrieve(id)

  MeetingDep = Annotated[Meeting, Depends(get_meeting)]
  ```

- Stateful collaborators are injected through `dependencies.py` factories — never instantiated at module scope inside `service.py`. Use `@lru_cache(maxsize=1)` on the factory when one instance per process is desired. Pure stateless helper **functions** (e.g., once auth lands, `hash_password` / `verify_password` backed by a module-level `PasswordHasher`) may live at module scope in the service module, above the class.
- Process-wide singletons (clients with state) use `@lru_cache(maxsize=1)` on the factory. Plain module-level singletons (`redis_client = RedisClient()`) are also acceptable for stateless wrappers; put them in `client.py`.

## Services

- One class per `service.py`, named `<Feature>Service` in **singular** form (`MeetingService`, `ParticipantService`, not `MeetingsService`). The service class stays singular even when it manages many rows.
- Constructor takes its dependencies (typically `AsyncSession` + sibling services or helpers) and stores them on `self.session` / `self.<dep>`. Use a leading underscore (`self._session`) only when the service hides the session from callers; otherwise keep it public.
- Never instantiate collaborators at module scope inside `service.py` (e.g. `_ai_client = AIClient()`). Inject them through `__init__` so tests can override them and so the composition root stays in `dependencies.py`.
- Public methods are verbs in present tense: `create`, `retrieve`, `list`, `update`, `get_by_stream`, `mark_no_audio`. Avoid `get_or_*` unless the operation truly is upsert-shaped (`get_or_create_room`).
- Private helpers prefixed `_`. `@staticmethod` for pure helpers that don't touch `self`.
- **Never reach a method through its own class name from inside the class** (`MeetingService._save(...)`). If a method needs to call another method of the same class, it is not standalone — make it an instance method (call via `self._x(...)`) or, when it must not touch instance state, a `@classmethod` and call via `cls._x(...)`. The bare-class-name call is the smell that says the method was mis-classified as a `@staticmethod`.
- Persistence pattern (canonical, copy this):

  ```python
  async def _save(self, instance: Model) -> Model:
      self.session.add(instance)
      await self.session.commit()
      await self.session.refresh(instance)
      return instance
  ```

- Queries: prefer `sqlmodel.select` + `await self.session.exec(query)`; terminate with `.one()`, `.one_or_none()`, or `.all()`. Use `sqlalchemy.dialects.postgresql.insert` for `ON CONFLICT`.
- **Always use `self.session.exec(...)`** — never `self.session.execute(...)`. sqlmodel's `AsyncSession.execute` is deprecated and emits a runtime warning; `exec` is the supported entry point and dispatches correctly for `select`, `update`, `delete`, and dialect inserts (`pg_insert(...).on_conflict_do_update(...)`). For DML statements whose typing isn't covered by `exec`'s overloads, suppress the call-overload check inline (`# type: ignore[call-overload]`) — do not switch back to `execute`.
- Use `selectinload` for explicit relationship loading; `Relationship(sa_relationship_kwargs={"lazy": "raise"})` is the project default — code MUST opt in to loads.
- Raise feature-specific errors (e.g. `MeetingNotFoundError()`) instead of `HTTPException` — the global handler converts them.
- Never construct `HTTPException` in a service. Never call `logger.exception` for expected control-flow errors.
