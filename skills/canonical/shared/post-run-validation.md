---
id: post-run-validation
name: Post-Run Validation and Artifact Capture
purpose: Validate Codex execution results, capture structured artifacts, and persist a reviewable task run record.
owner_agent: engineering
target_runtimes: [codex]
stage: active
inputs:
  - task_id referencing the executed task
  - repo_id for path resolution
  - codex execution result (exit code, stdout, stderr, timestamps)
  - worktree path at state/worktrees/<repo-id>/<task-id>/
outputs:
  - diff artifact at state/artifacts/engineering/<task-id>/diff.patch
  - execution logs at state/logs/engineering/<task-id>/
  - task run record at state/checkpoints/platform/task_runs/<run-id>.json
  - validation result (pass/fail with structured failure codes)
allowed_edit_boundaries:
  - state/artifacts/engineering/<task-id>/
  - state/logs/engineering/<task-id>/
  - state/checkpoints/platform/task_runs/
  - state/checkpoints/platform/worktrees/ (status update only)
forbidden_areas:
  - state/worktrees/<repo-id>/<task-id>/ (read-only during validation — do not modify execution output)
  - packages/
  - infra/
  - docs/
  - apps/
dependencies:
  - bounded-codex-implementation must have completed (execution result available)
  - worktree must exist at state/worktrees/<repo-id>/<task-id>/
  - task packet must exist at state/worktrees/<repo-id>/<task-id>/TASK_PACKET.md
validation_steps:
  - worktree exists at expected path
  - task packet exists in worktree
  - codex exit code is recorded
  - diff artifact was generated and written
  - log files were written
  - task run record was persisted with all required fields
  - validation result includes structured failure codes when applicable
handoff_contract:
  what_is_handed_off: task run ID, validation result, artifact paths, review-ready summary
  handed_to: supervisor for review routing and optional approval
codex_adaptation_notes: |
  This skill runs AFTER Codex — it validates and captures what Codex produced.
  The engineering worker executes this skill as a post-step. Codex never reads
  this skill file directly.
---

## Instructions

### 1. Collect execution inputs

Gather from the completed Codex invocation:
- `exit_code` — the Codex CLI exit code
- `stdout` — captured standard output
- `stderr` — captured standard error
- `started_at` — execution start timestamp
- `finished_at` — execution end timestamp
- `last_agent_message` — the final agent message from Codex output (if extractable)

Gather from context:
- `task_id`
- `repo_id`
- `worktree_path` — `state/worktrees/<repo-id>/<task-id>/`

### 2. Validate execution prerequisites

Confirm:
- Worktree exists at `state/worktrees/<repo-id>/<task-id>/`
- Task packet exists at `<worktree_path>/TASK_PACKET.md`
- Codex execution result is available (exit code is not null)

If any prerequisite is missing, record a `PREREQUISITES_MISSING` failure and skip to step 6.

### 3. Capture diff artifact

Generate a diff of all changes in the worktree:

```
git -C <worktree_path> diff HEAD
```

Write the diff to `state/artifacts/engineering/<task-id>/diff.patch`.

If the diff is empty (no changes), record this as a validation note. An empty diff with exit code 0 may indicate Codex determined no changes were needed — this is not automatically a failure but must be flagged for review.

### 4. Capture logs

Write execution logs to `state/logs/engineering/<task-id>/`:
- `stdout.log` — Codex standard output
- `stderr.log` — Codex standard error
- `execution.json` — structured execution metadata:

```json
{
  "task_id": "<task-id>",
  "repo_id": "<repo-id>",
  "exit_code": <exit_code>,
  "started_at": "<ISO 8601>",
  "finished_at": "<ISO 8601>",
  "worktree_path": "<worktree_path>",
  "last_agent_message": "<extracted or null>"
}
```

### 5. Run validation checks

Execute each check and record the result:

| Check | Pass condition | Failure code |
|-------|---------------|--------------|
| Exit code | Codex exited with code 0 | `codex_nonzero_exit` |
| Diff exists | `diff.patch` exists and is non-empty | `empty_diff` |
| Boundary compliance | No files modified outside `<worktree_path>` | `boundary_violation` |
| Testing policy | Lane-matching tests created/modified for logic changes, or valid no-test exception | `missing_tests_for_logic_change` |
| Packet integrity | `TASK_PACKET.md` still exists unmodified in worktree | `packet_tampered` |

**Testing policy evaluation**:
- Identify whether the diff contains logic-bearing changes (not just docs, comments, config, or generated files)
- If logic-bearing: check whether lane-matching test files were created or modified
- If no tests: check whether the Codex output contains a valid machine-readable `no_test_reason_code`
- Valid no-test codes: `docs_only`, `generated_file`, `visual_only_no_logic`, `comments_only`, `config_no_behavior_change`, `approved_followup_test_task`
- If `approved_followup_test_task`: verify the referenced task exists in `state/checkpoints/platform/tasks/`, is open, and matches the lane

Aggregate result:
- If all checks pass: `VALIDATION_PASSED`
- If any check fails: `VALIDATION_FAILED` with the list of failure codes

### 6. Persist task run record

Write a task run record to `state/checkpoints/platform/task_runs/<run-id>.json`:

```json
{
  "run_id": "<generated run ID>",
  "task_id": "<task-id>",
  "repo_id": "<repo-id>",
  "worktree_path": "<worktree_path>",
  "started_at": "<ISO 8601>",
  "finished_at": "<ISO 8601>",
  "exit_code": <exit_code>,
  "validation_result": "VALIDATION_PASSED | VALIDATION_FAILED",
  "failure_codes": ["<code>", ...],
  "testing_policy": {
    "logic_bearing_changes": true | false,
    "tests_added_or_modified": true | false,
    "no_test_reason_code": "<code or null>",
    "followup_task_id": "<task-id or null>"
  },
  "artifacts": {
    "diff": "state/artifacts/engineering/<task-id>/diff.patch",
    "stdout": "state/logs/engineering/<task-id>/stdout.log",
    "stderr": "state/logs/engineering/<task-id>/stderr.log",
    "execution_metadata": "state/logs/engineering/<task-id>/execution.json"
  }
}
```

### 7. Update worktree metadata

Update the worktree metadata at `state/checkpoints/platform/worktrees/<repo-id>--<task-id>.json`:
- Set `status` to `completed` if validation passed, `failed` otherwise
- Add `validated_at` timestamp

### 8. Hand off

Report to the supervisor:
- Task run ID
- Validation result and any failure codes
- Paths to all captured artifacts
- Whether the task run is review-ready or needs intervention
