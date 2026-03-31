---
id: repo-sync
name: Repo Sync
purpose: Prepare a managed local repo snapshot from a configured source path so workers operate on a consistent, isolated copy.
owner_agent: engineering
target_runtimes: [codex]
stage: active
inputs:
  - repo_id from infra/repos.json
outputs:
  - synced repo snapshot at state/repos/<repo-id>/
  - repo metadata record at state/checkpoints/platform/repos/<repo-id>.json
allowed_edit_boundaries:
  - state/repos/<repo-id>/
  - state/checkpoints/platform/repos/
forbidden_areas:
  - packages/
  - infra/ (read only — do not modify repos.json)
  - docs/
  - apps/
  - products/ (source path is read only)
dependencies:
  - infra/repos.json must contain a record for the requested repo_id
  - source_path from the repo record must exist and be a valid git repository
validation_steps:
  - repo record exists in infra/repos.json
  - source path exists and contains a git repository
  - state/repos/<repo-id>/ exists after sync
  - state/repos/<repo-id>/ contains a valid git working tree
  - no runtime state from state/ was copied into the snapshot
  - repo metadata checkpoint was written
handoff_contract:
  what_is_handed_off: repo_id and confirmed snapshot path at state/repos/<repo-id>/
  handed_to: worktree-lifecycle skill or bounded-codex-implementation skill
codex_adaptation_notes: |
  This skill runs BEFORE Codex — it prepares the repo that Codex will work against.
  The engineering worker executes this skill as a pre-step. Codex never reads this
  skill file directly.
---

## Instructions

### 1. Load repo configuration

Read `infra/repos.json` and find the record matching the requested `repo_id`.

Extract:
- `id` — the repo identifier
- `source_path` — the local path to the source of truth
- `default_branch` — the branch to sync from

If no record matches, fail with a clear error. Do not guess paths.

### 2. Validate source

Confirm `source_path` exists and is a git repository (contains `.git/` or is a valid git working tree).

If the source path is relative (e.g. `.` or `products/fishing-logbook-ios`), resolve it relative to the repo root.

### 3. Sync to managed snapshot

Sync the source tree into `state/repos/<repo-id>/`.

Sync rules:
- Use the source path as read-only input — do not modify it
- Exclude `state/` directories from the sync to prevent copying runtime artifacts
- Exclude `.claude/` worktree state from the sync
- Preserve git history (this is a working copy, not a shallow clone)
- If `state/repos/<repo-id>/` already exists, update it rather than recreating from scratch

For the current scaffold phase, `rsync` or `git worktree` from the source is acceptable. The important invariant is that `state/repos/<repo-id>/` reflects the source at sync time without carrying runtime pollution.

### 4. Validate snapshot

Confirm:
- `state/repos/<repo-id>/` exists
- It contains a valid git working tree
- The checked-out branch matches `default_branch` or is in a known-clean state
- No `state/` subdirectory was copied into the snapshot

### 5. Persist repo metadata

Write or update a metadata record at `state/checkpoints/platform/repos/<repo-id>.json` containing:

```json
{
  "repo_id": "<repo-id>",
  "source_path": "<resolved source path>",
  "snapshot_path": "state/repos/<repo-id>/",
  "synced_at": "<ISO 8601 timestamp>",
  "default_branch": "<branch>",
  "head_sha": "<current HEAD SHA of the snapshot>"
}
```

### 6. Hand off

The synced snapshot is now ready for worktree creation or direct use by downstream skills. Report the `repo_id` and snapshot path.
