# Repo Sync — Codex Adapter

Canonical source: `skills/canonical/shared/repo-sync.md`

This file documents how the engineering worker translates the canonical
`repo-sync` skill into a managed repo preparation step.

Codex does not read this file at runtime. The engineering worker uses
the canonical definition to:

1. Load repo config from `infra/repos.json` for the target `repo_id`
2. Resolve the `source_path` (relative paths resolve from repo root)
3. Sync the source tree into `state/repos/<repo-id>/`:
   - Source path is read-only — never modified
   - `state/` and `.claude/` directories are excluded from sync
   - Git history is preserved
   - Existing snapshots are updated, not recreated
4. Validate the snapshot:
   - Valid git working tree
   - Clean branch state matching `default_branch`
   - No runtime state pollution
5. Persist repo metadata to `state/checkpoints/platform/repos/<repo-id>.json`
   with `repo_id`, `source_path`, `snapshot_path`, `synced_at`, `default_branch`, `head_sha`

The snapshot at `state/repos/<repo-id>/` is the input for worktree creation.
The engineering worker is responsible for calling this before any worktree or
execution step.
