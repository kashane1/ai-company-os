---
status: open
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
