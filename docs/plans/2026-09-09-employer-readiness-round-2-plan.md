---
status: in-review
change_id: employer-readiness-round-2
owner: Codex
last_reviewed: 2026-09-09
---

# Employer readiness: evidence and recovery

The goal is trustworthy execution evidence and a reproducible evaluator experience.
Work begins from published main in an isolated checkout. Existing operational work
and the private audit remain separate. Changes are committed locally in reviewable
groups; publishing and release actions are outside this implementation.

## Execution order

1. Execute configured verification commands and persist their real outcomes.
2. Capture staged, unstaged, and new files without changing the index; apply testing
   policy to the selected repository's source root.
3. Require meaningful, task-bound completion evidence. Make the deterministic demo
   internally consistent with the same testing rules.
4. Bound worker infrastructure failures, support explicit approval continuation,
   and make launchd own the foreground supervisor.
5. Correct active operational documentation after behavior is settled.
6. Improve LifeClock text contrast and add focused After Plans and Catchbook UI
   coverage using synthetic state.

## Implementation boundaries

Use existing schemas, stores, transactions, supervisor behavior, and product test
targets. Commands come from the operator-controlled repository registry, never an
agent's result prose. Preserve failed evidence and approval history. Avoid adding
services or generic infrastructure solely for this work.

## Validation

First reproduce each behavioral defect with a failing regression test. Use real
temporary Git repositories and subprocesses for change capture and verification;
use isolated database/queue state for lifecycle tests. Run focused tests for each
commit, then the full Python suite, quality checks, evaluator demos, and affected
iOS suites. Record unverified external behavior explicitly. The private audit IDs
and completion ledger remain local-only.

## Local verification and review handoff

The implementation is committed on `codex/employer-readiness-round-2`, based on
published main `bf7e753`. It is ready for review; no push, deployment, live
LaunchAgent installation, or external release action was performed.

The final local runs used Python 3.12.3, Xcode 26.6, XcodeGen 2.45.4, and isolated
iOS 26.5 simulators. Each product used the shared `scripts/test_ios.sh` command.

| Suite | Result | Coverage |
|---|---|---|
| Python, excluding the separate performance gate | 2,048 passed; two upstream deprecation warnings | 85.82%, above the configured 85% floor |
| After Plans | 88 passed, 3 opt-in Supabase cases skipped | 51.56% app line coverage |
| Catchbook | 333 passed, no failures or skips | 40.47% app line coverage |
| LifeClock | 452 passed, 3 documented StoreKit cases skipped | 68.30% app line coverage |

The dispatch performance gate also passed; its optional PostgreSQL case was
skipped. Configured Ruff, documentation paths, plan indexing, asset budgets,
the evaluator walkthrough, and the real synthetic worker recovery demo passed.
The zero-dependency evaluator also ran on Python 3.10.

The product tests exercise real app state with synthetic service inputs.
Catchbook's denied location and unavailable camera are injected at DEBUG app
boundaries; photo-load errors use the production loader's unit-test seam.
Neither proves OS permission-dialog behavior. LifeClock's refreshed captures
and bounded contrast measurements have a separate capture manifest.

Approval continuation currently supports the database queue and rejects Redis
before changing task state. Verification subprocesses use a restricted
environment, not an OS sandbox. These checks do not establish live Apple,
Supabase, physical-device, spoken VoiceOver, or unattended production behavior.
