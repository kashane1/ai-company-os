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
   - Generate via `git -C <worktree> diff HEAD`
   - Write to `state/artifacts/engineering/<task-id>/diff.patch`
4. Capture logs:
   - `state/logs/engineering/<task-id>/stdout.log`
   - `state/logs/engineering/<task-id>/stderr.log`
   - `state/logs/engineering/<task-id>/execution.json` (structured metadata)
5. Run validation checks:
   - Exit code is 0 → `codex_nonzero_exit`
   - Diff is non-empty → `empty_diff`
   - No boundary violations → `boundary_violation`
   - Testing policy compliance → `missing_tests_for_logic_change`
   - Packet integrity → `packet_tampered`
6. Persist task run record to `state/checkpoints/platform/task_runs/<run-id>.json`
   with validation result, failure codes, testing policy data, and artifact paths
7. Update worktree metadata status to `completed` or `failed`

The task run record and artifact paths are handed to the supervisor for
review routing. The engineering worker is responsible for calling this after
every Codex execution, whether successful or not.
