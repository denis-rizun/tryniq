---
name: open-pr
description: Use when opening or creating a pull request for the current branch in this repo.
---

# Open PR

## Overview

Create the PR with the GitHub CLI, filling the repo's PR template
(`.github/pull_request_template.md`). Title uses the conventional-commit format.

## Steps

1. Ask the user: **"Which branch should the PR target?"** — default is `main`;
   wait for their answer before proceeding.
2. Read the commits and diff between the current branch and the target to
   understand every change.
3. Fill `.github/pull_request_template.md` (Summary + one bullet per concrete
   change).
4. `gh pr create --base <target> --title "<title>" --body "<body>"`

## Title

Conventional-commit format: `type(scope): action description` (same scopes as
the **commit** skill).

## Body

Use the template verbatim — a one-sentence Summary, then one bullet per concrete
change, and the generated-with footer. Bullet rules:

- One concrete, meaningful change per bullet.
- Start with a verb: `Add`, `Update`, `Fix`, `Remove`, `Refactor`.
- Name the real component/module/file in **bold** or `backticks`; be specific.

End the body with:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Example

```markdown
## Summary
Add lowest-load round-robin assignment of per-speaker streams to Swift workers.

---
- Add `LiveASRClient.assign_stream` load-based selection over registered `WorkerSession`s
- Update `IngestService._assign_swift_worker` to handle the no-worker fallback
- Add unit tests for round-robin ordering under mixed worker load

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
