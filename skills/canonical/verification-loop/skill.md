---
id: verification-loop
name: Verification Loop
purpose: Pre-PR / pre-release quality-gate umbrella. Composes the structural and runtime verification lanes into a single pass | soft_fail | hard_fail verdict.
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

The higher-level "is this PR ready to merge?" sweep. `verification-loop`
is the **umbrella** over two verification lanes — it composes (does NOT
replace) them into one `VerificationLoopReport` with a verdict and a
full sub-check trace.

**Explicit non-goal:** `verification-loop` never writes, never
dispatches, never mutates the registry. It reads every input and reports.

## When to invoke

- Pre-PR: operator trigger phrases — "run the verification loop",
  "pre-PR sweep", "check if this is ready to merge", "run all the
  quality gates".
- CI / merge gate: `packages.policies.verification_loop.run_verification_loop()`
  raises `PolicyViolation(VERIFICATION_LOOP_HARD_FAIL)` on hard fail.
- Advisory: `packages.tools.primitives.verification_loop_runner.run()`
  returns the typed structural report without raising.

## Contract

Inputs (keyword-only, todo 015): `since_ref: str = "main"`,
`lookback_task_runs: int = 20`, `known_drift: tuple[str, ...]`.

Outputs: `VerificationLoopReport` with `verdict`
(`pass | soft_fail | hard_fail`), `sub_checks`
(`{name, severity, summary, detail}`), `infra_errors`, `since_ref`,
`lookback_task_runs`, `schema_version`.

## Verification lanes

Two lanes, each its own canonical skill with its own runner primitive.
This umbrella owns only the shared severity vocabulary and the verdict
aggregation that combines them.

**Structural — `verification-loop-structural`** (runner:
`verification_loop_runner.py`). *"Is the registry honest about what
exists?"* — 4 sub-checks: `reconciliation`, `skill_stocktake`,
`changed_surface`, `stale_doc`. The `stale_doc` sub-check wraps
`scripts/ci/check_doc_paths.sh` — the mechanical doc-path-existence
portion of the `stale-doc-detector` skill. Per-sub-check severity
rules live in that skill.

**Runtime — `verification-loop-runtime`** (runner:
`verification_loop_runtime_runner.py`). *"Is the system behaving as
intended over time?"* — the failing party is the operator, not the
registry. MVP sub-check: `stale_postmortems`.

## Deferred sub-checks

Not in any lane yet; add back when input is stable:

- `context_budget` composition — needs thresholds.
- Recent-task-run `post-run-validation` audit — needs evidence it
  would have caught a known failure.
- `dispatch-health` read — depends on an unshipped Hermes stream.

A deferred sub-check not composed at runtime is recorded as
`severity: skipped`. `skipped` never affects the verdict. The
`stale-doc-detector` doc-path scan — previously deferred here — is now
active as the structural lane's `stale_doc` sub-check.

## Severity enum (5-state per todos 009 + 010)

| Severity | Meaning                                              | Verdict effect      |
| -------- | ---------------------------------------------------- | ------------------- |
| `info`   | Clean sub-check; informational only.                 | none                |
| `warn`   | Drift / budget notice; operator should review.        | contributes to `soft_fail` |
| `fail`   | Real drift / missing tests; merge blocker.            | contributes to `hard_fail` |
| `error`  | Sub-check crashed (platform bug).                    | contributes to `soft_fail` (never `hard_fail`) |
| `skipped`| Input absent or deferred sub-check.                   | none                |

The `fail` vs `error` split is critical. A platform bug that crashes a
sub-check should NOT block merges — it routes to a skill bug fix, not a
red X on a PR.

## Caller → entry-point mapping (per todo 013)

| Caller                                  | Entry point                                              |
| ---------------------------------------- | -------------------------------------------------------- |
| CI (pre-merge)                           | `packages/policies/verification_loop.py`                 |
| Operator via trigger phrase              | Skill adapter (which invokes the runner primitive)       |
| `packages/policies/release_readiness.py` | `packages/policies/verification_loop.py`                 |
| Codex / ACP peer                         | `packages/tools/primitives/verification_loop_runner.py`  |
| Hermes `worker-skill-evolution`          | `packages/tools/primitives/verification_loop_runner.py`  |

**Rule:** if you catch `PolicyViolation` from the policy wrapper, you
are in the wrong module. Use the runner primitive instead.

## Boundaries and failure modes

- **Read-only.** Reads git, the registry, CLAUDE.md, the filesystem.
  Writes nothing.
- **Redaction.** Task-run records (deferred sub-check) carry error
  tracebacks and payloads. The aggregator redacts fields matching
  `/secret|token|password|key/i` plus `task.payload` and
  `error.traceback` before reporting. Fixture `boundary_redaction.yaml`
  asserts no `sk-fake` substring leaks.
- **God-object trigger.** The structural/runtime split this guardrail
  once mandated is **done** — `verification-loop-structural` and
  `verification-loop-runtime` are separate skills. The guardrail now
  applies **per lane**: every sub-check in a lane must share that
  lane's failing party, and conditional branching beyond the verdict
  aggregator — or growth past the hard limits (canonical body ≤ 300 md
  lines, policy wrapper ≤ 400 py lines) — means a new concern needs
  its own skill rather than another sub-check bolted onto a lane.
- **Parallelism deferred (todo 019).** Sub-checks run sequentially.
- **Performance.** < 3 s on the live repo.

## References

- Plan: `docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md` Phase 3.
- Structural lane: `skills/canonical/verification-loop-structural/skill.md`.
- Runtime lane: `skills/canonical/verification-loop-runtime/skill.md`.
- Policy wrapper: `packages/policies/verification_loop.py`.
