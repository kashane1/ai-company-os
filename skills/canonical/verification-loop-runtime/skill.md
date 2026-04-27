---
id: verification-loop-runtime
name: Verification Loop (Runtime)
purpose: Runtime-evidence half of the verification-loop split. Detects stale OPEN postmortems and RESOLVED postmortems lacking audit-log entries.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: agentic
---

# Skill: verification-loop-runtime

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

`verification-loop` (the original) answers: *"Is the registry honest about
what exists?"* — structural drift checks. This skill answers a different
question: *"Is the system behaving as we intended over time?"* — runtime
evidence.

The failing party for a runtime check is usually the **operator** (the
founder hasn't reviewed an open postmortem; an audit-log entry is
missing) — not the registry. Different verdict semantics. That's why the
two lanes are split per the god-object trigger documented at
`verification-loop/skill.md:122-127`.

This lane is also load-bearing for the **H1 security mitigation** of the
PostMortem store: the `stale_postmortems` sub-check cross-checks
`RESOLVED` records against `state/logs/postmortems/audit.jsonl`. A
same-uid attacker who calls `PostMortemStore.update_status` directly
bypasses the audit log; this sub-check catches that.

## When to invoke

- Pre-PR via the meta `verification-loop` skill (composes structural + runtime).
- Standalone via the runner primitive at
  `packages/tools/primitives/verification_loop_runtime_runner.py:run()`.

## Sub-checks (MVP — 1, room for future)

1. **`stale_postmortems`**
   - Scans `state/postmortems/` for OPEN records older than 14 days.
   - Cross-checks RESOLVED records against the audit log.
   - Severity: `info` if both sets are empty; otherwise `warn`.
   - Verdict effect: contributes to `soft_fail`, never `hard_fail`. Stale
     postmortems are operator hygiene; they should not block a merge.

Future runtime sub-checks (deferred to follow-up plans):

- Worker-signal anomaly detection (recurrence spikes).
- Ratchet breach detection (Recommendation #3 in the audit).

## Severity & verdict aggregation

Same 5-state enum as `verification-loop`:

| Severity | Verdict effect              |
| -------- | --------------------------- |
| `info`   | none                        |
| `warn`   | contributes to `soft_fail`  |
| `fail`   | contributes to `hard_fail`  |
| `error`  | contributes to `soft_fail`  |
| `skipped`| none                        |

## Boundaries

- **Read-only.** Reads `state/postmortems/` and the audit log. Writes nothing.
- **No raising.** `run()` returns a typed report; sub-check crashes become `severity: error`.
- **Lane scope.** This lane owns checks where the failing party is the
  human operator, not the registry. New runtime sub-checks must satisfy
  that test before being added here.

## References

- Plan: `docs/plans/2026-04-27-feat-postmortem-schema-and-adaptive-feedback-loop-plan.md`.
- Runner primitive: `packages/tools/primitives/verification_loop_runtime_runner.py`.
- Sibling: `skills/canonical/verification-loop/skill.md` (structural).
- PostMortem store: `packages/db/postmortem_store.py`.
- Audit log: `state/logs/postmortems/audit.jsonl` (append-only).
