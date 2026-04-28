---
id: test-coverage-audit
name: Test Coverage Audit
purpose: Audit a worktree diff against the coverage policy in `packages/policies/testing.py` BEFORE commit. Catches coverage regressions in the same task that introduced them, instead of as post-merge follow-up tickets.
owner_agent: engineering
target_runtimes: [claude, codex]
stage: deferred
inputs:
  - worktree_path (string) — defaults to repo root
  - changed_files (list of string, optional) — auto-detected via `git diff --name-only main...HEAD` if absent
  - coverage_report_path (string, optional) — path to a pre-generated coverage report; if absent, Codex adapter triggers generation
outputs:
  - TestCoverageVerdict
    - coverage_percent (object: {python: float, ios: float, overall: float})
    - policy_verdict (enum: meets_policy | needs_tests | valid_exception)
    - tests_to_add (list of {file, line_range, reason})
    - exemption_reason (NoTestReasonCode or null)
allowed_edit_boundaries:
  - state/artifacts/coverage/<branch>/
forbidden_areas:
  - packages/policies/ (read-only input)
  - tests/ (this skill audits, never modifies, tests)
  - products/ (no source modification)
dependencies:
  - packages/policies/testing.py exists and is readable
  - git is available for diff detection
  - coverage tooling (Python: `coverage`, iOS: `xccov`) is installed when the Codex adapter runs
validation_steps:
  - coverage_percent has all three keys (python, ios, overall)
  - policy_verdict is one of the three enumerated values
  - tests_to_add is non-empty when policy_verdict == needs_tests
  - exemption_reason is a real NoTestReasonCode member when policy_verdict == valid_exception
handoff_contract:
  what_is_handed_off: TestCoverageVerdict
  handed_to: the actor about to commit / open a PR. They use it to add tests, request an exemption, or proceed.
claude_adaptation_notes: |
  Claude consumes the coverage report (parsed by the Codex adapter) and
  the worktree diff. For each changed file with insufficient coverage,
  Claude proposes specific tests to add (file:line_range:reason) by
  reading the changed lines. Claude does NOT run coverage tooling — the
  Codex adapter owns that path.
codex_adaptation_notes: |
  Codex owns coverage tool invocation: `coverage run` + `coverage json`
  for Python; `xcodebuild -enableCodeCoverage YES` + `xccov view --json`
  for iOS. Codex parses the output into the structured `coverage_percent`
  object and writes the report to `state/artifacts/coverage/<branch>/`.
  Codex does NOT propose tests — that's Claude's slice.
---

> **stage: deferred** — registered ahead of activation. Coverage tooling
> is not yet wired into the Codex pipeline (no project-level `coverage`
> config, no `xccov` invocation in worker-ios). Activate by moving
> `stage: active` once the tooling is configured. Until then, this
> skill is contract-frozen.

## Instructions

### 1. Detect the change set

If `changed_files` is not provided, run:

```
git diff --name-only main...HEAD
```

Filter to logic-bearing files only (drop `.md`, `.yaml` config, `.json` fixtures). Per-lane policy:

- Python lane: `*.py` under `packages/`, `apps/` (excluding `apps/*/main.py` if it's a thin entry point per `testing.py` rules).
- iOS lane: `*.swift` under `products/<product>-ios/`.

### 2. Generate or load the coverage report

If `coverage_report_path` is provided, parse it. Otherwise, the Codex adapter runs:

- Python: `coverage run -m pytest && coverage json -o <report>`
- iOS: `xcodebuild test -enableCodeCoverage YES ... && xccov view --json <result_bundle>`

Write the parsed report to `state/artifacts/coverage/<branch>/<lane>.json`.

### 3. Apply policy

Read `packages/policies/testing.py`. Required thresholds (current values, may shift — always read live):

- Python: ≥ 55% line coverage on changed files
- iOS: ≥ 20% line coverage on changed files
- Overall: meets the higher of the two when both lanes are present

Apply per-file:

- If a changed file's coverage is below the lane threshold AND the file is logic-bearing, add it to `tests_to_add`.
- If the actor declared a `NoTestReasonCode` (e.g. `CONFIG_NO_BEHAVIOR_CHANGE`, `COMMENTS_ONLY`) and the diff matches the reason, mark `exemption_reason` and skip threshold enforcement for that file.

### 4. Bucket the verdict

| Verdict | When |
|---|---|
| `meets_policy` | Every logic-bearing file meets the threshold or has a valid exemption. `tests_to_add` is empty. |
| `needs_tests` | At least one logic-bearing file is below threshold with no exemption. `tests_to_add` lists each one. |
| `valid_exception` | Diff is logic-bearing in shape but covered by a documented `NoTestReasonCode`. `exemption_reason` set. |

### 5. Propose tests (Claude's slice)

For each entry in `tests_to_add`, Claude reads the changed lines and proposes a test target:

```yaml
- file: packages/foo/bar.py
  line_range: 42-67
  reason: "branch coverage on the error path"
  suggested_test: tests/python/unit/test_bar.py::test_error_path_when_x
```

Claude does NOT write the test — proposing is the contract. The actor commits the proposal as part of the same task.

### 6. Emit the verdict

Write `state/artifacts/coverage/<branch>/verdict.json`:

```yaml
branch: <git branch>
coverage_percent:
  python: <float>
  ios: <float>
  overall: <float>
policy_verdict: meets_policy | needs_tests | valid_exception
tests_to_add: [list]
exemption_reason: <NoTestReasonCode or null>
audited_at: <ISO 8601>
```

## Failure modes

- **coverage_tool_unavailable** — `coverage` or `xccov` not installed/configured. Halt; emit `policy_verdict: needs_tests` with `tests_to_add: []` and `reason: "coverage tooling unavailable"`. Never default to `meets_policy` on tool failure.
- **policy_unavailable** — `packages/policies/testing.py` cannot be read. Halt with same conservative default as above. Failing open is forbidden.
- **diff_empty** — no logic-bearing files changed. Emit `policy_verdict: meets_policy` with `coverage_percent: {python: 0, ios: 0, overall: 0}` and an explanatory note.
- **invalid_no_test_reason** — actor claimed a `NoTestReasonCode` that doesn't apply (e.g. `COMMENTS_ONLY` on a diff with code changes). Emit `policy_verdict: needs_tests` and surface the mismatch.
- **partial_lane_coverage** — only one lane's tooling ran (e.g. Python coverage but xccov failed). Emit `policy_verdict: needs_tests` for the missing lane unless the diff has zero files in it.

## Worked example

Deferred — populate when the first call site exists. Tracked at
`docs/plans/2026-04-27-feat-three-new-skills-pack-plan.md`.

## References

- `packages/policies/testing.py` — the policy this skill consults.
- `packages/schemas/testing.py` — `NoTestReasonCode`, `TestLane`, `TestingPolicyResult`, `ValidationFailureCode` enums.
- Sibling skill: `skills/canonical/shared/post-run-validation.md` — runs AFTER a task; checks the same testing-policy surface for completed work.
- `coverage.py`: https://coverage.readthedocs.io/
- Apple `xccov`: https://developer.apple.com/documentation/xcode/code-coverage
