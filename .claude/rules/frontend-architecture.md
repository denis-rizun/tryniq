---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# Frontend Architecture

Binding rules for module layout, server/client split, imports, and component shape. Mirror the shape of the nearest existing feature — do not introduce new flavors.

## Foundational principles

- **Organized by feature** — code that changes together lives together.
- **The frontend is a projection of the backend graph.** Anything not yet served by the backend is mock data marked with a `TODO(api):` comment.
- **App Router first.** Default to Server Components. Client islands opt in with `'use client'` and stay as small as possible.

## Module layout

```
frontend/
    src/
        app/                     # Next.js App Router (file-based routing)
            layout.tsx           # root shell — providers only
            globals.css          # the only stylesheet in the app
            (app)/               # authenticated route group
                layout.tsx       # AppShell (nav rail + top bar)
                page.tsx         # / planning
                ai/page.tsx
                plans/page.tsx
                admin/page.tsx
                account/page.tsx
                inventory/page.tsx
            login/page.tsx       # public route — no shell
        components/
            ui/                  # primitive presentational pieces (shadcn + Signal)
            shell/               # app chrome (nav-rail, top-bar, app-shell)
            <feature>/           # feature components (screens, plans, map, ai, admin, ...)
        lib/
            api/                 # typed backend client (see frontend-data.md)
                client.ts
                types.ts
                adapters.ts
                query-client.tsx
                auth.ts
                users.ts
            hooks/               # reusable client hooks (use-*.ts)
            mock/                # placeholder data for surfaces the backend does not serve yet
            store.ts             # single Zustand UI store
            config.ts            # centralised env access
            types.ts             # UI-facing domain types
            format.ts            # pure format helpers
            geo.ts               # H3 / lat-long helpers
            utils.ts             # tiny shared helpers (cn, ...)
```

## Signal feature modules

These are the only `<feature>` slices for Phase 1. Do not invent new ones without adding a row here:

- `screens/` — ranked list, screen row, screen-detail popover, filter column.
- `pois/` — POI markers, POI category picker.
- `audience-segments/` — segment picker (Captify + Mastercard), segment AND/OR logic.
- `plans/` — basket, plan list, plan save dialog.
- `map/` — `signal-map.tsx`, layers (heatmap, radius, poi-markers, screen-markers).
- `ai/` — recommendation card and AI brief input.
- `admin/` — screen uploads, POI uploads, weights config.
- `account/` — account settings.
- `auth/` — login form.

## Rules

- **One responsibility per file. Soft cap: 200 lines, hard cap: 250.** If you cross the soft cap, split a sub-component or hook out; never let a file exceed 250 lines.
- **File names are `kebab-case.ts` / `kebab-case.tsx`.** The default-exported or main type uses `PascalCase` inside.
- **A page that does both data fetching and heavy interactivity splits** into `page.tsx` (entry) and `<name>-client.tsx` (client component).
- **Do not invent new top-level folders.** No `src/services/`, no `src/contexts/`, no `src/utils/` — use the buckets above.
- **No barrel files** (`index.ts` re-exports). Import from the source file directly.

## Server vs client components

- Default to a **Server Component**. Add `'use client'` only when the file needs browser APIs, hooks, event handlers, or state.
- Provider components (`QueryProvider`, `Toaster`) are mounted once in `src/app/layout.tsx`. Do not re-mount providers per route.
- The `AppShell` lives in `src/app/(app)/layout.tsx`. `/login` lives outside the group and has no shell.
- Never import server-only modules from client files (no `fs`, no secrets). Browser-visible env vars start with `NEXT_PUBLIC_` and go through `lib/config.ts`.

## Imports

- Absolute imports rooted at `@/` — never relative (`../../lib/...`).
- Biome's `organizeImports` action is on. Do not hand-sort.
- Use `import type { ... }` for type-only imports.
- Avoid barrel files. Import from the source file.

## Components

- Components are **arrow function expressions** assigned to a `const`, then exported (named export preferred; default export only at route entrypoints because Next requires it):

  ```tsx
  export const Foo = ({ id }: { id: string }) => <div>{id}</div>;
  ```

- Props are typed inline for one or two fields, or via a sibling `interface FooProps { ... }` for three or more.
- No `React.FC`. No `function` declarations for components. No `defaultProps`.
- Hooks: file name `use-<thing>.ts` in `lib/hooks/`. The exported hook is `useThing`. One hook per file.
- Event handlers are `onX` (e.g. `onClickScreen`, `onChangeRadius`) — present-tense verbs, no `did`/`will` prefix.

## When you're not sure

1. Find the closest existing example in `src/` and mirror it exactly — file layout, naming, hook shape, query keys, className taxonomy.
2. Cross-check wire-format types against `backend/app/<feature>/schemas.py`. If the two disagree, the backend wins and you update `lib/api/types.ts` (and adapters).
3. If still unclear, ask before inventing. Do not "improve" patterns that are already consistent across the codebase.
