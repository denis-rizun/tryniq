---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# Frontend Tests

Binding rules for frontend testing. Minimal by design — the backend has its own test rules, and Phase 1 is an internal tool.

## Layers

- **Unit** — pure functions in `lib/` (adapters, format helpers). Colocate as `<thing>.test.ts` next to the source file. Use **Vitest**.
- **Component** — React Testing Library, colocated as `<component>.test.tsx`. Render with the providers required by the component (mostly `QueryClientProvider` with a fresh client per test). Use **Vitest** + `@testing-library/react` + `jsdom`.
- **End-to-end** — deferred unless a flow is explicitly listed in `docs/PRD.md` as needing an automated check. When introduced, lives under `frontend/e2e/` and uses **Playwright**.

## Rules

- No snapshot tests. They rot and nobody reads them.
- No `enzyme`, no shallow rendering. Render real DOM.
- No mocks of internal modules. Mock only at the wire boundary — wrap `apiGet`/`apiPost` with MSW or a hand-rolled fetch stub for component tests.
- One assertion focus per test. Test behavior, not implementation details (class names, internal state).
- Filenames: `<thing>.test.ts(x)`. Imports use the `@/` alias.

## Commands

```bash
pnpm test                       # vitest run
pnpm test --watch               # watch mode
pnpm test src/lib/format.test.ts   # single file
```
