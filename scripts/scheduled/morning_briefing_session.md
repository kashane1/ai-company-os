# morning-briefing — scheduled Claude session prompt

Runs every weekday at 07:30 local time via the Cowork `scheduled-tasks` MCP.
Produces the single daily surface that rolls up everything the platform did
(and blocked on) while Kashane was asleep.

## Goal

One file on disk (`state/artifacts/briefings/<date>-morning.md`) plus one
Gmail **draft** (never sent) containing the same content, so Kashane can
review it in either place. The briefing is the founder-visible proof that
Phases 1–3 are doing their job.

## Pre-flight (once per session)

1. Read the runtime-supervisor status file at
   `state/checkpoints/platform/runtime-supervisor-status.json`. Any lane
   reporting `blocked` goes to the top of the briefing with the recovery
   action.
2. Read `state/checkpoints/platform/security-state.json`. If
   `mcp-threat-model.md:checksum` drifted, surface it at the top.
3. Check `state/flags/gtm_frozen`. If present, surface it at the top.
4. Run the preflights idempotently by reading their last log lines from
   `state/logs/runtime-supervisor/preflight.log`. Do **not** execute them
   from inside the briefing — that is the runtime-supervisor's job.

## Body

The briefing is structured in six sections, in this fixed order:

1. **Blocked lanes & P0 drift** — runtime-supervisor status + threat-model
   checksum + GTM freeze + preflight state.
2. **Pending approvals** — every `approval_requested` event without a
   matching `approval_decided`, grouped by action. For each, show
   subject_id, action, time waiting, and the magic-link TTL state (from
   the `ApprovalTokenStore` Phase 3.1 index).
3. **GTM day-ahead** — today's scheduled posts, engagement rollup from
   yesterday, and any `SOCIAL_POST_SCHEDULE` tasks that hit a cooldown.
4. **Engineering & iOS status** — open tasks per lane, last failure codes
   from each lane's log, and any regression captures filed overnight by
   the `failure-mode-regression` skill (Phase 4.6).
5. **Artifact chain health** — run the product-artifact-chain validator
   (Phase 5.1) and the GTM chain validator (Phase 2.3). Surface any
   broken links or missing files.
6. **Observability rollup** — output of
   `packages/tools/observability/rollup.py` (Phase 4.3), redacted.

## Writes

1. `state/artifacts/briefings/<YYYY-MM-DD>-morning.md` — full body.
2. Gmail draft with subject `Morning briefing <YYYY-MM-DD>` and the same
   body. **Draft only**, no send.
3. Control-plane event `morning_briefing_written` with a pointer to the
   file.

## Failure modes

- Runtime-supervisor status file missing → briefing still runs, surfaces
  `failure_code=runtime_supervisor_status_missing` at the top.
- Gmail MCP unavailable → write the file anyway, emit
  `failure_code=gmail_draft_unavailable`, the founder reads the file.
- Observability rollup errors → include the exception message in the
  briefing under "Observability rollup (errored)" and keep going.
