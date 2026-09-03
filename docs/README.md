# docs/ — start here

Most of this directory is generated *by the system as it works* — product
specs, run plans, session handoffs, postmortems. The volume is the system
documenting its own output, not hand-written prose. If you are evaluating
the engineering, do not read top-to-bottom — use the map below.

## For agents resuming work

- [founder/printify-shirt-workflow.md](founder/printify-shirt-workflow.md) — next-shirt procedure and reusable CLI: native Duplicate once, API artwork/copy update, preserve mockups and prices, one visual review.
- [plans/2026-09-02-home-from-working-pod-design.md](plans/2026-09-02-home-from-working-pod-design.md) — broader HomeFromWorking direction; operated draft CLI available, Etsy payload automation remains planned.
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
- [agency/README.md](agency/README.md) — **the web/agency (WaaS) lane map**: prospecting, demo sites, client sites, the three build paths, and the `state/prospects/` data layout. Routes to [waas-prospecting-lane.md](waas-prospecting-lane.md), [demo-site-build-playbook.md](demo-site-build-playbook.md), and [agency/client-lifecycle.md](agency/client-lifecycle.md).
- [founder/operator-guide.md](founder/operator-guide.md) — **operator commands**: discovery sweeps, scoring, runtime, validation, agent prompts.
- [founder/discovery-guide.md](founder/discovery-guide.md) — discovery layer deep dive: find → score → validate (front of the loop).
- [example_prompts.md](example_prompts.md) — example prompts to run in this repo + what each one activates.
- [examples/](examples/) — schema-faithful sample audit artifacts.

## Everything else is run/spec output (skim, don't read)

Each directory below carries an auto-generated `INDEX.md` (title + one-line
summary per file). **Read the index, then open only the file you need** —
don't read the directory top-to-bottom. Regenerate after adding docs with
`python3 scripts/docs/gen_doc_index.py <dir>` (`--recursive` for nested dirs).

| Path | What it is |
|---|---|
| `products/` (~219 files) | Per-product specs, positioning, and release artifacts the system produced while building the iOS apps |
| [`plans/`](plans/INDEX.md) (46) | Per-feature implementation plans; completed/superseded ones move to `plans/archive/` |
| [`solutions/`](solutions/INDEX.md) (21) | Recorded fixes/learnings from real runs (categorized subfolders) |
| [`agency/`](agency/INDEX.md), [`founder/`](founder/INDEX.md) | Lane maps and operator guides |
| [`brainstorms/`](brainstorms/INDEX.md), `handoffs/`, [`research/`](research/INDEX.md) | Working notes from individual agent sessions |
| [`decisions/`](decisions/INDEX.md), [`adr/`](adr/INDEX.md) | Architecture decision records |
| [`failure-modes/`](failure-modes/INDEX.md), [`security/`](security/INDEX.md), [`runbooks/`](runbooks/INDEX.md) | Operational hardening notes |

Treating these as the system's audit/working trail (not documentation to
be read linearly) is the intended way to evaluate this repo.
