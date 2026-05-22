---
id: verification-loop-structural
name: Verification Loop (Structural)
purpose: Structural-drift half of the verification-loop split. Composes reconciliation + skill-stocktake + changed-surface missing-tests into a pass | soft_fail | hard_fail verdict.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: agentic
---

# Skill: verification-loop-structural

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

`verification-loop-structural` answers one question: *"Is the registry
honest about what exists, and does the changed surface carry its
tests?"* — static / structural drift.

It is one of the two lanes under the `verification-loop` umbrella. The
sibling lane, `verification-loop-runtime`, answers a different
question — *"Is the system behaving as we intended over time?"* — and
the failing party there is the operator, not the registry.

This skill composes (does NOT replace) the existing structural
validators into a `VerificationLoopReport` with a verdict and a full
sub-check trace.

**Explicit non-goal:** structural verification never writes, never
dispatches, never mutates the registry. It reads every input and
reports.

## When to invoke

- Via the `verification-loop` umbrella skill, which composes this lane
  with `verification-loop-runtime`.
- CI / merge gate: `packages.policies.verification_loop.run_verification_loop()`
  raises `PolicyViolation(VERIFICATION_LOOP_HARD_FAIL)` on hard fail.
- Advisory (non-Claude runtimes): `packages.tools.primitives.verification_loop_runner.run()`
  returns the typed report without raising.

## Contract

Inputs (keyword-only per the Python idiom rule in todo 015):

- `since_ref: str = "main"` — git ref the changed-surface check diffs against.
- `lookback_task_runs: int = 20` — reserved for the deferred task-run audit.
- `known_drift: tuple[str, ...]` — substrings tagged as pre-existing
  known drift; the aggregator tolerates them.

Outputs: `VerificationLoopReport` with `verdict`, `sub_checks`,
`infra_errors`, `since_ref`, `lookback_task_runs`, `schema_version`.

## Sub-checks (MVP — 3, not 6)

1. **`reconciliation`** — `reconcile_registry()`. Drift →
   `severity: fail` (real missing-fixture drift is always
   hard-failing; this is the `reconcile_registry` hard gate).
2. **`skill_stocktake`** — `registry_drift.check_drift()`. Drift →
   `severity: warn` (soft — drift is a signal, not a merge blocker
   by default). Known drift is tolerated.
3. **`changed_surface`** — `git diff --name-only <ref>...HEAD`
   cross-referenced against lane rules. Logic file changed without
   a matching test file changed → `severity: fail`.

## Severity & verdict aggregation

Same 5-state enum as the `verification-loop` umbrella:

| Severity | Meaning                                              | Verdict effect      |
| -------- | ---------------------------------------------------- | ------------------- |
| `info`   | Clean sub-check; informational only.                 | none                |
| `warn`   | Drift / budget notice; operator should review.        | contributes to `soft_fail` |
| `fail`   | Real drift / missing tests; merge blocker.            | contributes to `hard_fail` |
| `error`  | Sub-check crashed (platform bug).                    | contributes to `soft_fail` (never `hard_fail`) |
| `skipped`| Input absent or deferred sub-check.                   | none                |

The aggregator raises `VERIFICATION_LOOP_HARD_FAIL` (via the policy
wrapper only) when any sub-check has `severity: fail`.

## Boundaries

- **Read-only.** Reads git, the registry, CLAUDE.md, the filesystem.
  Writes nothing.
- **No raising.** `verification_loop_runner.run()` returns a typed
  report; sub-check crashes become `severity: error`.
- **Lane scope.** This lane owns checks where the failing party is the
  registry or the changed surface — not the operator. Operator-hygiene
  checks belong in `verification-loop-runtime`.
- **God-object trigger.** A 4th active sub-check OR conditional
  branching beyond the verdict aggregator means this lane is doing too
  much — split the new concern into its own skill rather than growing
  this one. Hard limits: canonical body ≤ 300 md lines, policy wrapper
  ≤ 400 py lines.

## References

- Umbrella: `skills/canonical/verification-loop/skill.md`.
- Sibling lane: `skills/canonical/verification-loop-runtime/skill.md`.
- Runner primitive: `packages/tools/primitives/verification_loop_runner.py`.
- Policy wrapper: `packages/policies/verification_loop.py`.
- Composed: `reconcile_registry()`, `registry_drift.check_drift()`,
  `_changed_surface_check()` (git diff cross-reference against testing.py).
