---
paths:
  - "backend/**/*.py"
---

# Backend Language & Style

## Language & runtime

- Python **3.14**. Use native PEP 604 unions (`X | Y`), PEP 585 generics (`list[int]`, `dict[str, X]`), and PEP 695 `type` aliases.
- **Never** add `from __future__ import annotations`. Remove it if you find it.
- Async-only in the API process. No blocking I/O on the request path.
- Use new generic syntax for decorators/functions when generics are needed: `def f[T](...) -> T: ...` and `def deco[**P, R](func: Callable[P, Awaitable[R]]) -> ...`.

## Style & formatting

- `ruff` is the source of truth. Run `ruff check` and `ruff format` before declaring work complete. Line length 120. Selected rules: `F E W C N I B Q T UP`.
- Every function and method has a return type annotation. Parameters are annotated. `-> None` is explicit, not implied.
- No docstrings, let names and types speak.
- No comments.
- No emojis in code.
- String quoting: double quotes are the norm (ruff `Q` rule). Single quotes only inside an f-string when needed.
- Prefer `pathlib.Path` over `os.path`. Prefer `enum.StrEnum` over string literals for closed sets.
- Prefer early returns over nested `else` branches.
- **Blank lines separate logical steps inside a function** — `ruff format` won't add these, so it's on you. A guard block (`if ... : continue` / `raise` / `return`) is followed by a blank line before the next step, and a `try/except` block is almost always followed by a blank line before the code that uses its result. The goal is to read a function as a sequence of distinct steps rather than one dense wall. Example:

  ```python
  for participant in participants:
      if participant.is_local_user:
          continue

      name = self.resolve_name(participant.stream_id)
      if not name:
          raise ParticipantNameUnresolvedError()

      resolved[participant.stream_id] = name
  ```

  ```python
  try:
      operations = GRAPH_OPERATIONS_ADAPTER.validate_python(payload)
  except ValidationError as exc:
      raise AIValidationError(kind="graph_ops", detail=str(exc)) from exc

  nodes: dict[str, GraphNode] = {}
  ```

  Apply judgment — keep genuinely cohesive one-liners together; don't pad every line. The rule is about grouping distinct steps, not maximising whitespace.
- **Do not isolate a function's final statement with a blank line.** When the closing `return` consumes the value produced by the line directly above it, the two are one step — keep them together. A blank line there orphans the return instead of separating distinct steps; reserve blank lines for genuine step boundaries earlier in the body.

  ```python
  # bad — the return is orphaned from the line that feeds it
  responses = [MeetingResponse.model_validate(meeting) for meeting in meetings]

  return self._with_counts(responses)

  # good
  responses = [MeetingResponse.model_validate(meeting) for meeting in meetings]
  return self._with_counts(responses)
  ```
- Truthy checks for non-numeric / non-string types: prefer `if not x` / `if x` over `if x is None` / `if x is not None` for objects, models, collections, UUIDs, datetimes, and other reference types. Reserve `is None` for primitives where a falsy non-None value (`0`, `0.0`, `""`, `False`) is a meaningful, distinct case from absence.
- Inject collaborators via `__init__`; do not instantiate them inside the class. Constructor parameters are required and typed; no `dep: Foo | None = None` "optional" placeholders that fall back to `Foo()`. The composition root (FastAPI dependency factories in `<feature>/dependencies.py`) owns construction.
- Per-function size cap: keep functions under ~80 lines of code. If you cross that, split into helpers; method names paired with local dataclasses are preferable to long inline state.
- Do not use the keyword-only `*` separator in function/method signatures. Pass arguments positionally or by name without the bare `*` marker.

## Class member order

Within a class, members appear in this order:

1. Dunder methods (`__init__`, `__call__`, ...)
2. Public instance methods
3. Private/protected instance methods (`_x`)
4. Classmethods — public first, then private/protected
5. Staticmethods — public first, then private/protected

## Naming

- Modules: `lower_snake_case.py`. Packages: `lower_snake_case/`.
- No abbreviated names — `query`, not `q`; `result`, not `res`. This applies to function parameters, query-string parameters, and local variables alike. Established idioms (`id`, `db`, loop index `i`) are fine.
- Classes: `PascalCase`. Functions/methods/variables: `lower_snake_case`. Constants/enum members/settings fields: `UPPER_SNAKE_CASE`.
- Dependency aliases end in `Dep` (e.g. `MeetingServiceDep`).
- TypeAdapter constants end in `_ADAPTER`.
- Schema suffixes: `Request`, `Response`, `Event`. Discriminator field is named `kind`.
- Enums: `<Domain>Status`, `<Domain>EventKind`, `<Domain>Event` (lifecycle).

## Doing the right amount

- Do not add error handling, fallbacks, or validation for situations that can't happen. Trust internal callers; validate only at boundaries (HTTP, WS, external services).
- Do not introduce new abstractions speculatively. Three similar lines beat a premature helper.
- Do not add backwards-compat shims, feature flags, or `# removed` placeholders. Delete what is unused.
- Match the scope of the change to the task. A bug fix is not a refactor.
