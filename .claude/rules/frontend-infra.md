---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# Frontend Infra & Configuration

Binding rules for environment access, configuration, and operational concerns.

## Environment access

- **All env access goes through `src/lib/config.ts`.** Never read `process.env.NEXT_PUBLIC_*` from a component, hook, route, or `lib/api/` file.
- Browser-visible env vars **must** be prefixed `NEXT_PUBLIC_`. Anything else is server-only and must not leak through `config`.
- `config.ts` exposes `config = { apiBaseUrl, ... }`. A `required(name, value)` helper throws on startup when a required var is missing — keep this contract; do not silently default secrets or URLs.
- Do not hardcode hostnames, API URLs, or model identifiers anywhere outside `config.ts`. Add a config field instead.

## Stylesheet & assets

- The **single** global stylesheet is `src/app/globals.css`. It carries the Tryniq "Lab paper" design system (CSS custom properties + component classes) plus shadcn theme tokens.
- Do not create additional `.css` files anywhere under `src/`. No CSS Modules. No `*.module.css`.
- Fonts: `Inter` (UI) and `JetBrains Mono` (code / timestamps) are loaded in `src/app/layout.tsx` and bound to the `font-family` declarations already present in `globals.css`.
- Static assets live in `frontend/public/`. Reference them with absolute paths (`/logo.svg`), never relative.

## Logging & observability

- Use `console.error` for unexpected client errors (network failures handled by React Query are not "unexpected").
- Do not add a custom logger abstraction. The console is enough for an internal Phase 1 tool.
- Never log secrets, tokens, or PII (email is acceptable for auth flows only).

## Build & lint gates

- `pnpm check` — Biome lint + format check. **Must pass.**
- `pnpm typecheck` — `tsc --noEmit`. **Must pass.**
- `pnpm build` — `next build`. **Must pass.**
- Run all three before declaring work complete.
