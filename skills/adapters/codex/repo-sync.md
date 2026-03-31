# Repo Sync — Codex Adapter

Canonical source: `skills/canonical/shared/repo-sync.md`

This file documents how the engineering worker translates the canonical
`repo-sync` skill into a managed repo preparation step.

Codex does not read this file at runtime. The engineering worker uses
the canonical definition to:

1. Load repo config from `infra/repos.json` for the target `repo_id`
2. Resolve the `source_path` (relative paths resolve from repo root)
3. Copy the source tree into `state/repos/<repo-id>/`:
   - Source path is read-only
   - `state/`, `.git`, common cache directories, and `__pycache__` are excluded
   - The destination is cleared before each sync
   - A fresh git snapshot is initialized inside the managed repo copy
4. Validate the snapshot:
   - Valid git working tree after re-initialization
   - No copied runtime state pollution
5. Persist repo metadata to `state/checkpoints/platform/repos/<repo-id>.json`
   using the current `RepoRecord` schema

The snapshot at `state/repos/<repo-id>/` is the input for worktree creation.
The engineering worker is responsible for calling this before any worktree or
execution step.

## Current runtime status

This adapter is **operational but drifting from the canonical skill**.

- Implemented in `apps/worker-engineering/engineering/repo_manager.py`
- File copy behavior lives in `apps/worker-engineering/engineering/file_sync.py`
- Git snapshot re-initialization lives in `apps/worker-engineering/engineering/git_state.py`

Important divergence from the canonical definition:

- The runtime does not preserve source git history in the managed snapshot.
- The runtime recreates a clean git repo with a baseline commit on each sync.
- The persisted repo record stores `managed_path`, `sync_status`, and `last_synced_at`, not `snapshot_path`, `synced_at`, and `head_sha`.
