# Post-Run Validation and Artifact Capture — Codex Adapter

Canonical source: `skills/canonical/shared/post-run-validation.md`

This file documents how the engineering worker translates the canonical
`post-run-validation` skill into a post-execution validation and capture step.

Codex does not read this file at runtime. The engineering worker uses
the canonical definition to:

1. Capture diff artifact:
   - Generate via `git -C <worktree> diff --stat --patch`
   - Write to `state/artifacts/engineering/<task-id>/worktree.diff`
2. Run six validation checks:
   - `worktree_exists` — worktree directory exists
   - `packet_exists` — `TASK_PACKET.md` exists in worktree
   - `execution_result_exists` — `codex_last_message.md` exists in worktree
   - `codex_exit_code_zero` — exit code is 0
   - `diff_artifact_exists` — `worktree.diff` written to artifact path
   - `tests_with_code_policy` — testing policy satisfied (via `packages/policies/testing.py`)
3. Classify the result: `safe_for_review`, `no_change`, `validation_failed`, or `execution_failed`
4. Write review artifact to `state/artifacts/engineering/<task-id>/review_summary.json`
5. Create an approval record (if `safe_for_review`) at `state/checkpoints/platform/approvals/`
6. Persist the full `TaskRun` record to `state/checkpoints/platform/task_runs/run-<task-id>.json`

The task run record, classification, and artifact paths are handed to the
supervisor for review routing. The engineering worker calls this after
every Codex execution, whether successful or not.

## Current runtime status

This adapter is **aligned with worker reality** as of 2026-04-01.

- Validation: `apps/worker-engineering/engineering/validator.py`
- Classification and review: `apps/worker-engineering/engineering/review.py`
- Orchestration: `apps/worker-engineering/engineering/runner.py`
- Testing policy: `packages/policies/testing.py`
- Task run schema: `packages/schemas/task_run.py`

## Artifact path reference

| Artifact | Path |
|----------|------|
| Task packet | `<worktree>/TASK_PACKET.md` |
| Execution result | `<worktree>/codex_last_message.md` |
| Execution metadata | `<worktree>/codex_execution.json` |
| Stdout log | `state/logs/engineering/<task-id>.stdout.log` |
| Stderr log | `state/logs/engineering/<task-id>.stderr.log` |
| Diff | `state/artifacts/engineering/<task-id>/worktree.diff` |
| Review summary | `state/artifacts/engineering/<task-id>/review_summary.json` |
| Summary | `state/artifacts/engineering/<task-id>/summary.txt` |
| Task run record | `state/checkpoints/platform/task_runs/run-<task-id>.json` |
| Approval record | `state/checkpoints/platform/approvals/approval-<task-id>.json` |

## What is not yet implemented

These items appear in the canonical skill as target-contract behavior:

- **Boundary-violation check**: No post-hoc verification that Codex didn't modify files outside the worktree. Runtime relies on `--sandbox workspace-write` for enforcement.
- **Packet-tamper check**: No verification that `TASK_PACKET.md` was unmodified during execution.
- **Worktree metadata update**: Worktree status is not updated to `completed`/`failed` after validation.
- **Approval gate enforcement**: Approval record is created but does not yet block downstream git actions.
