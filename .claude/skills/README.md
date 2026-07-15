# Skills

Project skills for tryniq. Each skill is a directory containing a `SKILL.md`
file (`name` + `description` frontmatter, then imperative instructions). Claude
Code auto-discovers them here — no sync step. These are real, git-tracked files
(tryniq does not use the symlink/`agents/`-root pattern).

Current skills cover the git workflow:

| Skill            | When to use                                              |
|------------------|----------------------------------------------------------|
| `prepare-branch` | Starting any new task, before branching.                 |
| `create-branch`  | Creating the task branch (`type/[ticket-]description`).  |
| `commit`         | Making an atomic Conventional Commit.                    |
| `open-pr`        | Opening the PR (fills `.github/pull_request_template.md`).|

Normal flow: `prepare-branch` → `create-branch` → work → `commit` (many) →
`open-pr`.

> The project `commit` skill intentionally shadows the global harness `commit`
> skill so commits follow tryniq's scopes and required co-author trailer.

## SKILL.md format

```markdown
---
name: skill-name
description: When to use this skill — the trigger conditions, written so an
  agent can decide relevance from this line alone.
---

Step-by-step instructions for performing the skill.
```

- `name` matches the directory name (kebab-case).
- `description` leads with the triggering situation.

## Adding a skill

1. Create `skills/<name>/SKILL.md` with the frontmatter above.
2. Write clear, imperative instructions; keep the skill focused on one job.
3. Add any supporting files the skill references into the same directory.

Add skills one at a time.
