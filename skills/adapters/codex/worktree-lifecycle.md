# Worktree Lifecycle — Codex Adapter

Canonical source: `skills/canonical/shared/worktree-lifecycle.md`

This file documents how the engineering worker translates the canonical
`worktree-lifecycle` skill into worktree preparation and management.

Codex does not read this file at runtime. The engineering worker uses
the canonical definition to:

1. Validate that `state/repos/<repo-id>/` exists (via repo-sync)
2. Clone the managed repo snapshot into `state/worktrees/<repo-id>/<task-id>/`
3. Write worker-owned helper files such as `workspace_context.txt`
4. Persist worktree metadata to `state/checkpoints/platform/worktrees/worktree-<task-id>.json`
   using the current `WorktreeMetadata` schema

The worktree at `state/worktrees/<repo-id>/<task-id>/` is the working directory
for Codex execution. The managed repo snapshot remains read-only while the
worktree is active.

## Current runtime status

This adapter is a **useful contract but not yet reflected in runtime**.

- Implemented today in `apps/worker-engineering/engineering/worktree_manager.py`
- Path helper lives in `packages/tools/worktrees.py`

Important divergence from the canonical definition:

- The runtime uses `git clone` of the managed snapshot, not `git worktree add`
- Existing worktrees are not reused; the directory is cleared and recreated every run
- No task branch such as `task/<task-id>` is created
- The persisted metadata schema has `id`, `root_path`, `status`, `created_at`, and optional `packet_path`, but not `branch`, `base_sha`, or `validated_at`

Cleanup expectations (post-lifecycle):
- Worktrees remain on disk after execution for inspection and artifact capture
- Removal happens only after the full task lifecycle completes
- Failed worktrees are preserved for debugging
- Removal: `git worktree remove` + branch deletion + metadata status update
