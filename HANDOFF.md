# ai-company-os — session handoff (work done 2026-05-17)

> Superseded by `docs/handoffs/INDEX.md`. Preserved for historical context only.

Read this first when resuming on a new machine.

## What this repo is

An AI-first engineering system: a fleet of AI coding agents, directed by
Kashane, that discovers product niches, builds apps, and ships them — with
typed boundaries, human approval gates, and a replayable audit trail.
~2 months old, ~565 commits, three iOS products. It is Kashane's flagship
side project for job applications.

## Strategy (decided, do not relitigate)

Own it and show everything, truthfully. Reframe the "AI wrote this" /
"sprawl" signals as the thesis (parallel-agent pipeline, system documents
its own runs), not hide them. Every claim must survive `git log` and a
skeptical engineer opening the cited file. No tenure/production-soak claims.

## What was done this session — **PR #48 MERGED into origin/main**

PR #48 (branch `portfolio/employer-facing-polish`) was merged on
2026-05-18. `origin/main` is at `414a514` and includes all of the below
plus the 35 prior upstream commits. Local `main` == `origin/main`.

- README top-fold rewrite, badges, Mermaid architecture diagram, repo
  orientation table; removed a stale layout section that contradicted
  reality (catchbook-only, missing workers).
- `docs/FOR-EMPLOYERS.md` — honest framing, claim→code map, 5-min eval path.
- `docs/README.md` — orients a reader so docs sprawl reads as run output.
- `docs/flagship-simulator-driven-polish.md` — one workflow traced end to
  end, every cited path verified, real Life Clock session logs as evidence.
- `docs/reliability-lessons.md` — 7 reliability decisions, each tied to
  code/tests.
- Proprietary all-rights-reserved `LICENSE`; `Makefile` + `scripts/demo.sh`
  + `scripts/demo/run_demo.py` — zero-dependency end-to-end demo emitting
  schema-faithful artifacts to `docs/examples/`.
- Tests (9 passing): `tests/python/unit/test_typed_tool_surface.py`,
  `tests/python/integration/test_end_to_end_control_loop.py`,
  `tests/python/integration/test_audit_artifact_crash_safety.py`.
- CI: stopped gating iOS coverage (UI-heavy lane; still reported).
- Bundled unrelated in-progress WIP (life-clock Info.plist, project.yml,
  legal docs) to preserve it. Runtime `state/` intentionally excluded.
- Also pruned 34 already-merged local branches (safe `-d`; remote untouched).

## Current git state

- `origin/main` = `414a514` (PR #48 merge commit) — fully up to date.
- On a fresh clone you get everything; just `git clone` and go.

## How to resume

```bash
make demo                 # zero-dep end-to-end demo, no setup
./scripts/test_python.sh  # full suite (NOT verified last session — disk was 98%)
.venv/bin/python -m pytest tests/python -q   # alt
```

## Next goals (priority order)

1. **Run the full `tests/python` suite.** Last session only verified the 3
   new files (9/9) + collection (495, no import errors); disk was 98% full
   so the whole suite was not run. Free disk first.
2. **De-stale the rest of the README.** Top-fold is rewritten, but lower
   sections ("Lean V1", "Current Status: Early control-plane phase",
   "Getting Started: minimal real control-plane slice") tonally contradict
   "ships 3 products, ~565 commits." A skeptical top-to-bottom reader feels
   the seam. Do a truthful de-stale pass.
3. **Strengthen the weakest claim.** "runs recurring workflows behind
   approval gates" is the least independently verifiable line vs the
   code-cited ones. Add one concrete traced recurring workflow, or soften.
4. Optional polish from the original review: `CONTRIBUTING.md`, a tiny
   pip-installable engine quickstart, more sample artifacts.

## Companion

The `job-hunt` repo (github.com/kashane1/job-hunt) has its own
`HANDOFF.md`. Its application answers describe THIS repo; if the framing
here changes materially, update `profile/raw/ai-company-os.md` there and
regenerate.
