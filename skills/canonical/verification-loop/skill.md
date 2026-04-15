---
id: verification-loop
name: Verification Loop
purpose: Pre-PR / pre-release quality gate that composes reconciliation + skill-stocktake + changed-surface missing-tests into a single aggregated report with pass | soft_fail | hard_fail verdict.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: agentic
---

# Skill: verification-loop

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

`reconcile_registry()` is structural. `skill-stocktake` finds orphan
canonical files. `context-budget` reports lane token totals.
`post-run-validation` validates a single task run. None of these is
the higher-level "is this PR ready to merge?" sweep.

This skill is that sweep. It composes (does NOT replace) the
existing validators into a single `VerificationLoopReport` with a
verdict and a full sub-check trace. Operators invoke it via trigger
phrase; CI invokes it via the policy wrapper at
`packages/policies/verification_loop.py`.

**Explicit non-goal:** `verification-loop` never writes, never
dispatches, never mutates the registry. It reads every input and
reports.

## When to invoke

- Pre-PR: operator via trigger phrases — "run the verification
  loop", "pre-PR sweep", "check if this is ready to merge", "run
  all the quality gates".
- CI / merge gate: `packages.policies.verification_loop.run_verification_loop()`
  raises `PolicyViolation(VERIFICATION_LOOP_HARD_FAIL)` on hard
  fail. CI catches and blocks merge.
- Advisory (non-Claude runtimes): `packages.tools.primitives.verification_loop_runner.run()`
  returns the typed report without raising.

## Contract

Inputs (keyword-only per the Python idiom rule in todo 015):

- `since_ref: str = "main"` — git ref the changed-surface check
  diffs against.
- `lookback_task_runs: int = 20` — reserved for the deferred
  task-run audit sub-check.
- `known_drift: tuple[str, ...]` — substrings tagged as pre-existing
  known drift; the aggregator tolerates them.

Outputs: `VerificationLoopReport` with
- `verdict`: `"pass" | "soft_fail" | "hard_fail"`.
- `sub_checks`: list of `{name, severity, summary, detail}`.
- `infra_errors`: list of sub-check names that crashed (severity
  `error` — mapped to `soft_fail`, never `hard_fail`).
- `since_ref`, `lookback_task_runs`, `schema_version`.

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

Deferred sub-checks (not in MVP; add back when input is stable):

- `context_budget` composition — needs thresholds.
- Recent-task-run `post-run-validation` audit — needs evidence the
  check would have caught a known failure.
- `dispatch-health` read — depends on an unshipped Hermes
  cross-cutting stream.

When a deferred sub-check is not composed at runtime, the aggregator
records its slot as `severity: skipped` in the report. `skipped`
never affects the verdict.

## Severity enum (5-state per todos 009 + 010)

| Severity | Meaning                                              | Verdict effect      |
| -------- | ---------------------------------------------------- | ------------------- |
| `info`   | Clean sub-check; informational only.                 | none                |
| `warn`   | Drift / budget notice; operator should review.        | contributes to `soft_fail` |
| `fail`   | Real drift / missing tests; merge blocker.            | contributes to `hard_fail` |
| `error`  | Sub-check crashed (platform bug).                    | contributes to `soft_fail` (never `hard_fail`) |
| `skipped`| Input absent or deferred sub-check.                   | none                |

The `fail` vs `error` split is critical. A platform bug that makes
a sub-check crash should NOT block merges — it blocks the team and
should route to a bug fix on the skill, not a red X on a PR.

## Caller → entry-point mapping (per todo 013)

| Caller                                  | Entry point                                              |
| ---------------------------------------- | -------------------------------------------------------- |
| CI (pre-merge)                           | `packages/policies/verification_loop.py`                 |
| Operator via trigger phrase              | Skill adapter (which invokes the runner primitive)       |
| `packages/policies/release_readiness.py` | `packages/policies/verification_loop.py`                 |
| Codex / ACP peer                         | `packages/tools/primitives/verification_loop_runner.py`  |
| Hermes `worker-skill-evolution`          | `packages/tools/primitives/verification_loop_runner.py`  |

**Rule:** if you catch `PolicyViolation` from the policy wrapper,
you are in the wrong module. Use the runner primitive instead.

## Boundaries and failure modes

- **Read-only.** Reads git, reads the registry, reads CLAUDE.md,
  reads the filesystem. Writes nothing.
- **Redaction.** Task-run records (deferred sub-check) would carry
  error tracebacks and payloads. The aggregator redacts fields
  matching `/secret|token|password|key/i` plus `task.payload` and
  `error.traceback` before reporting. Test fixture
  `boundary_redaction.yaml` asserts no `sk-fake` substring leaks.
- **God-object trigger.** If `verification-loop` acquires a 4th
  sub-check OR any conditional branching beyond the verdict
  aggregator, split into `verification-loop-structural` and
  `verification-loop-runtime`. Hard limits: canonical body ≤ 300
  md lines, policy wrapper ≤ 400 py lines.
- **Parallelism deferred (todo 019).** Sub-checks run sequentially.
  Phase 3 smoke captures per-sub-check wallclock so a future
  parallelism decision is data-driven.
- **Performance.** < 3 s on the live repo.

## References

- Plan: `docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md` Phase 3.
- Runner primitive: `packages/tools/primitives/verification_loop_runner.py`.
- Policy wrapper: `packages/policies/verification_loop.py`.
- Template (NOT release_readiness.py): `packages/policies/skill_evolution.py`.
- Composed: `reconcile_registry()`, `registry_drift.check_drift()`,
  `_changed_surface_check()` (git diff cross-reference against testing.py).
