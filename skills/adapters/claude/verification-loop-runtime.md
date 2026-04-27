# verification-loop-runtime — Claude adapter

> Thin pointer. Source of truth is the canonical body.

Read and follow:

- **Canonical:** `skills/canonical/verification-loop-runtime/skill.md`
- **Runner primitive:** `packages/tools/primitives/verification_loop_runtime_runner.py`

## Quick reference

This skill is the **runtime-evidence** half of the verification-loop split.

- **Sibling:** `verification-loop` (structural drift checks).
- **This lane owns:** checks where the failing party is the human
  operator, not the registry. Today: `stale_postmortems`. Future:
  worker-signal anomalies, ratchet breaches.

## When Claude should invoke

Trigger phrases (per `CLAUDE.md`):

- "check stale postmortems"
- "audit operator hygiene"
- "run the runtime verification loop"

Or whenever a pre-PR sweep needs operator-evidence checks (the meta
`verification-loop` skill composes both lanes).

## How to invoke

```python
from packages.tools.primitives.verification_loop_runtime_runner import run
report = run()  # NEVER raises; returns VerificationLoopRuntimeReport
```

Do not catch exceptions — the runner already wraps every sub-check.
Inspect `report.verdict` (`pass | soft_fail | hard_fail`) and the
per-sub-check `severity` and `summary`.

## Boundaries

- **Read-only.** Reads `state/postmortems/` and the audit log. Writes nothing.
- **Soft fail only.** No sub-check in this lane raises `hard_fail`. Stale postmortems are operator hygiene, not merge blockers.
- **No retries.** Sub-check crashes are reported as `severity: error`, contributing to `soft_fail`. Fix the platform bug; do not retry.
