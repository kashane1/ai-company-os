# Worktree Lifecycle — Codex Adapter

Canonical source: `skills/canonical/shared/worktree-lifecycle.md`

This file documents how the engineering worker translates the canonical
`worktree-lifecycle` skill into worktree preparation and management.

Codex does not read this file at runtime. The engineering worker uses
the canonical definition to:

1. Validate that `state/repos/<repo-id>/` exists (via repo-sync)
2. Validate that the task record exists and is runnable
3. Check for an existing worktree at `state/worktrees/<repo-id>/<task-id>/`:
   - Reuse if valid
   - Remove and recreate if corrupt
   - Create fresh if absent
4. Create an isolated git worktree:
   - Path: `state/worktrees/<repo-id>/<task-id>/`
   - Branch: `task/<task-id>` (new branch from snapshot HEAD)
   - Command: `git -C state/repos/<repo-id>/ worktree add state/worktrees/<repo-id>/<task-id>/ -b task/<task-id>`
5. Validate the worktree:
   - Valid git working tree
   - Correct branch checked out
   - Clean starting state
6. Persist worktree metadata to `state/checkpoints/platform/worktrees/<repo-id>--<task-id>.json`
   with `repo_id`, `task_id`, `worktree_path`, `branch`, `created_at`, `base_sha`, `status`

The worktree at `state/worktrees/<repo-id>/<task-id>/` is the working directory
for Codex execution. The managed repo snapshot remains read-only while the
worktree is active.

Cleanup expectations (post-lifecycle):
- Worktrees remain on disk after execution for inspection and artifact capture
- Removal happens only after the full task lifecycle completes
- Failed worktrees are preserved for debugging
- Removal: `git worktree remove` + branch deletion + metadata status update
