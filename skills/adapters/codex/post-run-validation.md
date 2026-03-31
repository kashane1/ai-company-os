# Post-Run Validation and Artifact Capture — Codex Adapter

Canonical source: `skills/canonical/shared/post-run-validation.md`

This file documents how the engineering worker translates the canonical
`post-run-validation` skill into a post-execution validation and capture step.

Codex does not read this file at runtime. The engineering worker uses
the canonical definition to:

1. Collect Codex execution results (exit code, stdout, stderr, timestamps)
2. Validate prerequisites:
   - Worktree exists at `state/worktrees/<repo-id>/<task-id>/`
   - Task packet exists at `<worktree>/TASK_PACKET.md`
3. Capture diff artifact:
   - Generate via `git -C <worktree> diff --stat --patch`
   - Write to `state/artifacts/engineering/<task-id>/worktree.diff`
4. Capture logs:
   - `state/logs/engineering/<task-id>.stdout.log`
   - `state/logs/engineering/<task-id>.stderr.log`
   - execution metadata currently lands in `<worktree>/codex_execution.json`
5. Run validation checks:
   - Exit code is 0 → `codex_nonzero_exit`
   - Diff artifact exists
   - Testing policy compliance
6. Persist the richer current `TaskRun` record to `state/checkpoints/platform/task_runs/<run-id>.json`

The task run record and artifact paths are handed to the supervisor for
review routing. The engineering worker is responsible for calling this after
every Codex execution, whether successful or not.

## Current runtime status

This adapter is **operational but drifting from worker reality**.

- Implemented in `apps/worker-engineering/engineering/validator.py`
- Orchestrated in `apps/worker-engineering/engineering/runner.py`

Important divergence from the canonical definition:

- Logs are flat files under `state/logs/<lane>/`, not per-task directories
- Diff artifact path is `worktree.diff`, not `diff.patch`
- No explicit packet-tamper check exists
- No explicit boundary-violation check exists
- Worktree metadata is not updated to `completed` or `failed` after validation
- Execution metadata is stored in the worktree, not under `state/logs/`
