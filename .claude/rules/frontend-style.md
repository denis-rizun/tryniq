---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
  - "frontend/**/*.css"
---

# Frontend Language & Style

## Language & runtime

- **TypeScript** in `strict` mode. No `any` (Biome warns); no `// @ts-ignore`. If you need an escape hatch, use `unknown` and narrow.
- **Next.js 16** App Router, **React 19**. Server Components by default; client components opt in with `'use client'`.
- Node 20, **pnpm** (lockfile is `pnpm-lock.yaml`). Do not introduce `npm` or `yarn` artifacts.
- Path alias `@/*` → `src/*`. Always import via `@/...`, never relative `../../`.
- Write modern TS. Use `??`, `?.`, `satisfies`, `as const`, and template literal types freely.

## Style & formatting

- **Biome** is the source of truth. Run `pnpm check` (lint + format check) and `pnpm format` (autofix) before declaring work complete.
- Single quotes for JS/TS strings, double quotes for JSX attributes, trailing commas everywhere, semicolons always, line width 100.
- **No comments. No JSDoc. Ever.** Do not add explanatory comments, including `// why:` markers — names and types must carry the meaning. If something needs explaining, put it in the commit message or PR description, not the code. The single exception is the mandatory `// TODO(api): ...` marker that ties mock data to its backend module.
- **No emojis** in code, strings, or commit messages.
- Prefer early `return` over nested ternaries / `else` branches.
- Prefer `const` arrow functions over `function` declarations.
- Prefer `for (const x of xs)` and array methods (`map` / `filter` / `find`) over index loops.
- Use `as const` for literal tuples; use `satisfies` to validate object literals against a type without widening.

## Components

- Arrow function expressions assigned to a `const`, then exported (named export preferred).

  ```tsx
  export const UtteranceRow = ({ utterance }: { utterance: Utterance }) => (
    <li className="utterance">{utterance.text}</li>
  );
  ```

- No `React.FC`. No `function MyComponent(...)`. No `defaultProps`.
- Hooks: file name `use-<thing>.ts` in `lib/hooks/`. The exported hook is `useThing`. One hook per file.

## Styling

- **The Tryniq "Lab paper" stylesheet is sacred.** It lives in `src/app/globals.css`. Do not rename classes, do not split it into pieces, do not convert rules to Tailwind utilities. If a surface needs a style, find the existing class for it.
- Components apply styling primarily via `className` strings that map to selectors already defined in `globals.css`: `.app-shell`, `.sidebar`, `.topbar`, `.drawer`, `.utterance`, `.meetings-table`, `.graph-canvas`, `.cite-chip`, `.btn`, `.filter-chip`, ... — read the stylesheet before naming a new class.
- **shadcn primitives are allowed for behavior** (Dialog, Popover, Tooltip, Select, Sheet, DropdownMenu, Toast/Sonner, Command). Their generated classes stay as-is. Wrap them in a feature component (`<ExportModal>`) that applies the Lab-paper className taxonomy on the visible surface.
- **Tailwind utilities are a last resort**, used only when a shadcn primitive forces them or for a truly one-off layout primitive (a `flex` row, a `gap`). They are not the default styling mechanism.
- Inline `style={{ ... }}` is acceptable for one-off layout primitives. Do not escalate it into a styling system.
- Use `clsx` via the `cn` helper in `lib/utils.ts` for conditional classNames.
- Icons come from `lucide-react`, wrapped through `@/components/ui/icon` (the `Icon` component with a `name` prop). Do not import `lucide-react` directly from feature components.

## Naming

- Files: `kebab-case.ts` / `kebab-case.tsx`. Hooks: `use-<thing>.ts`. Route entrypoints: `page.tsx`, `layout.tsx` (Next conventions).
- Types/interfaces/components: `PascalCase`. Functions/variables/props: `camelCase`. Constants: `UPPER_SNAKE_CASE` only for true module-level constants (`NAV_ITEMS`, `DEFAULT_FILTERS`).
- Wire-format type suffix: `Response` (REST). Discriminator field on tagged unions is `kind`.
- UI-facing domain types live in `lib/types.ts` with no suffix (`Meeting`, `Utterance`, `Person`).
- Adapter functions: `to<UIType>` (e.g. `toMeeting`, `toUtterance`).
- Hooks are camelCase verbs prefixed with `use` (`useLiveTranscript`, `useMeetingGraph`, `useAIDrawer`).

## Destructive actions

- **Every delete (or otherwise irreversible) action goes through a confirmation modal** before the mutation fires. The trigger button only opens the confirmation; only the confirm button calls `mutate()`.
- The confirmation is a nested `.backdrop` / `.modal` with `role="alertdialog"`, names the thing being deleted and its blast radius (e.g. "“Weekly sync” and its transcript, notes, and audio will be removed"), and offers Cancel plus a `.btn-danger` confirm. Escape and backdrop-click close the confirmation, not the parent modal.
- The only exception is when the user explicitly asks to skip the confirmation for a given action.

## Doing the right amount

- Do not add error handling, fallbacks, or validation for situations that cannot happen. Trust the backend's typed contract; validate only at the wire boundary (JSON parse inside `apiGet`, status check).
- Do not introduce new abstractions speculatively. Three similar lines beat a premature helper.
- Do not add backwards-compat shims, feature flags, or `// removed` placeholders. Delete unused code.
- A bug fix is not a refactor. Match the scope of the change to the task.
