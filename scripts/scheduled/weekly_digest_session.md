# weekly-digest — scheduled Claude session prompt

Runs Fridays at 17:00 local via the Cowork `scheduled-tasks` MCP.

## Goal

Produce a single weekly rollup that aggregates the week's operator rhythm
into one founder-readable document.

## Body

1. Aggregate tasks by status across lanes (engineering, iOS, appstore,
   gtm) over the past 7 days from the task store.
2. Aggregate approvals by final state (approved, rejected, still pending,
   token expired).
3. Aggregate GTM engagement: posts published, engagement delta vs. the
   prior week, any `social-post-safety` rejections and why.
4. Capture blockers carried into next week from the runtime-supervisor
   status file and the last five morning briefings.
5. Summarize any `failure-mode-regression` fixtures captured during the
   week, grouped by `failure_code`.
6. Summarize skill pack health: the row set from
   `skills/registry.yaml` plus any skills whose `fixture_status` flipped
   during the week.

## Writes

- `state/artifacts/briefings/<YYYY-MM-DD>-weekly.md`
- `weekly_digest_written` event
- Gmail draft (not sent) with the same body

## Failure modes

- Any upstream aggregation errors → include them in the digest under a
  "Collection errors" section, keep going.
