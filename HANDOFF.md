# ai-company-os — session handoff (updated 2026-05-19)

Read this first when resuming on a new machine.

## What this repo is

An AI-first engineering system: Kashane directs a fleet of AI coding agents to
discover product niches, build apps, and ship them inside a control plane with
typed tool boundaries, human approval gates, and a replayable audit trail.
It is the flagship job-application project. The goal is not to hide AI usage;
the goal is to make the system legible, honest, verifiable, and impressive to a
skeptical engineer.

## Strategy (decided, do not relitigate)

Own the AI-written surface and make it easy to verify. Every employer-facing
claim should survive:

- `git log`
- local commands
- opening the cited files

Do not claim production soak, long tenure, or "fully autonomous" behavior
unless the repo proves it directly. When in doubt, soften the claim.

## Current verified baseline

- `main` and `origin/main` are aligned at `17c6fd8`
  (`docs: tighten evaluator path and recurring approval trace`).
- `make demo` passes.
- `./scripts/test_python.sh` passes with `495 passed, 1 skipped`.
- Python coverage from the last verified full run: `76%`.
- README de-stale pass is complete enough that the top-level docs no longer
  describe the repo as an "early scaffold."
- `docs/recurring-approval-sweep.md` exists and traces one recurring
  approval-gated workflow honestly.
- `CONTRIBUTING.md` exists.
- The GTM validator fix is already merged into the baseline.

## What changed before this handoff

The current `main` already includes the earlier employer-facing cleanup that:

- rewrote the README top fold and repo orientation
- added `docs/FOR-EMPLOYERS.md`
- clarified `docs/README.md`
- added the zero-dependency demo in `make demo` / `scripts/demo.sh`
- generated schema-faithful sample artifacts under `docs/examples/`
- added recurring-approval workflow tracing
- kept the repo's framing aligned with what can actually be verified locally

The old `HANDOFF.md` still described the repo around PR #48 and `414a514`.
That is now stale and should not be reused.

## Resume commands

```bash
make demo
./scripts/test_python.sh
```

If you want the fastest evaluator path after resuming, also check:

```bash
./scripts/evaluator_check.sh
```

## Employer-readiness backlog (multi-week)

Keep this order unless a blocking bug or broken claim appears.

1. Update and preserve the verification baseline whenever framing changes.
2. Tighten the employer evaluation path across `README.md`,
   `docs/FOR-EMPLOYERS.md`, `docs/README.md`, and `CONTRIBUTING.md`.
3. Expand `docs/examples/` so the full claim set is inspectable:
   goal, typed task, worker result, validation outcome, approval gate,
   task-run artifact, and postmortem/follow-up artifact.
4. Keep one low-setup employer verification script current
   (`scripts/evaluator_check.sh`).
5. Resolve P1 Life Clock accessibility parity for agent-driveable flows
   (see `todos/028-pending-p1-life-clock-a11y-id-gaps-block-agent-flows.md`).
6. Resolve P1 Life Clock quest persistence key stability
   (see `todos/026-pending-p1-life-clock-quest-persistence-fragile-key.md`).
7. Extract Life Clock support-moment presentation logic
   (see `todos/027-pending-p1-life-clock-store-presentation-leak.md`).
8. Resolve Catchbook location-model planning compatibility
   (see `todos/001-pending-p1-define-location-migration-compatibility.md`).
9. Improve per-product orientation under `products/*/README.md`.
10. Maintain a short evaluator walkthrough with exact commands and expected
    outcomes.
11. Audit employer-facing docs for broken links and stale paths.
12. Make recurring workflows more verifiable without overclaiming production
    scheduling.
13. Raise confidence in approval gates with more fail-closed coverage where
    needed.
14. Keep generated docs understandable without spending days reorganizing them.
15. Mirror material framing changes into the companion `job-hunt` repo
    (`profile/raw/ai-company-os.md`) when needed.

## Current first-session target

The recommended next session is:

1. Refresh this handoff.
2. Re-run `make demo` and `./scripts/test_python.sh`.
3. Add `docs/EVALUATOR-WALKTHROUGH.md`.
4. Add or update `scripts/evaluator_check.sh`.
5. Wire the new evaluator path into top-level docs.
6. Commit and push on a reviewable branch.

## Companion repo

`github.com/kashane1/job-hunt` has its own `HANDOFF.md`. If this repo's
employer framing changes materially, update `profile/raw/ai-company-os.md`
there and regenerate any dependent application answers.
