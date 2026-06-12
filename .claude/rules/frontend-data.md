---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# Frontend Data Layer

Binding rules for the typed backend client, data fetching/caching, client state, and mock data.

## Backend client (`lib/api/`)

- **All** network access goes through `lib/api/client.ts` (`apiGet`, `apiPost`, `apiPatch`, `apiDelete`, `ApiError`). Never call `fetch` directly from a component, page, hook, or feature module.
- Wire-format types live in `lib/api/types.ts` and use **snake_case** field names because they map directly to backend Pydantic. Do not rename them. Suffix REST responses with `Response` (e.g. `UserResponse`, `ScreenResponse`).
- UI-facing types live in `lib/types.ts` and use **camelCase**. Conversion happens in `lib/api/adapters.ts` via `to<UIType>(...)` (e.g. `toUser`, `toScreen`). **Never** consume `*Response` types in components — adapt first.
- **One file per backend feature module**: `auth.ts`, `users.ts`, `screens.ts`, `pois.ts`, `audience.ts`, `plans.ts`, `ai_assistant.ts`, `admin.ts`. Each file exports thin async functions that compose `apiGet` / `apiPost` / `apiPatch` / `apiDelete` with a typed path and return `Promise<T>`.
- When the backend adds a route: add a typed function in the matching `lib/api/<feature>.ts` and the response type in `lib/api/types.ts` in the same change.

## Data fetching & caching (TanStack Query v5)

- Use `@tanstack/react-query` for all reads. Never store fetched data in `useState` + `useEffect`.
- **Query keys are arrays starting with the resource name, then identifiers**: `['screens']`, `['screens', { filters }]`, `['plan', planId]`. Match the conventions already used in the codebase exactly so cache invalidation lines up.
- Mutations use `useMutation`. On success, invalidate the queries that the mutation affects via `queryClient.invalidateQueries({ queryKey: [...] })`. Do not write into the cache imperatively unless there is a strong reason.
- The global `QueryClient` defaults — `staleTime: 0`, `refetchOnMount: 'always'`, `refetchOnWindowFocus: true`, `retry: 1` — are intentional. Do not override per-query unless you have a concrete reason and document it inline with a one-line `// why:` comment.

## Client state (Zustand)

- Cross-route UI state (popover open, plan modal open, layers toggles, AI card dismissed) lives in **one** Zustand store: `lib/store.ts` (`useUIStore`).
- Server data does not belong in Zustand — it belongs in React Query.
- Component-local state belongs in `useState` / `useReducer` — do not promote it to the store unless another route needs it.
- Selectors: `useUIStore((s) => s.popoverScreenId)` for fine-grained subscriptions when re-render cost matters; destructure when you need several fields together.

## Mock data (`lib/mock/`)

- Surfaces the backend does not yet serve (screens, POIs, audience segments, plans, AI recommendations, admin screen list) read from `src/lib/mock/`.
- Every consumer of mock data **must mark the call site** with a `TODO(api):` comment naming the backend module that will replace it. Example: `// TODO(api): screens not implemented (backend/app/screens)`.
- When the backend ships the real data: **delete** the mock module, **delete** the `TODO(api):` comment, and route through `lib/api/<feature>.ts`. Do not leave the mock as a "fallback".
- Mock data is typed against the UI types in `lib/types.ts`, not against wire-format types.

## Errors

- The api client throws `ApiError(status, message)`. React Query surfaces it via `query.isError` / `mutation.error`. Render an empty/error state in the page.
- Never wrap a `useQuery` in a `try/catch`; React Query owns the error path.
- Toasts (`sonner`) are reserved for cross-route lifecycle notifications (login success, plan saved, export ready). Do not `toast()` from inside a component for routine UX feedback — render in-place state instead.
