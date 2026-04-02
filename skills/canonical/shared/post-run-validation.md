---
id: post-run-validation
name: Post-Run Validation and Artifact Capture
purpose: Validate Codex execution results, capture structured artifacts, classify the outcome, and persist a reviewable task run record.
owner_agent: engineering
target_runtimes: [codex]
stage: active
inputs:
  - task_id referencing the executed task
  - repo_id for path resolution
  - codex execution result (exit code, stdout, stderr, timestamps, timed_out flag)
  - worktree path at state/worktrees/<repo-id>/<task-id>/
  - execution result file at <worktree>/codex_last_message.md
  - pre-run and post-run git state snapshots (status_lines, changed_files, diff_summary)
outputs:
  - diff artifact at state/artifacts/engineering/<task-id>/worktree.diff
  - review summary at state/artifacts/engineering/<task-id>/review_summary.json
  - execution logs at state/logs/engineering/<task-id>.stdout.log and <task-id>.stderr.log
  - execution metadata at <worktree>/codex_execution.json
  - task run record at state/checkpoints/platform/task_runs/run-<task-id>.json
  - validation result (pass/fail with structured failure codes)
  - result classification (safe_for_review, no_change, validation_failed, execution_failed)
  - approval record at state/checkpoints/platform/approvals/ (if safe_for_review)
allowed_edit_boundaries:
  - state/artifacts/engineering/<task-id>/
  - state/logs/engineering/
  - state/checkpoints/platform/task_runs/
  - state/checkpoints/platform/approvals/
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
  - execution result must exist at <worktree>/codex_last_message.md
validation_steps:
  - worktree exists at expected path
  - task packet exists in worktree
  - execution result file exists in worktree
  - codex exit code is 0
  - diff artifact was generated and written
  - testing policy is satisfied
  - task run record was persisted with all required fields
  - validation result includes structured failure codes when applicable
handoff_contract:
  what_is_handed_off: task run ID, classification, validation result, artifact paths, review-ready summary, approval record (if applicable)
  handed_to: supervisor for review routing and optional approval
codex_adaptation_notes: |
  This skill runs AFTER Codex — it validates and captures what Codex produced.
  The engineering worker executes this skill as a post-step. Codex never reads
  this skill file directly. Orchestrated by runner.py using validator.py and review.py.
---

## Instructions

### 1. Collect execution inputs

Gather from the completed Codex invocation (via `CodexExecutionRecord`):
- `exit_code` — the Codex CLI exit code (-1 if timed out)
- `stdout_path` — path to captured stdout log
- `stderr_path` — path to captured stderr log
- `started_at` / `finished_at` — execution timestamps
- `timed_out` — whether execution hit the timeout limit
- `command` / `command_display` — the Codex CLI invocation used

Gather from context:
- `task_id`
- `repo_id`
- `worktree_path` — `state/worktrees/<repo-id>/<task-id>/`
- `execution_result_path` — `<worktree>/codex_last_message.md`
- `pre_run_git_state` / `post_run_git_state` — git state snapshots captured before and after execution

### 2. Capture diff artifact

Generate a diff of all changes in the worktree:

```
git -C <worktree_path> diff --stat --patch
```

Write the diff to `state/artifacts/engineering/<task-id>/worktree.diff`.

If the diff is empty (no changes), record this as a validation note. An empty diff with exit code 0 may indicate Codex determined no changes were needed — this is not automatically a failure but feeds into classification as `no_change`.

### 3. Run validation checks

Execute each check and record a `ValidationCheck(name, passed, details, code)`:

| Check | Name | Pass condition | Failure code |
|-------|------|---------------|--------------|
| Worktree exists | `worktree_exists` | Worktree directory exists at expected path | — |
| Packet exists | `packet_exists` | `TASK_PACKET.md` exists in worktree | — |
| Execution result exists | `execution_result_exists` | `codex_last_message.md` exists in worktree | — |
| Exit code | `codex_exit_code_zero` | Codex exited with code 0 | — |
| Diff artifact exists | `diff_artifact_exists` | `worktree.diff` exists at artifact path | — |
| Testing policy | `tests_with_code_policy` | Lane-matching tests created/modified for logic changes, or valid no-test exception | failure code from testing policy evaluation |

Aggregate result:
- If all checks pass: `SUCCEEDED`
- If any check fails: `FAILED` with the list of failure codes

**Testing policy evaluation** (implemented in `packages/policies/testing.py`):

1. Parse testing metadata from the `## Testing` section of `codex_last_message.md`
   - Extract `no_test_reason_code` and `followup_task_id` via regex
   - If no Testing section exists: `missing_testing_metadata` failure
2. Identify logic-bearing changes by lane:
   - Python lane: files in `apps/` or `packages/` (excluding `tests/python/`)
   - iOS lane: files in `products/<product>/Sources/`
3. If no logic-bearing changes: no tests required (pass)
4. If logic-bearing changes exist:
   - Check for lane-matching test files added or modified
   - Python lane tests: files in `tests/python/`
   - iOS lane tests: files in `products/<product>/Tests/`
5. If no matching tests found, check for valid no-test exception:
   - Valid codes: `COMMENTS_ONLY`, `VISUAL_ONLY_NON_LOGIC`, `CONFIG_NO_BEHAVIOR_CHANGE`, `APPROVED_FOLLOWUP_TEST_TASK`
   - If `APPROVED_FOLLOWUP_TEST_TASK`: verify the referenced task exists, is open (pending/in_progress/blocked), matches the lane and repo
   - Invalid code: `invalid_no_test_reason_code` failure
   - Invalid followup reference: `invalid_followup_test_task_reference` failure
6. If no tests and no valid exception: `missing_tests_for_logic_change` failure

> **Not yet implemented:** Boundary-violation checks (verifying no files modified outside the worktree) and packet-tamper checks (verifying TASK_PACKET.md was not modified during execution) are described as target-contract behavior. The runtime currently relies on Codex sandbox mode (`--sandbox workspace-write`) for boundary enforcement and does not perform post-hoc verification.

### 4. Classify the result

Determine the result classification (implemented in `engineering/review.py`):

| Classification | Condition |
|----------------|-----------|
| `execution_failed` | Exit code ≠ 0 |
| `validation_failed` | Any validation check failed (exit code was 0) |
| `no_change` | All checks passed but no files changed |
| `safe_for_review` | All checks passed and files changed |

Classification drives the final task status:
- `safe_for_review` or `no_change` → task status `COMPLETED`
- `execution_failed` or `validation_failed` → task status `FAILED`

### 5. Write review artifact

Write a review summary to `state/artifacts/engineering/<task-id>/review_summary.json`:

```json
{
  "task_id": "<task-id>",
  "worktree_path": "<worktree_path>",
  "changed_files": ["<file>", ...],
  "validator_results": [{"name": "...", "passed": true, "details": "...", "code": null}, ...],
  "testing_policy": { ... },
  "testing_summary": "<from ## Testing section>",
  "failure_codes": ["<code>", ...],
  "stdout_path": "<path>",
  "stderr_path": "<path>",
  "diff_path": "<path>",
  "summary": "<human-readable summary>",
  "created_at": "<ISO 8601>"
}
```

### 6. Create approval record (if safe_for_review)

If classification is `safe_for_review`, create an approval record at `state/checkpoints/platform/approvals/approval-<task-id>.json` with status `PENDING`.

> **Not yet implemented:** The approval record is created but does not yet gate downstream actions (commit, push, PR, merge). These remain manual. The approval gate is scaffolding for future enforcement.

### 7. Persist task run record

Write a task run record to `state/checkpoints/platform/task_runs/run-<task-id>.json`. The record includes:

- `id`, `task_id`, `worker_lane`, `repo_id`
- `worktree_id`, `worktree_path`, `packet_path`, `execution_result_path`
- `execution` — full `CodexExecutionRecord` (command, paths, exit code, timestamps, timed_out)
- `pre_run_git_state` / `post_run_git_state` — `GitStateSnapshot` (status_lines, changed_files, diff_summary)
- `diff_path`, `classification`, `review_artifact_path`, `approval_id`
- `status` — `succeeded` or `failed`
- `summary` — human-readable result description
- `started_at` / `finished_at`
- `validation_checks` — list of `ValidationCheck` results
- `testing_policy` — `TestingPolicyResult` (or null)
- `failure_codes` — list of failure code strings
- `artifacts` — list of all artifact paths (packet, execution result, stdout, stderr, diff, review summary, summary.txt, execution metadata)

### 8. Hand off

Report to the supervisor (via `TaskResult`):
- Task run ID and classification
- Validation result and any failure codes
- Paths to all captured artifacts
- Whether the task run is review-ready or needs intervention
- Approval ID (if applicable)
- Suggested next actions:
  - Inspect the review artifact and diff before any git history mutation
  - Use the approval record as the future gate for commit, push, and PR phases

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
