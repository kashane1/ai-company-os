---
id: post-run-validation
name: Post-Run Validation
purpose: Final gate on every task result before the control plane persists it. Each lane declares a contract describing the artifacts and event shape a completed task must emit; this skill validates against it.
owner_agent: supervisor
target_runtimes: [claude]
kind: validator
---

# Post-Run Validation

## Role

The control plane calls this skill inline from
`ControlPlaneService.submit_task_result` as the **final gate** before a
task transitions to `COMPLETED`. If the skill returns
`verdict=fail`, the control plane downgrades the submission to
`status=REJECTED` and emits a `task_result_rejected` event carrying the
`failure_code` so the failure-mode-regression skill can capture a
fixture.

## Inputs

- `lane` — `WorkerLane` value (engineering | ios | appstore | gtm)
- `task_type` — task packet type
- `result` — dict with `task_id`, `status=completed`, `artifacts: list[str]`,
  `events: list[str]`, and structured `failure_codes: list[str]`
- `repo_root` — for resolving relative artifact paths

## Contract lookup

The lane contract lives at
`skills/canonical/post-run-validation/contracts/<lane>.yaml`. Each
contract declares:

```yaml
required_artifacts:
  - path: <relative path, may include {task_id}>
required_events:
  - <event name>
forbidden_failure_codes:
  - <code that must never appear in structured failure_codes>
```

For engineering and iOS, the control plane first reads the deterministic
persisted `TaskRun` (`run-{task_id}`) through
`packages.policies.completion_evidence`. It binds task, repo, and lane;
requires passed validation and configured verification records; verifies the
review diff hash and logs; and checks the nonempty JSON review artifact against
the same task, worktree, paths, changed files, and testing policy. The skill
then receives that persisted provenance and persisted task events. Submission
summary, artifact, and event fields are not completion evidence for those lanes.

## Output

```json
{
  "verdict": "ok" | "fail",
  "failure_code": "<string or empty>",
  "reason": "<human-readable>",
  "lane": "<lane>"
}
```

## Failure codes

- `contract_missing`
- `required_artifact_missing`
- `required_event_missing`
- `forbidden_failure_code_present`
- `lane_unknown`
- `exception:<type>` — fail-closed wrapper caught an error

## Fixtures

- `fixtures/happy_path.json` — engineering lane, all artifacts + events
- `fixtures/boundary_no_artifacts.json` — empty artifacts list → fail
- `fixtures/adversarial_forbidden_code.json` — structured evidence contains a forbidden code

The fixture status is `passing` and the validator is wired into the
loader as a synchronous, hot-path skill.
