---
id: bounded-codex-implementation
name: Bounded Codex Implementation
purpose: Execute a scoped code change through Codex CLI within an isolated worktree with explicit constraints.
owner_agent: engineering
target_runtimes: [codex]
stage: active
inputs:
  - task_id referencing a persisted engineering task
  - repo_id from infra/repos.json
  - task objective (title + summary from the task record)
  - explicit constraints list from the task record
outputs:
  - modified files within the task worktree
  - diff artifact at state/artifacts/engineering/<task-id>/
  - task run record at state/checkpoints/platform/task_runs/
  - execution logs at state/logs/engineering/
allowed_edit_boundaries:
  - state/worktrees/<repo-id>/<task-id>/
  - state/artifacts/engineering/<task-id>/
  - state/logs/engineering/
  - state/checkpoints/platform/task_runs/
forbidden_areas:
  - packages/policies/
  - packages/schemas/
  - infra/
  - docs/
  - apps/ (except through the worktree copy)
dependencies:
  - task must exist in state/checkpoints/platform/tasks/
  - repo must be synced to state/repos/<repo-id>/
validation_steps:
  - worktree was created at the expected path
  - task packet was rendered and written to the worktree
  - codex CLI exited with code 0
  - diff artifact is non-empty
  - no files modified outside the worktree boundary
  - task run record was persisted
handoff_contract:
  what_is_handed_off: task run ID, diff artifact path, validation result
  handed_to: supervisor for review and optional approval routing
codex_adaptation_notes: |
  This skill IS the Codex execution flow. The task packet rendered into the
  worktree is the direct Codex input. The engineering worker orchestrates the
  surrounding steps (sync, worktree, validate, persist).
---

## Instructions

### 1. Load the task

Read the task record from `state/checkpoints/platform/tasks/<task-id>.json`.
Confirm status is `pending` or `in_progress`.
Extract `repo_id`, `title`, `summary`, `constraints`, and `risk_level`.

### 2. Prepare the worktree

Confirm the managed repo exists at `state/repos/<repo-id>/`.
Create an isolated worktree at `state/worktrees/<repo-id>/<task-id>/`.

### 3. Render the task packet

Generate a markdown task packet containing:

```
# Task: <title>

## Objective
<summary>

## Rules
- Work only inside this worktree
- Do not modify files outside the repository root
- Do not commit or push
- Leave changes uncommitted for inspection

## Constraints
<one bullet per constraint from the task record>
```

Write the packet to `<worktree>/TASK_PACKET.md`.

### 4. Execute via Codex CLI

Run `codex exec` with:

- working directory: the worktree path
- stdin: the rendered task packet
- sandbox mode: workspace-write
- no auto-commit

Capture stdout, stderr, exit code, and timestamps.

### 5. Capture artifacts

Generate a diff of all worktree changes.
Write the diff to `state/artifacts/engineering/<task-id>/diff.patch`.
Write stdout/stderr logs to `state/logs/engineering/<task-id>/`.

### 6. Validate

- Codex exit code is 0
- Diff artifact exists and is non-empty
- No files modified outside `state/worktrees/<repo-id>/<task-id>/`

### 7. Persist the task run

Write a task run record to `state/checkpoints/platform/task_runs/<run-id>.json` containing status, timestamps, artifact paths, and validation results.
