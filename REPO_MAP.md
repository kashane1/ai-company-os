# REPO_MAP

A fresh-agent orientation. Read this in 60 seconds, then read
[docs/preflight-for-agents.md](docs/preflight-for-agents.md) before doing any
work that mutates the repo.

## What this repo is

`ai-company-os` — a local-first platform that turns founder goals into
typed worker tasks, runs them inside isolated git worktrees, gates
irreversible actions behind a human approval surface, and ships real iOS
products. See [README.md](README.md) for the longer narrative and
[docs/architecture.md](docs/architecture.md) for how docs map to code.

## Five zones

| Zone | What it owns | Where state lives |
|---|---|---|
| [apps/](apps/) | Worker + API entrypoints (engineering, iOS, App Store, GTM, supervisor, runtime-supervisor, approval-reviewer, skill-evolution) | reads/writes `state/` |
| [packages/](packages/) | Shared platform code: `schemas`, `policies`, `db`, `queue`, `tools`, `config` | reads/writes `state/` |
| [products/](products/) | Managed iOS product source (one subdir per product) | reads/writes nothing outside its own tree |
| [docs/](docs/) | Architecture docs **plus** run/spec output the system produced | the system writes here as it works |
| [state/](state/) | Runtime-owned data only — never source. Glossary at [state/README.md](state/README.md) | every worker and skill writes here |

Two supporting zones:

| Zone | Purpose |
|---|---|
| [skills/](skills/) | Canonical skill definitions + adapters + registry. Source of truth for reusable agent procedures. See [skills/WIRING.md](skills/WIRING.md). |
| [infra/](infra/) | Local infra notes, product registry, launchd plists, fastlane stubs. Product registry is [infra/products.json](infra/products.json). |

## Where things go

| Need to write… | Write to |
|---|---|
| a runtime artifact (diff, report, log) | `state/artifacts/<lane>/<run-id>/` |
| a checkpoint (task, task-run, repo, worktree) | `state/checkpoints/platform/<kind>/` |
| a session handoff | `docs/handoffs/YYYY-MM-DD-<short-slug>.md` (see [docs/handoffs/INDEX.md](docs/handoffs/INDEX.md)) |
| a feature plan | `docs/plans/YYYY-MM-DD-<slug>-plan.md` (see [docs/plans/INDEX.md](docs/plans/INDEX.md)) |
| a working ticket | `todos/NNN-<status>-<priority>-<slug>.md` (see [todos/README.md](todos/README.md)) |
| an ADR | `docs/adr/YYYY-MM-DD-<slug>.md` |
| a postmortem | through `PostMortemStore.save` ([packages/db/postmortem_store.py](packages/db/postmortem_store.py)) |
| a product brief / spec | `docs/products/<product-id>/` |
| product source | `products/<product-id>/` |
| a discovered opportunity | `state/checkpoints/platform/opportunities/` (via `OpportunityInbox`) |

## Where things must NOT go

| Surface | Rule |
|---|---|
| product source under `products/*` | Do not touch unless the task is explicitly product work and you're in the iOS lane |
| `state/` | Source files never live here; only runtime writes |
| `packages/policies/` | Requires explicit founder approval to edit |
| `packages/schemas/` | Requires explicit founder approval to edit |
| `skills/canonical/` | Source of truth for skills — edit via the proper review path only |
| `skills/adapters/` | Runtime translations — edit alongside the canonical they implement |
| `skills/registry.yaml` | Indexed; touch only when a skill is added, retired, or restaged |
| `.claude/skills/` | Routing pointers only. Never add skill logic here. See [skills/WIRING.md](skills/WIRING.md). |
| `.claude/commands/`, `.claude/hooks/`, `.claude/settings*.json` | Operator-owned; do not edit without explicit approval |
| `.local`, `.codex/` | Private operator surfaces; never inspect or edit |

## What a fresh agent should read first

1. [REPO_MAP.md](REPO_MAP.md) — this file
2. [docs/preflight-for-agents.md](docs/preflight-for-agents.md) — boundaries for this session
3. [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md) — short pointers
4. [docs/skills-index.md](docs/skills-index.md) — the skill catalog + trigger phrases
5. [docs/architecture.md](docs/architecture.md) — how docs map to code
6. [docs/approval-policy.md](docs/approval-policy.md) — what requires human approval

## Architectural rules (non-negotiable)

- The platform owns orchestration.
- Codex writes code but does not own business logic or policy.
- Workers execute tasks but do not define what is allowed.
- Policies are explicit, shared, and versioned in code.
- Runtime state lives in `state/`, not in source folders.
- iOS engineering and App Store release handling are separate lanes.
- OpenClaw is optional and external to orchestration.

## Skill chain (binding)

Skills are defined canonically and adapted per runtime. The chain is:

```
skills/canonical/<id>/   →   skills/adapters/<runtime>/<id>.md   →   .claude/skills/<id>.md
   (source of truth)         (translation, e.g. Claude/Codex)        (discovery pointer only)
```

`.claude/skills/*.md` are thin pointers. **Do not add skill logic to project
skill files.** Edit the adapter or canonical source instead. Full convention
in [skills/WIRING.md](skills/WIRING.md).

If multiple trigger phrases match a user message, ASK rather than guess
(disambiguation rule, [docs/skills-index.md](docs/skills-index.md)).

## Lanes at a glance

| Lane | App entrypoint | Lane doc |
|---|---|---|
| Supervisor | [apps/worker-supervisor/](apps/worker-supervisor/) | [docs/agent-model.md](docs/agent-model.md) |
| Engineering | [apps/worker-engineering/](apps/worker-engineering/) | [docs/engineering-flow.md](docs/engineering-flow.md), [docs/codex-worker.md](docs/codex-worker.md) |
| iOS | [apps/worker-ios/](apps/worker-ios/) | [docs/ios-lane.md](docs/ios-lane.md) |
| App Store | [apps/worker-appstore/](apps/worker-appstore/) | [docs/appstore-lane.md](docs/appstore-lane.md) |
| GTM | [apps/worker-gtm/](apps/worker-gtm/) | (per-skill docs under `skills/canonical/`) |
| Skill evolution | [apps/worker-skill-evolution/](apps/worker-skill-evolution/) | [docs/runbooks/skill-evolution-revert.md](docs/runbooks/skill-evolution-revert.md) |
| API | [apps/api/](apps/api/) | [docs/architecture.md](docs/architecture.md) |
| Runtime supervisor | [apps/runtime-supervisor/](apps/runtime-supervisor/) | [docs/local-dev.md](docs/local-dev.md) |
| Approval reviewer | [apps/approval-reviewer/](apps/approval-reviewer/) | [docs/approval-flow.md](docs/approval-flow.md) |

## Running the demo

```
make demo
```

Zero-dependency end-to-end demo: goal → typed task → worker execution →
validation → human approval gate → audit artifact. No Postgres, Redis,
Codex, network, or Mac runtime required.

For the **discovery layer** (find → score → validate, the front of the loop):

```
python3 scripts/discovery_demo.py
```

Offline by default. Start with [docs/founder/discovery-guide.md](docs/founder/discovery-guide.md).

## End-of-session

Write a dated handoff under `docs/handoffs/`. See
[docs/handoffs/INDEX.md](docs/handoffs/INDEX.md) for the structure.
