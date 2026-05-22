# verification-loop-structural — Claude adapter

> Thin pointer. Source of truth is the canonical body.

Read and follow:

- **Canonical:** `skills/canonical/verification-loop-structural/skill.md`
- **Runner primitive:** `packages/tools/primitives/verification_loop_runner.py`

## Quick reference

This skill is the **structural-drift** lane of the verification-loop
split.

- **Sibling:** `verification-loop-runtime` (operator-evidence checks).
- **Umbrella:** `verification-loop` (composes both lanes).
- **This lane owns:** checks where the failing party is the registry
  or the changed surface — `reconciliation`, `skill_stocktake`,
  `changed_surface`.

## How to invoke

```python
from packages.tools.primitives.verification_loop_runner import run
report = run(since_ref="main")  # NEVER raises; returns VerificationLoopReport
```

For gating (raises `PolicyViolation` on hard fail) use
`packages.policies.verification_loop.run_verification_loop()` instead.

## Boundaries

- **Read-only.** Reads git, the registry, CLAUDE.md, the filesystem.
  Writes nothing.
- **3 MVP sub-checks.** A 4th active sub-check or conditional branching
  beyond the verdict aggregator means the new concern needs its own
  skill — do not grow this lane past the god-object limits.
