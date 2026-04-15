---
status: completed
priority: p3
issue_id: "019"
tags: [code-review, performance, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan's `verification-loop` runs three sub-checks (reconciliation + stocktake + changed-surface) sequentially. All three are pure filesystem reads with no shared mutable state — embarrassingly parallel. Running them concurrently would meaningfully shrink the `<3 s` NFR budget and keep headroom for when more sub-checks land. Not blocking because the current sequential path is within budget, but worth tracking.

## Findings

Architecture strategist second-pass finding #4:
> "Sub-check parallelism is entirely absent from Phase 3. The plan says 'run all sub-checks on every invocation, no fail-fast' and budgets `< 3 s` but sequentializes reconciliation + stocktake + changed-surface. A 200-changed-file `git diff` walk alone can consume most of the budget; running it concurrently with stocktake's registry walk is a trivial win. Use `concurrent.futures.ThreadPoolExecutor(max_workers=3)` for independent sub-checks, with a deterministic result-ordering step before verdict aggregation so fixture outputs stay stable."

## Proposed Solutions

### Option 1: `ThreadPoolExecutor(max_workers=3)` with deterministic result ordering

`packages/policies/verification_loop.py` runs independent sub-checks in a thread pool, collects results, then aggregates in a fixed order before producing the verdict. tiktoken thread-safety TODO does NOT block this because context-budget is not in the MVP sub-check set.

```python
from concurrent.futures import ThreadPoolExecutor
sub_checks = [_run_reconciliation, _run_stocktake, _run_changed_surface]
with ThreadPoolExecutor(max_workers=len(sub_checks)) as pool:
    results = list(pool.map(lambda f: f(payload), sub_checks))
# Fixed ordering by index preserves determinism
```

Pros:
- Trivial code addition
- Wins budget headroom for future sub-checks
- Deterministic because `pool.map` preserves order

Cons:
- Introduces threading semantics into a skill that was single-threaded
- Must be tested with a deliberately-slow sub-check to prove parallelism kicks in

Effort: small
Risk: low

### Option 2: Defer until Phase 3 smoke shows budget pressure

Ship sequential first. Add parallelism when measurements show a sub-check is the bottleneck.

Pros:
- YAGNI-compliant
- Simpler first version

Cons:
- The moment context-budget joins the MVP set (once thresholds exist), the budget will likely pressure — at which point we re-do this

Effort: trivial
Risk: low

## Recommended Action

Option 2 for the first Phase 3 landing. Revisit when either (a) budget pressure is observed or (b) context-budget sub-check joins the verification-loop. At that point, apply Option 1.

## Acceptance Criteria

- [ ] Decision documented: sequential for first landing, parallelism when budget pressure observed
- [ ] Phase 3 smoke run records per-sub-check wallclock so future parallelism decision is data-driven
- [ ] Follow-up issue filed to reconsider after context-budget composition lands

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
