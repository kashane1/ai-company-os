# HomeFromWorking POD direction reset

## What changed

- Adopted the founder's September 2 direction: start with owner-approved artwork
  and automate listing preparation through a reviewed Printify draft. Broader
  product research is deferred.
- Added the [current design](../plans/2026-09-02-home-from-working-pod-design.md),
  including the first milestone, repository audit, approval/identity requirements,
  and practical gaps to verify during implementation.
- Preserved the supplied handoff as reference material with a provenance header;
  the original contents are unchanged and are not treated as execution authority.
- Marked both August 31 commerce plans superseded and moved them to the plan
  archive. Added current-direction links at repository entry points.
- Changed documentation only. No marketplace/account calls, runtime changes,
  implementation, commits, or pushes occurred.

## What is open

Implement the local manifest and preflight for one Gildan 5000 design, then add a
product-approved Printify draft integration. The first milestone requires a real
verified draft; an offline demo alone does not complete it. Publication and Etsy
enrichment follow with separate revision-specific live approval.

## What is blocked

No blocker to local implementation preparation. A real product run needs the
approved PNG, exact text, selected provider/variants, and account configuration.
No Printify/Etsy clients or POD configuration were found in source. Account access
and the connected Etsy vs custom API shop configuration remain unverified.

## What is stale

Before this session, `check_plans_index.py` reported six unindexed plans. The two
HomeFromWorking plans are now archived; four unrelated existing gaps remain:

- `2026-06-13-bbw-v2-landing-design.md`
- `2026-06-13-bbw-v2-landing-plan.md`
- `2026-06-14-feat-bbw-site-trust-positioning-and-demo-gallery-plan.md`
- `2026-06-15-feat-dataforseo-prospect-discovery-plan.md`

## Files touched

- `README.md`, `AGENTS.md`, `docs/README.md`, `docs/agent-model.md`,
  `docs/architecture.md`, `docs/founder/operator-guide.md`: current scope pointers.
- `docs/plans/2026-09-02-home-from-working-pod-design.md`: current direction/design.
- `docs/plans/references/2026-09-02-home-from-working-pod-handoff.md`: supplied source.
- Moved `docs/plans/2026-08-31-home-from-working-design.md` and
  `docs/plans/2026-08-31-home-from-working.md` to `docs/plans/archive/`, retaining
  history and adding superseded status/linkage.
- `docs/plans/INDEX.md`, `docs/plans/archive/INDEX.md`, `docs/founder/INDEX.md`,
  `docs/handoffs/INDEX.md`: navigation and lifecycle updates.
- This session handoff.

## Validation run

- `git diff --check`: passed.
- `python3 scripts/docs/archive_plans.py --check`: passed.
- Generated founder/archive index checks: passed.
- All 17 local links in the new design, supplied reference wrapper, and archived
  plans resolved; superseded status and unchanged source contents verified.
- `python3 scripts/docs/check_plans_index.py`: fails only on the four existing
  unrelated documents listed above.
- No application tests run: this change contains no executable code.

## Working tree

Documentation changes are uncommitted. `git status --short` also reports the
pre-existing `M .claude/launch.json` and `?? products/pokemon-tcg-search/`; those
were untouched. The moved plans appear as deleted old paths plus untracked archive
paths until staged. No approval records were created or modified.

## Exact next action

Read the current POD design and implement the local approved-artwork manifest and
preflight slice with matching Python tests. Resolve the approved PNG and selected
Gildan/provider configuration before a real product run. Do not resume the archived
research-first plan or interpret the supplied briefs as approval to create listings.
