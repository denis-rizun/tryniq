---
name: prepare-branch
description: Use when starting a new task or feature in this repo, before creating a branch or making any changes.
---

# Prepare Branch

## Overview

Every task starts from a fresh `main`. Update `main`, then branch off it — never
build a task on a stale base or directly on `main`.

## Steps

1. Make sure the working tree is clean (`git status`). Commit or stash first.
2. Get onto an up-to-date `main`:
   ```
   git checkout main
   git pull origin main --rebase
   ```
3. Create the task branch. **REQUIRED SUB-SKILL:** use **create-branch** (it
   asks for the ticket key and enforces the naming convention).
4. Only then start implementing.

## Notes

- Base branch is always `main`.
- If work already exists on another branch that this task depends on and is not
  yet merged, base off that branch instead and rebase onto `main` once it lands.
