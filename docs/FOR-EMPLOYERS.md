# For Employers — read this first

You probably arrived here from a job application where I called this my main
side project. You are a skeptical engineer. Good. This document is written for
you, and everything in it is checkable from the repo in about five minutes.

If you want the fastest guided pass after this page, open
[`docs/EVALUATOR-WALKTHROUGH.md`](EVALUATOR-WALKTHROUGH.md) or run
`./scripts/evaluator_check.sh`.

## What this is, in one sentence

`ai-company-os` is an AI-first engineering system: I direct a fleet of AI
coding agents to discover product niches, build apps, and ship them — inside
a control plane with typed tool boundaries, human approval gates, and a full
audit trail, so the system can run unattended without me losing track of what
it did or why.

It is not a prompt bundle and not a single mega-agent. The platform owns
orchestration; agents only execute within boundaries the platform defines.

## The honest framing (because you will check)

Run `git log` — you should. Here is what it shows and what it means:

- **First commit 2026-03-27.** This is roughly a two-month intensive build,
  not a multi-year project. I will never tell you otherwise.
- **~565 commits, large parallel branch set.** This is not noise or
  embellishment. It is the *output of the pipeline working*: I run many AI
  agents in parallel, each on its own branch, gated and reviewed before
  merge. The velocity is the thesis of the project, not an accident of it.
- **Three shipped iOS products in `products/`** (life-clock, catchbook,
  after-plans). These are not off-topic sprawl — they are what the system
  *produces*. A niche-discovery → build → market → release loop that has not
  shipped anything is a slide deck. This one ships.

If a claim about this project cannot survive `git log`, I do not make it.
That constraint is deliberate and it is the most important thing this
document is trying to demonstrate about how I work.

## Claim → code map (verify in five minutes)

| Claim | Where to look |
|---|---|
| Platform owns orchestration; agents are lane workers | `apps/worker-*`, `apps/runtime-supervisor`, `apps/api` |
| Typed tool/task surface — enum-constrained, validated at the boundary | `packages/schemas/` — frozen dataclasses with `str, Enum` fields and explicit `to_dict`/`from_dict` (`goal.py`, `approval.py`, `event.py`, `postmortem.py`, `release.py`, `product.py`); Pydantic models guard the API surface in `apps/api/` |
| Human-in-the-loop gates on consequential actions | `packages/policies/approvals.py`, `packages/policies/approval_tokens.py`, `apps/api/approval_endpoint.py`, `apps/approval-reviewer/main.py` |
| Recurring operator workflow around approvals | `scripts/scheduled/approval_sweep_session.md`, `docs/recurring-approval-sweep.md` |
| Every run writes a structured audit artifact, with retention | `packages/db/postmortem_store.py`, `packages/policies/postmortem_retention.py` |
| Repo mutations are isolated, not hidden in prompts | git worktree flow; `state/` holds runtime state, never source |
| Secrets never leak into artifacts | redaction tests asserting `sk-…` / `AKIA…` are scrubbed; `.env` gitignored; clean history |
| Process maturity uncommon in a solo repo | `.github/workflows/tests.yml`, tests-ship-with-code policy, PR template, conventional commits, 95 Python test suites |

## Run it yourself in under a minute (no setup)

```bash
./scripts/evaluator_check.sh
make demo        # or: ./scripts/demo.sh
```

No Postgres, Redis, Codex, network, or Mac runtime required. It prints the
control loop end to end (goal → task → execute → validate → human approval
gate → audit artifact) and writes schema-faithful sample artifacts to
[`docs/examples/`](examples/) — built from the real schema classes, so they
cannot drift from production.

`./scripts/evaluator_check.sh` wraps the demo, confirms the key files exist,
and can optionally run a fast Python test subset when test dependencies are
installed.

## The five-minute evaluation path

1. Read this file, then run `./scripts/evaluator_check.sh` or `make demo`.
2. `git log --oneline | head` — confirm velocity and conventional commits.
3. `packages/schemas/` — see the typed boundary the agents are constrained by.
4. `packages/policies/approvals.py` + `apps/api/approval_endpoint.py` — see
   the human gate that makes unattended operation safe.
5. `products/life-clock-ios/`, `products/catchbook-ios/`, and
   `products/after-plans-ios/` — inspect the actual product outputs.
6. `./scripts/test_python.sh` — verify the current platform baseline.

## What I want you to take from it

- I design **systems and ownership boundaries**, not prompt chains.
- I treat **safety and auditability as the product**: typed boundaries,
  approval gates, replayable audit trail — the same properties that make any
  production system trustworthy.
- I can **direct AI agents at real scale** and still stay in control of the
  output, because I built the observability to do so.
- I **ship**. The system has produced real iOS apps, not just a framework.
- I **state only what survives scrutiny.** That is the trait this whole
  document is built to prove.

## Why there are so many branches (this is the method, not mess)

If you run `git branch -a` you will see a large set of `claude/*` and
`feat/*` branches. That is the pipeline, working as designed:

- I run AI coding agents in parallel, each isolated on its own branch and
  its own git worktree (`state/worktrees/`), so concurrent work cannot
  collide.
- Each branch is gated the same way: typed task contract in, validation +
  testing-policy enforcement, then a human approval gate before anything
  irreversible (merge, release).
- `main` is the only thing that matters for evaluation — it is what every
  gated, reviewed change lands into. The branch fan-out is the throughput
  mechanism; the gates are why throughput does not mean chaos.

Directing many agents at once is the point of the system. The
infrastructure in this repo exists so I can do that and still answer, for
any change, exactly what happened and why.

## Go deeper

- **[One workflow, traced end to end](flagship-simulator-driven-polish.md)** —
  discover/define a product → build for the simulator → screenshot-audited
  polish against reference apps → approval-gated App Store handoff. Every
  file cited exists; the Life Clock session logs are real loop output.
- **[What this taught me about reliability](reliability-lessons.md)** —
  seven concrete reliability decisions and the code/tests behind each.

## Known rough edges (I would rather you hear it from me)

This is a fast-moving solo system, not a polished open-source library. The
default branch is a working monorepo: platform code in `apps/` and
`packages/`, product code in `products/`, generated run docs in `docs/`. If
you want the cleanest read of the engineering, start with the claim → code
map above rather than browsing top-down.
