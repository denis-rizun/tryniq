# Tryniq Frontend Constitution

This document is the **mandatory** style and structure guide for `frontend/`. Every agent or contributor MUST read this file *before* writing or modifying any TypeScript/TSX in this repo. It encodes conventions already present in the codebase — your job is to keep the codebase coherent with what is already here, not to introduce a new flavor.

If a rule below conflicts with `CLAUDE.md` (project root) or `docs/PRD.md`, those documents win on architectural questions; this document wins on code shape. Feature-owned wire types in `src/lib/api/<feature>.ts` are co-owned with `backend/app/*/schemas.py` — the backend Pydantic schemas are the source of truth for field names and discriminators.

---

## 0. Read first

Before writing code:

1. Read this file end-to-end.
2. Skim the surface nearest to your task (`src/app/<route>/`, `src/components/<feature>/`, `src/lib/api/`) — match its shape exactly.
3. Read `biome.json` for the formatter/linter ruleset (line width 100, single quotes, JSX double quotes, trailing commas, semicolons, organize imports on save).
4. Read `CLAUDE.md` at the repo root for the architectural commitments. The frontend is a *projection* of the backend graph and live transcript — treat anything that isn't yet served by the backend as mock data marked with a `TODO(api):` comment.

---

## 1. Language & runtime

- **TypeScript** in `strict` mode (`tsconfig.json`). No `any` (Biome warns); no `// @ts-ignore`. If you need an escape hatch, use `unknown` and narrow.
- **Next.js 16** App Router, **React 19**. Server Components by default; client components opt in with `'use client'` at the top of the file.
- Node 20, **pnpm** (lockfile is `pnpm-lock.yaml`). Don't introduce `npm` or `yarn` artifacts.
- Path alias `@/*` → `src/*`. Always import via `@/...`, never relative `../../`.
- Target ES2017 in tsconfig but write modern TS (Biome+Next handle downlevel). Use `??`, `?.`, `satisfies`, `as const`, and template literal types freely.

---

## 2. Module layout

```
src/
    app/                    # Next.js App Router routes (file-based)
        layout.tsx          # root shell (providers + sidebar/topbar)
        page.tsx            # / route
        globals.css         # global stylesheet (only stylesheet in the app)
        <route>/page.tsx    # route entrypoint
        <route>/<x>-client.tsx  # client portion when the page splits server/client
    components/
        ui/                 # primitive presentational pieces (icon, avatar, pill, ...)
        shell/              # app chrome (sidebar, topbar, toaster, overlays, breadcrumb)
        <feature>/          # feature components (meeting/, people/, chat/, upload/, ...)
    lib/
        api/                # typed backend client (see §5)
            client.ts       # fetch wrapper + ApiError
            <feature>.ts   # route functions + wire types for one backend feature
            <feature>-adapters.ts # backend response → UI types for that feature
            events.ts       # SSE + global WS subscribers
            query-client.tsx
            global-events-provider.tsx
        hooks/              # reusable client hooks (use-*.ts)
        mock/               # placeholder data for surfaces the backend does not serve yet
        config.ts           # centralised env access
        store.ts            # Zustand UI store
        types.ts            # UI-facing domain types (Meeting, Utterance, ...)
        format.ts           # pure format helpers
        utils.ts            # tiny shared helpers (cn, ...)
```

Rules:

- One responsibility per file. **Soft cap: 200 lines.** If you cross it, split a sub-component or hook out.
- File names are `kebab-case.ts` / `kebab-case.tsx`. The default-exported or main type uses `PascalCase` inside.
- A page that does both data fetching and heavy interactivity splits into `page.tsx` (entry) and `<name>-client.tsx` (client component) — see `src/app/meetings/[id]/overview/`.
- Don't invent new top-level folders. Don't add `src/services/`, `src/contexts/`, `src/utils/` — use the existing buckets.

---

## 3. Server vs client components

- Default to a **Server Component**. Add `'use client'` only when the file needs browser APIs, hooks, event handlers, or state.
- Client islands should be as small as possible. A page that needs React Query / Zustand becomes a client page; a page that just renders static markup stays server.
- Provider components (`QueryProvider`, `GlobalEventsProvider`) are mounted once in `app/layout.tsx`. Don't re-mount providers per route.
- Never import server-only modules from client files (no `fs`, no secrets). Browser-visible env vars start with `NEXT_PUBLIC_` and go through `lib/config.ts`.

---

## 4. Imports

- Absolute imports rooted at `@/` — never relative (`../../lib/...`).
- Biome's `organizeImports` action is **on**. Don't hand-sort; let `pnpm format` / `pnpm check` do it.
- Use `import type { ... }` for type-only imports (Biome `useImportType`).
- One import group per source area; rely on Biome's grouping rather than manual section comments.
- Avoid barrel files. Don't introduce `index.ts` re-export shims.

---

## 5. Backend client (`lib/api/`)

- **All** network access goes through `lib/api/client.ts` (`apiGet`, `apiPatch`, `ApiError`). Never call `fetch` directly from a component or page.
- Wire-format types (`MeetingResponse`, `UtteranceResponse`, `LiveEvent`, …) live beside their feature routes in `lib/api/<feature>.ts` and use **snake_case** field names because they map directly to backend Pydantic. Do not rename them.
- UI-facing types live in `lib/types.ts` and use **camelCase**. Conversion happens in `lib/api/<feature>-adapters.ts` via `toMeeting(...)`, `toMeetingListItem(...)`, `toUtterance(...)`. Never consume `*Response` types in components — adapt first.
- One file per backend feature module: `meetings.ts`, `participants.ts`, etc. Each file exports thin async functions that compose `apiGet` / `apiPatch` with a typed path and return `Promise<T>`.
- Subscribe to live events via `subscribeMeetingEvents` (SSE) and `subscribeGlobalEvents` (WS) in `lib/api/events.ts`. Don't open `EventSource` / `WebSocket` directly elsewhere.
- New backend routes added to the api → add a typed function and response type in the matching `lib/api/<feature>.ts`, plus a feature adapter when UI conversion is needed.

---

## 6. Data fetching & caching (React Query)

- Use `@tanstack/react-query` for all reads. Never store fetched data in `useState` + `useEffect`.
- Query keys are **arrays starting with the resource name**, then identifiers: `['meetings']`, `['transcript', id]`. Match the conventions already used in the codebase exactly so cache invalidation lines up.
- Mutations use `useMutation`. On success, invalidate the queries that the mutation affects via `queryClient.invalidateQueries({ queryKey: [...] })`. Don't write into the cache imperatively unless there's a strong reason.
- The global `QueryClient` defaults (`staleTime: 0`, `refetchOnMount: 'always'`, `refetchOnWindowFocus: true`, `retry: 1`) are intentional. Don't override per-query unless you have a concrete reason and document it inline.
- Live updates from `GlobalEventsProvider` push invalidations into the cache. Don't bypass it by polling.

---

## 7. Live data (SSE / WebSocket)

- Per-meeting live transcript: `subscribeMeetingEvents(meetingId, ...)` (SSE on `/meetings/{id}/events`). Consume it via `useLiveTranscript` — don't subscribe directly from a component.
- Global meeting lifecycle: `subscribeGlobalEvents(...)` (WS on `/events/ws`). Already mounted once in `GlobalEventsProvider`. Don't open a second global socket.
- Reconnect/backoff is handled inside `events.ts`. Don't wrap subscribers in additional reconnect logic at the call site.
- Treat malformed payloads as droppable — never crash the UI on a bad frame (already done with `try/catch` around `JSON.parse`).
- Live state lives in component-scoped React state (`useLiveTranscript`); it is not promoted into React Query or Zustand.

---

## 8. Client state (Zustand)

- Cross-route UI state (drawer open, command palette open, export modal, chat sessions) lives in **one** Zustand store: `lib/store.ts` (`useUIStore`).
- Server data does not belong in Zustand — it belongs in React Query.
- Component-local state belongs in `useState` / `useReducer` — don't promote it to the store unless another route needs it.
- Selectors: `useUIStore((s) => s.drawerOpen)` for fine-grained subscriptions when re-render cost matters; destructure when you need several fields together (already used in `MeetingHeader`).

---

## 9. Components

- Components are **arrow function expressions** assigned to a `const`, then exported (named export preferred; default export only at route entrypoints because Next requires it):

  ```tsx
  export const Foo = ({ id }: { id: string }) => <div>{id}</div>;
  ```

- Props are typed inline for one or two fields, or via a sibling `interface FooProps { ... }` for three or more (see `MeetingHeader`, `useLiveTranscript`).
- No `React.FC`. No `function` declarations for components. No `defaultProps`.
- Hooks: file name `use-<thing>.ts` in `lib/hooks/`. The exported hook is `useThing`. One hook per file.
- Event handlers are `onX` (e.g. `onClickUtterance`, `onCiteClick`) — present-tense verbs, no `did`/`will` prefix.
- Refs that mirror props for use inside effects use the `ref.current = prop` pattern shown in `useLiveTranscript`. Don't invent a new pattern.

---

## 10. Styling

- Single global stylesheet: `src/app/globals.css`. Component styles use **className strings** that map to selectors defined there.
- Don't introduce CSS Modules, Tailwind, styled-components, Emotion, or vanilla-extract. We don't have them and we are not adding them for the MVP.
- Use the existing class taxonomy (`meeting-status`, `meeting-status-live`, `mono`, `app-shell`, …) — read `globals.css` before naming a new class. Match the kebab-case-with-BEM-ish convention already in use.
- Inline `style={{ ... }}` is acceptable for one-off layout primitives (see `RootLayout`'s `<main>`). Don't escalate it into a styling system.
- Use `clsx` via the `cn` helper in `lib/utils.ts` for conditional classNames.
- Icons come from `lucide-react`, wrapped through `@/components/ui/icon`. Don't import `lucide-react` directly from feature components when an `Icon` wrapper exists.

---

## 11. Configuration & env

- All env access goes through `src/lib/config.ts`. Never read `process.env.NEXT_PUBLIC_*` from a component or hook.
- Browser-visible env vars **must** be prefixed `NEXT_PUBLIC_`. Anything else is server-only and must not leak through `config`.
- `config.ts`'s `required(name, value)` throws on startup when a required var is missing — keep this contract; don't silently default secrets/URLs.
- Do not hardcode hostnames, API URLs, or model identifiers. Add a config field instead.

---

## 12. Mock data

- The remaining temporary people mocks are direct imports from `src/lib/mock/people.ts` in the extension and topbar only.
- Every consumer of mock data must mark the call site with a `TODO(api):` comment naming the backend phase that will replace it (e.g. `// TODO(api): graph extraction not implemented (Phase 3)`).
- When the backend ships the real data: delete the mock module, delete the `TODO(api):` comment, and route through `lib/api/<feature>.ts`. Don't leave the mock as a "fallback".

---

## 13. Errors

- The api client throws `ApiError(status, message)`. React Query surfaces it via `query.isError` / `mutation.error`. Render an empty/error state in the page (see `OverviewPage` — `Could not load meeting transcript.`).
- Never wrap a `useQuery` in a `try/catch`; React Query owns the error path.
- Toasts (`sonner`) are reserved for cross-route lifecycle notifications driven by `GlobalEventsProvider`. Don't `toast()` from inside a component for routine UX feedback — render in-place state instead.
- Browser-only failures (malformed SSE payloads, dead WS) are dropped silently with a comment, not surfaced to the user. Keep that pattern.

---

## 14. Style & formatting

- **Biome** is the source of truth. Run `pnpm check` (and `pnpm format` to autofix) before declaring work complete.
- Single quotes for JS/TS strings, double quotes for JSX attributes, trailing commas everywhere, semicolons always, line width 100.
- No comments. No JSDoc. Names and types must carry the meaning. The only acceptable comments are:
  - `// TODO(api): ...` markers tying mock data to a backend phase.
  - One-line markers explaining a non-obvious *why* (a workaround, a wire-format quirk).
- No emojis in code or strings.
- Prefer early `return` over nested ternaries / `else` branches.
- Prefer `const` arrow functions over `function` declarations (Biome `useConst`).
- Prefer `for (const x of xs)` and array methods (`map` / `filter` / `find`) over index loops.
- Use `as const` for literal tuples (see `MEETING_EVENT_KINDS`); use `satisfies` to validate object literals against a type without widening.

---

## 15. Naming

- Files: `kebab-case.ts` / `kebab-case.tsx`. Hooks: `use-<thing>.ts`. Route entrypoints: `page.tsx`, `layout.tsx` (Next conventions).
- Types/interfaces/components: `PascalCase`. Functions/variables/props: `camelCase`. Constants: `UPPER_SNAKE_CASE` only for true module-level constants (`MEETING_EVENT_KINDS`, `PARTIAL_FLAG`).
- Wire-format type suffixes: `Response` (REST responses), `Event` (SSE/WS payloads). Discriminator field on events is `kind` (matches backend).
- UI-facing domain types live in `lib/types.ts` with no suffix (`Meeting`, `Utterance`, `PeopleMap`).
- Adapter functions: `to<UIType>` (e.g. `toMeeting`, `toUtterance`).
- Hooks are camelCase verbs prefixed with `use` (`useLiveTranscript`, `useUIStore`).

---

## 16. Doing the right amount

- Do not add error handling, fallbacks, or validation for situations that can't happen. Trust the backend's typed contract; validate only at the wire boundary (the JSON parse inside `events.ts`, `apiGet`'s status check).
- Do not introduce new abstractions speculatively. Three similar lines beat a premature helper.
- Do not add backwards-compat shims, feature flags, or `// removed` placeholders. Delete unused code.
- A bug fix is not a refactor. Match the scope of the change to the task.

---

## 17. When you're not sure

1. Find the closest existing example in `src/` and mirror it exactly — file layout, naming, hook shape, query keys, className taxonomy. Canonical references: `src/app/meetings/[id]/overview/`, `src/lib/api/`, `src/lib/hooks/use-live-transcript.ts`, `src/components/meeting/meeting-header.tsx`.
2. Cross-check wire-format types against `backend/app/<feature>/schemas.py`. If the two disagree, the backend wins and you update that feature's API file and adapter.
3. If still unclear, ask before inventing. Do not "improve" patterns that are already consistent across the codebase.
