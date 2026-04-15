---
status: completed
priority: p1
issue_id: "007"
tags: [code-review, data-integrity, state-dirs, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan writes JSON reports under `state/benchmarks/skill-estate/` and `state/artifacts/verification-loop/` across Phases 2, 3, and 4 but does not bind concrete rules for: (1) atomic writes, (2) `<run-id>` uniqueness, or (3) schema versioning. Without these, concurrent invocations collide, silent overwrites are possible, and a future schema change orphans old baselines.

## Findings

Data-integrity-guardian review identified three related gaps:

1. **Atomic writer binding is a hand-wave.** Plan says "atomic via temp-file + rename pattern from `registry_writer.py`" but no phase deliverable actually binds any validator to a specific function. Nothing prevents a drive-by `open(path, 'w')` landing in a follow-up.
2. **`<run-id>` collision unspecified.** Plan uses `smoke-<timestamp>` (Phase 3 smoke DoD) and `2026-04-15-ecc-gap-baseline/` (Phase 4) with no format pinned. Two concurrent invocations at second-granularity overwrite.
3. **No schema version field.** `StocktakeReport` / `ContextBudgetReport` / `VerificationLoopReport` serializations omit `schema_version`. A Phase-2-follow-up `DriftItem` shape change orphans old baselines.

All three are addressed by the same short primitive edit.

## Proposed Solutions

### Option 1: Bind all three rules in `packages/tools/primitives/_state_writer.py`

New module exposing:
- `atomic_write_json(path: Path, report: dict) -> None` — temp+rename via `registry_writer` helper
- `new_run_id() -> str` — returns `<UTC-ISO>Z-<uuid4[:8]>`
- Every report dataclass includes `schema_version: str = "1"` as its first field, asserted by a convention test

Pros:
- Single binding point
- Grep guard in `test_primitives_conventions.py` forbids raw `open(..., 'w')` under `state/benchmarks/**` and `state/artifacts/verification-loop/**`
- `new_run_id()` eliminates collisions by construction

Cons:
- Tiny new module

Effort: small
Risk: low

### Option 2: Document the rules in plan prose and trust reviewers

Update the plan with rules but skip the enforcement.

Pros:
- Zero new code

Cons:
- Drive-by raw file opens will land eventually
- No test to catch schema-version omission

Effort: trivial
Risk: high (quiet regression vector)

## Recommended Action

Option 1. Phase 2a ships the primitive; Phase 2b, 3, 4 all use it for every write. Convention test lands with Phase 2a.

## Technical Details

- New module: `packages/tools/primitives/_state_writer.py`
- Modified: `packages/tools/primitives/registry_drift.py` (use `new_run_id()`, `atomic_write_json()`)
- Modified: `packages/tools/primitives/context_budget.py` (same)
- Modified: `packages/policies/verification_loop.py` (same)
- Test: `tests/python/unit/test_state_writer_conventions.py` — grep guard + roundtrip

## Acceptance Criteria

- [ ] `packages/tools/primitives/_state_writer.py` exposes `atomic_write_json`, `new_run_id`
- [ ] All three report dataclasses have `schema_version: str = "1"` as first field
- [ ] Grep test asserts no raw `open(..., 'w')` under `state/benchmarks/**` or `state/artifacts/verification-loop/**`
- [ ] `<run-id>` format pinned to `<ISO8601-UTC>Z-<uuid4[:8]>` in every contract.yaml
- [ ] Writer raises if target dir exists (`os.makedirs(..., exist_ok=False)`) for run-id paths
- [ ] Unit test writes two concurrent reports with the same base timestamp and asserts both land without collision
- [ ] Plan document updated: Phase 2a/2b/3/4 DoD lines bind to this primitive

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Data-integrity-guardian flagged three gaps that share the same fix. Bundled into one todo.
