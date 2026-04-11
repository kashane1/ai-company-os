# Phase 6 — Deferred

**Status:** Deferred as planned. Not blocking Phases 0–5 from going live.
**Decided:** 2026-04-10
**Owner:** platform

## Scope

Phase 6 of `claude-orchestrator-readiness-plan.md` covers swapping the
file-backed stores for production-grade backends:

- `packages/db/postgres_backend.py` — Postgres-backed implementations of
  `TaskStore`, `ApprovalStore`, `EventStore`, `GoalStore`,
  `ReleaseStore`, and the new `ApprovalTokenStore`.
- `packages/queue/redis_backend.py` — a Redis-backed `TaskQueue` with
  the same `enqueue / claim_next / acknowledge` surface the file queue
  exposes today.
- A feature flag in `packages/config/settings.py` to select the
  backend per store.

## Why it's deferred

The readiness plan explicitly gates Phase 6 on "Phases 0–5 running
stable for one week on the always-on Mac without manual intervention."
As of this decision, Phases 0–5 have just landed. We need:

1. One full week of green morning briefings, evening closes, and the
   Friday weekly digest.
2. No `capture_pipeline_self_failure` entries in the failure-mode
   fixture index.
3. Approval token flow (including P0 second-factor) exercised at least
   once in anger on a real submission.

Only after those three pass do we open the Phase 6 ticket.

## What is NOT blocked by this

- All orchestration work (Phase 3.3 `SupervisorSession`)
- Strategic task types (Phase 5.2)
- Observability rollup + redaction (Phase 4.3)
- Approval-token HMAC flow (Phase 3.2)
- Post-run and failure-mode skills (Phase 4.5 / 4.6)

These all run on the current file-backed stores with no code changes
required when Phase 6 lands; the backend swap is strictly additive.

## Re-open criteria

When the three gating conditions are met, create a new decision doc
at `docs/decisions/phase-6-activation.md` and start the Postgres +
Redis branch.
