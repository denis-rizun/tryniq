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
            layout.tsx           # root shell (app-shell chrome) + providers
            globals.css          # the only stylesheet in the app
            page.tsx             # / landing
            meetings/
                page.tsx         # meetings directory
                meetings-client.tsx
                [id]/
                    layout.tsx   # per-meeting shell (tabs)
                    page.tsx
                    overview/page.tsx
                    graph/page.tsx
                    speakers/page.tsx
                    settings/page.tsx
            people/page.tsx
            chat/page.tsx
            upload/page.tsx
            extension/page.tsx
        components/
            ui/                  # primitive presentational pieces (shadcn + Icon registry)
            shell/               # app chrome (sidebar, topbar, breadcrumb, overlays, toaster)
            <feature>/           # feature components (meeting, meetings-list, people, chat, ...)
        lib/
            api/                 # typed backend client (see frontend-data.md)
                client.ts
                types.ts
                adapters.ts
                query-client.tsx
                events.ts
                meetings.ts
                people.ts
                chat.ts
            hooks/               # reusable client hooks (use-*.ts)
            mock/                # placeholder data for surfaces the backend does not serve yet
            store.ts             # single Zustand UI store
            config.ts            # centralised env access
            types.ts             # UI-facing domain types
            format.ts            # pure format helpers
            utils.ts             # tiny shared helpers (cn, ...)
```

## Feature modules

These are the `<feature>` slices that exist. Do not invent new ones without adding a row here:

- `meeting/` — meeting header, tabs, graph canvas, settings.
- `meetings-list/` — meetings directory table and toolbar.
- `people/` — person row, person drawer.
- `chat/` — AI drawer, chat message, session row, scope toggle, composer.
- `command-palette/` — global command palette.
- `export/` — export modal and preview builder.
- `upload/` — recording dropzone and upload progress.
- `extension/` — extension popup surface.
- `shell/` — app chrome (sidebar, topbar, breadcrumb, overlays, toaster).
- `ui/` — primitives (icon, avatar, pill, checkbox, status-dot, ...).

## Rules

- **One responsibility per file. Soft cap: 200 lines, hard cap: 250.** If you cross the soft cap, split a sub-component or hook out; never let a file exceed 250 lines.
- **File names are `kebab-case.ts` / `kebab-case.tsx`.** The default-exported or main type uses `PascalCase` inside.
- **A page that does both data fetching and heavy interactivity splits** into `page.tsx` (entry) and `<name>-client.tsx` (client component).
- **Do not invent new top-level folders.** No `src/services/`, no `src/contexts/`, no `src/utils/` — use the buckets above.
- **No barrel files** (`index.ts` re-exports). Import from the source file directly.

## Server vs client components

- Default to a **Server Component**. Add `'use client'` only when the file needs browser APIs, hooks, event handlers, or state.
- Provider components (`QueryProvider`, `Toaster`) are mounted once in `src/app/layout.tsx`. Do not re-mount providers per route.
- The app-shell chrome (sidebar + topbar) lives in the root `src/app/layout.tsx`; per-meeting tabs live in `src/app/meetings/[id]/layout.tsx`. There is no auth/login route yet — auth/RBAC is a planned feature. When it lands, add a public `login/` route outside the shell and gate the app behind an authenticated route group (`(app)/`), keeping the providers mounted in the root `layout.tsx`.
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
- Event handlers are `onX` (e.g. `onClickMeeting`, `onChangeScope`) — present-tense verbs, no `did`/`will` prefix.

## When you're not sure

1. Find the closest existing example in `src/` and mirror it exactly — file layout, naming, hook shape, query keys, className taxonomy.
2. Cross-check wire-format types against `backend/app/<feature>/schemas.py`. If the two disagree, the backend wins and you update `lib/api/types.ts` (and adapters).
3. If still unclear, ask before inventing. Do not "improve" patterns that are already consistent across the codebase.
