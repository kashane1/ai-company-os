# test-coverage-audit — Claude adapter

> Thin pointer. Source of truth: `skills/canonical/shared/test-coverage-audit.md`.
>
> **Status: deferred.** Registered ahead of coverage tooling activation.

## When to invoke

Trigger phrase (per `CLAUDE.md`): "audit test coverage" / "do my changes meet the coverage bar".

Use when an operator is about to commit and wants pre-merge verification that the change meets `packages/policies/testing.py` thresholds.

## Claude's slice

Claude does NOT run coverage tooling. The Codex adapter owns that path.

Claude:
1. Reads the coverage report at `state/artifacts/coverage/<branch>/<lane>.json` (Codex emitted it).
2. Reads the worktree diff to identify changed lines.
3. For each below-threshold file, **proposes** a test target with `file:line_range:reason:suggested_test`.
4. Surfaces exemptions when the diff matches a `NoTestReasonCode` (e.g. `COMMENTS_ONLY`, `CONFIG_NO_BEHAVIOR_CHANGE`).
5. Emits the `TestCoverageVerdict` shape to `state/artifacts/coverage/<branch>/verdict.json`.

## Boundaries

- **Read-only against `packages/policies/testing.py`.** Never propose policy changes from this skill.
- **Read-only against `tests/`.** This skill never writes tests — only proposes.
- **Never default to `meets_policy` on error.** Tooling failure → `needs_tests` with the failure surfaced.

## Failure surfacing

Map each failure mode (per the canonical body) to a concrete next-step:

| Failure | Next step |
|---|---|
| `coverage_tool_unavailable` | "Configure `coverage` for Python (`pip install coverage`) or wire `xccov` into the iOS scheme before retrying." |
| `policy_unavailable` | "Coverage policy file missing — restore `packages/policies/testing.py` or check git state." |
| `invalid_no_test_reason` | "The claimed `<code>` doesn't fit this diff. See `packages/schemas/testing.py:NoTestReasonCode` for valid codes." |
| `partial_lane_coverage` | "Only `<lane>` coverage ran. Configure the other lane's tooling and re-run." |
