# docs/ — start here

Most of this directory is generated *by the system as it works* — product
specs, run plans, session handoffs, postmortems. The volume is the system
documenting its own output, not hand-written prose. If you are evaluating
the engineering, do not read top-to-bottom — use the map below.

## For agents resuming work

- [../REPO_MAP.md](../REPO_MAP.md) — 60-second orientation across the five zones
- [preflight-for-agents.md](preflight-for-agents.md) — boundaries for this session
- [handoffs/INDEX.md](handoffs/INDEX.md) — append-only dated session handoffs
- [plans/INDEX.md](plans/INDEX.md) — per-feature implementation plans

## Read these first (the platform)

- [FOR-EMPLOYERS.md](FOR-EMPLOYERS.md) — honest framing + claim→code map.
- [EVALUATOR-WALKTHROUGH.md](EVALUATOR-WALKTHROUGH.md) — shortest practical review path with exact commands.
- [architecture.md](architecture.md) — how the docs map to the code layout.
- [operating-model.md](operating-model.md) — ownership boundaries.
- [approval-policy.md](approval-policy.md) / [approval-flow.md](approval-flow.md) — the human gate.
- [recurring-approval-sweep.md](recurring-approval-sweep.md) — recurring approval-gated operator workflow.
- [engineering-flow.md](engineering-flow.md) / [codex-worker.md](codex-worker.md) — how a task runs.
- [ios-lane.md](ios-lane.md) — the iOS product lane.
- [founder/operator-guide.md](founder/operator-guide.md) — **operator commands**: discovery sweeps, scoring, runtime, validation, agent prompts.
- [founder/discovery-guide.md](founder/discovery-guide.md) — discovery layer deep dive: find → score → validate (front of the loop).
- [example_prompts.md](example_prompts.md) — example prompts to run in this repo + what each one activates.
- [examples/](examples/) — schema-faithful sample audit artifacts.

## Everything else is run/spec output (skim, don't read)

| Path | What it is |
|---|---|
| `products/` (~359 files) | Per-product specs, positioning, and release artifacts the system produced while building the iOS apps |
| `plans/` (~38) | Per-feature implementation plans generated before execution |
| `solutions/` (~20) | Recorded fixes/learnings from real runs |
| `brainstorms/`, `handoffs/`, `research/` | Working notes from individual agent sessions |
| `decisions/`, `adr/` | Architecture decision records |
| `failure-modes/`, `security/`, `runbooks/` | Operational hardening notes |

Treating these as the system's audit/working trail (not documentation to
be read linearly) is the intended way to evaluate this repo.
