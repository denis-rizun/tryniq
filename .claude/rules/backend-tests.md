---
paths:
  - "backend/**/*.py"
---

# Backend Tests

Binding rules for backend test layout, fixtures, and execution. Mirror the shape of existing tests in `backend/tests/` — do not introduce new flavors.

## Three layers

Every test belongs to exactly one layer, picked by what it touches:

- **`tests/unit/`** — pure-function tests. No database, no Redis, no network, no filesystem, no mocks. Construct the real object under test, call it, assert. If a test needs an `AsyncSession`, an HTTP client, or any `Mock`/`patch`, it does **not** belong here.
- **`tests/integration/`** — tests that exercise real infrastructure (Postgres, Redis, S3, etc.) via service classes. No FastAPI request cycle. Use the shared `db_session` fixture from `tests/integration/conftest.py`.
- **`tests/e2e/`** — tests that drive the FastAPI app through HTTP using `httpx.AsyncClient` + `ASGITransport`. Use the `client` fixture (no DB) or `client_with_db` fixture (overrides `get_session` with the integration `db_session`).

Do not blur layers. A unit test that "just needs a quick DB call" is an integration test — move it.

## Markers

- Every test module starts with `pytestmark = pytest.mark.<layer>` matching its directory:

  ```python
  import pytest

  pytestmark = pytest.mark.unit
  ```

- Markers are declared in `pyproject.toml` under `[tool.pytest.ini_options].markers`. `--strict-markers` is enforced — undeclared markers fail collection.
- Select a layer either by path (`pytest tests/unit`) or by marker (`pytest -m unit`). Both must work.

## Layout & naming

```
backend/tests/
    __init__.py
    unit/
        __init__.py
        test_<subject>.py
    integration/
        __init__.py
        conftest.py             # engine, db_connection, db_session
        models.py               # test-only SQLModel rows (underscore-prefixed)
        test_<subject>.py
    e2e/
        __init__.py
        conftest.py             # client, client_with_db
        test_<subject>.py
```

- Test files: `test_<subject>.py`. Test classes: `Test<Subject>`. Test methods: `test_<behavior>` in present-tense indicative ("returns_ok", "rejects_unknown_level").
- One `Test<Subject>` class per cohesive behavior group. Group related cases under a class; do not write loose top-level test functions.
- Test-only SQLModels (e.g. `_SampleRow`) live in `tests/integration/models.py`, are underscore-prefixed, and exist only to exercise mixins/event listeners. They MUST NOT leak into production code or alembic autogenerate (alembic does not import `tests/`, keep it that way).

## Fixtures

- Shared cross-layer fixtures: none. The repo deliberately has no root `tests/conftest.py`.
- Integration fixtures live in `tests/integration/conftest.py`:
  - `test_engine` — session-scoped, points at `config.database.TEST_URL`, runs `SQLModel.metadata.create_all` at start and `drop_all` at teardown.
  - `db_connection` — function-scoped, opens a real connection, begins an outer transaction, rolls back on teardown.
  - `db_session` — function-scoped `AsyncSession` bound to `db_connection` with `join_transaction_mode="create_savepoint"`. Use this for every integration test so each test rolls back cleanly without dropping tables.
- E2E fixtures live in `tests/e2e/conftest.py`:
  - `client` — `AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver/api/v1")`. No lifespan.
  - `client_with_db` — same client plus `app.dependency_overrides[get_session]` wired to the integration `db_session`. The fixture clears the override in its own `finally`; do not add an autouse cleanup elsewhere.
- Per-class fixtures (`@pytest.fixture` inside a `Test<Subject>` class) are fine when they eliminate repetition within that class.

## Async

- `asyncio_mode = "auto"` in `pyproject.toml`. Do not decorate test methods with `@pytest.mark.asyncio`.
- All test methods that await anything are `async def`. Sync `def` is reserved for tests that touch no coroutine.

## Writing tests

- Arrange / Act / Assert with a single blank line between blocks. Each test asserts one behavior; multiple `assert`s are fine if they describe one observation.
- No docstrings, no comments — same rule as production code. The class name + method name describe the case.
- Use `pytest.mark.parametrize` for table-driven cases rather than copy-pasting test methods.
- Do not use `unittest.mock` in unit tests. In integration/e2e, prefer dependency overrides (`app.dependency_overrides[...]`) over `monkeypatch`/`Mock`.
- Never call `HTTPException`/`AppError` directly from tests to assert handler shape — exercise the registered handler via the real app and assert the JSON.

## Coverage

- Coverage gate is **≥90%** total. `make ci` runs the full suite with the gate enabled.
- The gate must pass when only unit + e2e are collected (i.e. without a Postgres available). If integration is the only layer covering some lines, lift that coverage with a unit test that calls the function directly with a real object (no mocks). Listener functions in `app/core/database.py` are the canonical example.
- Do not lower the gate to make a feature land. Either add unit coverage or genuinely exercise the path.
- `app/main.py` and `app/logger.py` are deliberately omitted from coverage (see `[tool.coverage.run].omit`). Do not add new files to that list without justification.

## Running tests

```bash
uv run pytest                          # full suite, with coverage gate
uv run pytest tests/unit               # one layer by path
uv run pytest -m unit                  # one layer by marker
uv run pytest -m "unit or e2e"         # multiple layers
uv run pytest --no-cov                 # iterate without the gate
uv run pytest tests/path/to/test_x.py::TestSubject::test_behavior
```

## Test database

Tests share the dev Postgres instance, but use a **separate database** named by `POSTGRES_TEST_DATABASE` (default `tryniq_test`). The dev DB is never touched by tests — the `test_database_url` fixture refuses to run if `TEST_DATABASE` equals `DATABASE`.

Schema for the test DB is built directly from `SQLModel.metadata`, not from alembic. The `test_engine` session-scoped fixture is the single source of truth:

1. Ensures the test database exists (connects to the `postgres` admin DB and issues `CREATE DATABASE` if missing — idempotent).
2. Calls `SQLModel.metadata.drop_all` then `create_all` to build a clean schema covering every model imported at collection time (including test-only models in `tests/integration/models.py`).
3. Yields the engine for the test session.
4. Drops everything at teardown.

This deliberately bypasses alembic. Tests verify behavior against the **current** models; migration history is validated separately by running `alembic upgrade head` against the dev DB. Do not add an alembic-against-test-DB step — it adds nothing the model graph doesn't already give us, and complicates the fixture.

Alembic only manages the dev/prod schema:

```bash
make migrate         # upgrade dev DB to head
```

Inside docker compose the API container reaches Postgres at `POSTGRES_HOST=postgres`; from the host machine (where pytest runs) it is `POSTGRES_TEST_HOST=localhost`. Both point at the same instance on `POSTGRES_PORT`.
