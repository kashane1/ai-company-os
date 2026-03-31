---
id: worktree-lifecycle
name: Worktree Lifecycle
purpose: Create, validate, and define cleanup expectations for task-isolated worktrees used during engineering execution.
owner_agent: engineering
target_runtimes: [codex]
stage: active
inputs:
  - repo_id referencing a synced snapshot at state/repos/<repo-id>/
  - task_id referencing a persisted engineering task
outputs:
  - isolated worktree at state/worktrees/<repo-id>/<task-id>/
  - worktree metadata record at state/checkpoints/platform/worktrees/<repo-id>--<task-id>.json
allowed_edit_boundaries:
  - state/worktrees/<repo-id>/<task-id>/
  - state/checkpoints/platform/worktrees/
forbidden_areas:
  - state/repos/<repo-id>/ (source snapshot is read-only during worktree use)
  - packages/
  - infra/
  - docs/
  - apps/
dependencies:
  - repo must be synced to state/repos/<repo-id>/ (via repo-sync skill)
  - task must exist in state/checkpoints/platform/tasks/<task-id>.json
validation_steps:
  - managed repo snapshot exists at state/repos/<repo-id>/
  - task record exists and is in a runnable state (pending or in_progress)
  - worktree was created at state/worktrees/<repo-id>/<task-id>/
  - worktree is a valid git working tree
  - worktree is isolated from the managed repo snapshot (changes in one do not affect the other)
  - worktree metadata checkpoint was written
handoff_contract:
  what_is_handed_off: worktree path at state/worktrees/<repo-id>/<task-id>/, worktree metadata record
  handed_to: codex-task-packet-library skill (for packet rendering) then bounded-codex-implementation skill (for execution)
codex_adaptation_notes: |
  This skill runs BEFORE Codex — it prepares the workspace Codex will write into.
  The engineering worker executes this skill as a pre-step. Codex never reads this
  skill file directly. Codex only sees the worktree as its working directory.
---

## Instructions

### 1. Validate preconditions

Confirm:
- `state/repos/<repo-id>/` exists and is a valid git repository (via repo-sync)
- Task record exists at `state/checkpoints/platform/tasks/<task-id>.json`
- Task status is `pending` or `in_progress`

If preconditions fail, report the specific failure. Do not create a worktree against an unsynced or missing repo.

### 2. Check for existing worktree

Check whether `state/worktrees/<repo-id>/<task-id>/` already exists.

- If it exists and is a valid git worktree: reuse it. Log that an existing worktree was found.
- If it exists but is invalid (corrupt, not a git tree): remove it and recreate.
- If it does not exist: proceed to creation.

### 3. Create the worktree

Create an isolated git worktree from the managed repo snapshot:

```
git -C state/repos/<repo-id>/ worktree add state/worktrees/<repo-id>/<task-id>/ -b task/<task-id>
```

Naming conventions:
- **Path**: `state/worktrees/<repo-id>/<task-id>/`
- **Branch**: `task/<task-id>` — a new branch created from the snapshot HEAD

The worktree must be isolated: file changes inside the worktree do not affect the managed repo snapshot, and vice versa.

### 4. Validate the worktree

Confirm:
- `state/worktrees/<repo-id>/<task-id>/` exists
- It is a valid git working tree (`git -C <path> rev-parse --is-inside-work-tree`)
- The checked-out branch is `task/<task-id>`
- No uncommitted changes exist at creation time (clean starting state)

### 5. Persist worktree metadata

Write or update a metadata record at `state/checkpoints/platform/worktrees/<repo-id>--<task-id>.json` containing:

```json
{
  "repo_id": "<repo-id>",
  "task_id": "<task-id>",
  "worktree_path": "state/worktrees/<repo-id>/<task-id>/",
  "branch": "task/<task-id>",
  "created_at": "<ISO 8601 timestamp>",
  "base_sha": "<SHA the worktree was created from>",
  "status": "active"
}
```

### 6. Hand off

The worktree is ready for task packet rendering and Codex execution. Report the worktree path and metadata.

---

## Cleanup expectations

Worktree cleanup is not part of creation but has defined expectations:

### After successful execution
- The worktree remains on disk for inspection and artifact capture
- The worktree metadata status may be updated to `completed` after post-run validation
- Cleanup (removal of the worktree directory and git branch) happens only after the full task lifecycle completes and artifacts are captured

### After failed execution
- The worktree remains on disk for debugging
- The worktree metadata status is updated to `failed`
- Cleanup is deferred to a separate maintenance pass or manual action

### Staleness
- Worktrees older than a configurable threshold (default: not enforced in v1) may be flagged for cleanup
- Automated cleanup is not implemented in v1 — staleness is advisory only

### Removal procedure
When cleanup is authorized:
1. Remove the git worktree: `git -C state/repos/<repo-id>/ worktree remove state/worktrees/<repo-id>/<task-id>/`
2. Delete the task branch if no longer needed: `git -C state/repos/<repo-id>/ branch -d task/<task-id>`
3. Update worktree metadata status to `removed`
