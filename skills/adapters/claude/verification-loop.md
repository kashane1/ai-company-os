---
description: Pre-PR / pre-release quality-gate umbrella over the structural and runtime verification lanes. Invoke for "run the verification loop", "pre-PR sweep", "check if this is ready to merge", "run all the quality gates".
canonical_source: skills/canonical/verification-loop/skill.md
---

# Verification Loop (Claude adapter)

You are running the `verification-loop` skill from
`skills/canonical/verification-loop/skill.md`. Follow the canonical
definition.

## Quick reference

`verification-loop` is the **umbrella** over two lanes:

- **Structural** — `verification-loop-structural` (4 sub-checks:
  `reconciliation`, `skill_stocktake`, `changed_surface`, `stale_doc`).
  See `skills/adapters/claude/verification-loop-structural.md`.
- **Runtime** — `verification-loop-runtime` (`stale_postmortems`).

Aggregator: any `fail` → `hard_fail`; else any `warn` or `error` →
`soft_fail`; else `pass`. `skipped` sub-checks are metadata only.

## Two entry points — pick carefully

**Advisory mode (no raise):**

```python
from packages.tools.primitives.verification_loop_runner import run
report = run(since_ref="main")
# report.verdict is "pass" | "soft_fail" | "hard_fail"
```

**Gating mode (raises on hard_fail):**

```python
from packages.policies.verification_loop import run_verification_loop
try:
    report = run_verification_loop(since_ref="main")
except PolicyViolation as exc:
    # exc.code == "verification_loop_hard_fail"
    ...
```

**If you catch `PolicyViolation` from `packages/policies/verification_loop.py`,
you are in the wrong module.** Use the runner primitive instead.

## What this skill does NOT do

- Does NOT replace `post-run-validation`.
- Does NOT replace `reconcile_registry()` — it calls it.
- Does NOT write. Not the registry, not source, not state (except
  when the operator explicitly writes the report to
  `state/artifacts/verification-loop/<run-id>/report.json` via
  `_state_writer.atomic_write_json`).

## Edit boundaries

Read-only. Every file read goes through `safe_join` where
applicable. Subprocess invocations are limited to `git diff
--name-only` with a 10s timeout.
