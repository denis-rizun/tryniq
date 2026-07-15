---
name: create-branch
description: Use when creating a new git branch for a task, feature, or fix in this repo.
---

# Create Branch

## Overview

One branch = one concern, named `type/[ticket-]short-description`.

**Before creating the branch, ask the user for the task's ticket key.** Include
it in the name only if they give one; otherwise omit it.

## Format

```
type/short-description            # no ticket given
type/TICKET-KEY-short-description # ticket given, e.g. feat/ABC-123-graph-builder
```

- **type**: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`
  (same set as commit types)
- **description**: lowercase kebab-case, **max 5 words**, present-tense verbs
  (`add`, `remove`, `update`, `fix`)
- No underscores, no uppercase, no trailing slash

## Rules

- Base off `main` — see the **prepare-branch** skill to get onto an updated
  `main` first (`git checkout main` → `git pull origin main --rebase`).
- One branch, one concern. If the work spans unrelated concerns, make separate
  branches. Keep it small enough to review in one PR.

## Examples

```
feat/asr-round-robin
feat/ABC-123-graph-builder-window
fix/ingest-late-join
refactor/worker-session-sender
chore/remove-dead-moonshine-code
docs/prd-phase-3
```

Anti-examples:
```
feature/add-x        ❌ use short type feat/
feat/AddX            ❌ no camelCase
feat/add_x           ❌ no underscores
feat/fix-bug-and-add-feature   ❌ multiple concerns
```

## Steps

1. Ask the user for the ticket key (proceed without one if they have none).
2. Pick the `type` and a 2–5 word kebab-case description.
3. Ensure the base is ready (**prepare-branch**).
4. `git checkout -b <type>/[<ticket>-]<description>`
5. Confirm with `git branch --show-current`.
