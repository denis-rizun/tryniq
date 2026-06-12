---
paths:
  - "backend/**/*.py"
---

# Backend Infrastructure

Rules for logging and exceptions.

## Logging

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

## Exceptions

- Base hierarchy in `app/core/exceptions.py`: `AppError` → `NotFoundError`, `BadRequestError`, `ForbiddenError`, `UnauthorizedError`, `ConflictError`. The global handler in `register_exception_handler` maps these to JSON.
- Feature-specific exceptions live in `<feature>/exceptions.py`, subclass the appropriate `AppError` child, take no arguments, and pass a fixed `detail` string:

  ```python
  class MeetingNotFoundError(NotFoundError):
      def __init__(self) -> None:
          super().__init__("Meeting not found")
  ```

- Do not catch `Exception` broadly. Catch the narrowest set you actually expect (e.g. `(RedisError, SQLAlchemyError)`, `(ValidationError, json.JSONDecodeError)`). The one acceptable broad catch is around best-effort cleanup, and it must log at `debug`/`warning` and continue.
