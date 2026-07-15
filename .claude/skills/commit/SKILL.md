---
name: commit
description: Use when creating a git commit in this repo — staging changes, writing a commit message, or about to run git commit.
---

# Commit

## Overview

Conventional commits, **strictly atomic**. One commit = one logical change.

**A feature is not one commit.** Implementing a feature almost always produces
several commits (e.g. schema, endpoint, worker task, UI, tests). Bundling a whole
feature — or a fix plus a refactor — into a single commit is **not** atomic.
Default to **more, smaller commits**.

Only commit when the user asks. If you are on `main`, branch first (see
**prepare-branch** / **create-branch**).

## Format

```
type(scope): action description
```

- **type**: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`
- **scope**: the tryniq module or package the change lives in. Use one of:
  `meeting`, `asr`, `ingest`, `transcript`, `participant`, `api`, `worker`,
  `frontend`, `streamer`, `extension`, `evals`, `docs`, `core`.
- **action**: lowercase, present simple tense (`add`, `remove`, `update`, `fix`)
- **max 10 words** total; no period at the end

Examples:
```
feat(asr): round-robin streams by lowest worker load
fix(ingest): handle late-join SSE partial cache miss
refactor(meeting): simplify redis pub/sub client
docs(prd): add phase 3 graph builder contract
```

## Required trailer

Every commit message ends with the tryniq co-author trailer, after a blank line:

```
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

## How to split

1. `git diff --staged` (and `git diff` if nothing is staged) to see everything.
2. Group changes by **one scope, one concern** per commit.
3. Stage only that unit — `git add <file>` or `git add -p` — commit, repeat.
4. Never bundle unrelated changes. `git add -A` is only safe when every pending
   change is genuinely one logical unit.

## Rationalization table

| Excuse | Reality |
|--------|---------|
| "It's all one feature, so one commit" | A feature is many logical changes. Split them. |
| "These files changed together" | Changing together ≠ one concern. Group by intent. |
| "Splitting is tedious" | `git add -p` per concern is fast and makes review real. |
| "I'll squash later anyway" | Commit atomically now; don't defer the thinking. |

## Red flags — STOP and split

- One commit touching multiple scopes/modules
- A commit message needing "and" to describe two things
- A bug fix and a new feature in the same commit
- Staging with `git add -A` without checking the diff first
