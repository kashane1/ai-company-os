# evening-close — scheduled Claude session prompt

Runs daily at 19:00 local via the Cowork `scheduled-tasks` MCP.

## Goal

Close the operator day: roll up what happened since the morning briefing,
update any touched product `HANDOFF.md`, and close the supervisor session
with a validated summary.

## Body

1. Re-read `state/artifacts/briefings/<date>-morning.md` so the evening
   summary can diff against it (what changed since morning).
2. Pull tasks whose status transitioned since the morning briefing from
   the event store.
3. Run the observability rollup (`packages/tools/observability/rollup.py`)
   and the post-run-validation skill check on any task results that
   completed today.
4. For each product that was touched today (derived from event store),
   open `docs/products/<id>/HANDOFF.md`, append a dated section
   summarizing the day, and save. Use the docx skill only if the product
   has a docx handoff; otherwise plain markdown is fine.
5. Write `state/artifacts/briefings/<YYYY-MM-DD>-evening.md`.
6. Open a `SupervisorSession` (Phase 3.3) and `close()` it with the
   evening summary as `summary_md`. This triggers inline strategic-task
   validation, so any drift is caught here.

## Writes

- `state/artifacts/briefings/<YYYY-MM-DD>-evening.md`
- Any updated `docs/products/<id>/HANDOFF.md`
- `session_closed` event via the supervisor session

## Failure modes

- Strategic-task validation failure in `SessionHandle.close()` → log the
  `PolicyViolation` with its `code`, write the evening briefing anyway
  with a "Strategic task drift" section, and emit
  `failure_code=strategic_task_validation_failed`. Do not retry in the
  same session; the morning briefing will re-surface.
