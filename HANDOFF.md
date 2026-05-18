# ai-company-os — session handoff (last updated 2026-05-18)

Read this first when resuming on a new machine.

## What this repo is

An AI-first engineering system: a fleet of AI coding agents, directed by
Kashane, that discovers product niches, builds apps, and ships them — with
typed boundaries, human approval gates, and a replayable audit trail.
~2 months old, ~600 commits, three iOS products. It is Kashane's flagship
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

## Follow-up session 2026-05-18 (branch `claude/nifty-cori-3923dc`, not yet merged)

All four prior "Next goals" are now closed:

1. **Full suite run — done.** Disk recovered (was 98%, now ~36%). Running
   the documented eval path from a clean venv surfaced a real bug:
   `python-multipart` and `pydantic` were imported by `apps/`/`packages/`
   but undeclared, so `pip install -e ".[test]" && pytest tests/python`
   hit 2 collection errors on a fresh clone. Added both to
   `pyproject.toml`; verified from a clean venv: `make demo` clean,
   **495 passed / 1 skipped**. (Import audit: only those two were missing.)
2. **README de-stale — done.** #2/#3/#4 were largely closed by upstream
   commit `17c6fd8` (CONTRIBUTING.md, recurring-approval-sweep.md, README
   status sections). Remaining tonal seams removed this session: "paper
   scaffold", "a healthy v1 should support", "after this scaffold" →
   present-tense where the demo/products substantiate it; deliberate
   dashboard/OpenClaw scoping left intact.
3. **Claim integrity pass — done.** Validated every `FOR-EMPLOYERS.md`
   claim→code path (all 19 resolve). Stale numbers corrected to survive
   `git log`: `~565`→`~600` commits, `95`→`98` test files, across README,
   FOR-EMPLOYERS, and this file.

Commits on this branch: `31e9f67` (deps fix), `a95f98b` (README de-stale),
`35ae5b2` (number corrections). **Not yet merged to `origin/main`.**

## Next goals (priority order)

1. **Open a PR for branch `claude/nifty-cori-3923dc` and merge.** Self-
   contained: dep fix + truthful doc corrections. After merge, `origin/main`
   commit count moves to ~608 — `~600` phrasing was chosen to stay accurate
   across the merge, so no further number edits needed.
2. Optional polish from the original review: a tiny pip-installable engine
   quickstart, more sample artifacts in `docs/examples/`.

## Companion

The `job-hunt` repo (github.com/kashane1/job-hunt) has its own
`HANDOFF.md`. Its application answers describe THIS repo; if the framing
here changes materially, update `profile/raw/ai-company-os.md` there and
regenerate.
