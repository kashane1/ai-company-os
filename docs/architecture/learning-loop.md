# Harness Learning Loop

Status: shipped 2026-04-27 (Phases 1+4 → 2 → 3 → 5).

The harness now closes the loop from observed failures back into future
worker behavior. Three durable artifacts cooperate:

```
worker rejection ──► failure-mode-regression ──► PostMortem stub
                              │                         │
                              ▼                         ▼
                  state/artifacts/failure-fixtures   state/postmortems/
                                                        │
                                ┌───────────────────────┤
                                │                       │
                                ▼                       ▼
                  worker_signals.load_recent_signals    verification-loop-runtime
                                │                       │
                                ▼                       ▼
                       TaskPacket.constraints      stale_postmortems sub-check
```

## Components

| File | Role |
|------|------|
| `packages/schemas/postmortem.py` | Frozen-dataclass schema. `__post_init__` redacts every string field uniformly. |
| `packages/db/postmortem_store.py` | Per-record JSON store. `update_status` writes append-only audit log. |
| `packages/policies/postmortem_retention.py` | Pure functions for staleness / visibility / severity-by-age. |
| `skills/canonical/failure-mode-regression/validator.py` | Emits a stub PostMortem after every fixture capture, dedup'd via O_EXCL lockfile. |
| `packages/tools/learning/worker_signals.py` | Allowlist-only constraint generator. Reads task_runs + open postmortems; injects strings drawn solely from a static map. |
| `packages/tools/primitives/verification_loop_runtime_runner.py` | New runtime-evidence runner. Currently owns the `stale_postmortems` sub-check. |
| `apps/worker-supervisor/main.py` | Calls `augment_packet_constraints` before constructing TaskPackets. |

## Security model (do not weaken without re-review)

1. **No free-text passthrough into prompts.** `worker_signals` constraints
   come **only** from `_FAILURE_CODE_TO_CONSTRAINT` and
   `_ROOT_CAUSE_CONSTRAINTS`. `validation_checks[*].details` text is
   never echoed. Adding to either map is treated as policy code.
2. **Audit log on every status change.** `PostMortemStore.update_status`
   writes to `state/logs/postmortems/audit.jsonl` (append-only,
   `O_APPEND` + `fsync`). The verification-loop-runtime sub-check
   cross-checks RESOLVED records against the audit log; missing entries
   surface as `warn`.
3. **Path leakage.** `PostMortem.__post_init__` strips `/Users/<name>/`,
   `/home/<name>/`, and `/var/folders/` prefixes from every string field
   that may carry a path.
4. **Dedup is filesystem-atomic.** `O_CREAT|O_EXCL` on
   `state/postmortems/.dedup/<failure_code>.lock` with 24h-mtime TTL.
   No read-modify-write on `index.json`.

## Kill-switches (operator tools, NOT security boundaries)

| Env var | Effect |
|---------|--------|
| `AI_COMPANY_OS_DISABLE_SIGNAL_INJECTION=1` | `load_recent_signals` returns `{}`. Supervisor packets get base constraints only. |
| `AI_COMPANY_OS_DISABLE_POSTMORTEM_EMIT=1` | `failure-mode-regression` writes the fixture but skips the postmortem stub. |

A same-uid attacker can flip either of these. They exist for operator
convenience (kill the loop fast if it misbehaves), not as a defense.

## Recurrence threshold

Per Reflexion / Devin / Replit production patterns: a single failure
does not promote into a constraint. `worker_signals.SignalQuery` defaults
`min_recurrence_count = 3` — the same `(lane, failure_code)` pair must
appear at least 3 times within the lookback window before its
constraint string is injected.

Postmortem-derived constraints (one per `root_cause_category` per lane)
do not require recurrence — a single OPEN categorized postmortem is
already a deliberate operator signal.

## Cap and FIFO

`max_per_lane = 5` is a hard cap (Cursor `.cursorrules` lesson: rules
files rot when uncapped). Selection is rank-by-frequency for task-run
failures; postmortem-derived strings append after, capped at the same
total.

## Connection to future ratchet (Recommendation #3 in audit)

The next harness plan will add a ratchet mechanism: a recurrence
threshold higher than 3 (e.g. 5+ in 7 days) escalates via approval token
instead of injecting a soft constraint. The plumbing here — typed
PostMortem records, audit-logged status changes, lane-keyed signal
emission — is the foundation that ratchet builds on.

The existing `failure-mode-regression` regression-fixture mechanism is
already a regression set in the SRE sense: every captured fixture is a
replayable test case. The ratchet will enforce: "no shipping until all
prior regression fixtures still pass." That's the strongest form of
ratchet, and it sits naturally on top of what shipped here.
