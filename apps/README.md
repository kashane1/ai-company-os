# apps/

Thin worker and API entrypoints for the platform. Each subdirectory is
a single lane, owning a narrow slice of execution responsibility.
Shared logic lives in [packages/](../packages/), not here.

## Lane table

| App | Lane | Likely entrypoint | Owns | Does not own | Related doc |
|---|---|---|---|---|---|
| [worker-supervisor/](worker-supervisor/) | supervisor | `main.py` | Goal decomposition, task routing, prioritization | Implementation, release work, repo mutation | [docs/agent-model.md](../docs/agent-model.md) |
| [worker-engineering/](worker-engineering/) | engineering | `main.py` | Generic software implementation via Codex in isolated worktrees | Product strategy, release operations, deployment | [docs/engineering-flow.md](../docs/engineering-flow.md), [docs/codex-worker.md](../docs/codex-worker.md) |
| [worker-ios/](worker-ios/) | iOS | `main.py` | iOS bugfix/feature work, Xcode builds, simulator runs, release-candidate artifacts | App Store submission, metadata, public release | [docs/ios-lane.md](../docs/ios-lane.md) |
| [worker-appstore/](worker-appstore/) | App Store | `main.py` | TestFlight prep, metadata, screenshots, App Store Connect interactions, release-state tracking | iOS implementation, code edits, build artifacts | [docs/appstore-lane.md](../docs/appstore-lane.md) |
| [worker-gtm/](worker-gtm/) | GTM | `main.py` | Content factory, scheduling, niche research, GTM artifact refresh | Product code, App Store submission, approval policy | per-skill docs under `skills/canonical/` |
| [worker-skill-evolution/](worker-skill-evolution/) | skill evolution | `main.py` | Skill-self-evolution worker (privilege-gated) | Direct skill edits without policy clearance | [docs/runbooks/skill-evolution-revert.md](../docs/runbooks/skill-evolution-revert.md) |
| [api/](api/) | API / control plane | `server.py`, `main.py` | Goals, tasks, approvals, release state, health, magic-link approval endpoint | Worker execution, repo mutation, policy decisions | [docs/architecture.md](../docs/architecture.md) |
| [runtime-supervisor/](runtime-supervisor/) | runtime supervisor | `cli.py`, `main.py` | Local launchd-friendly supervisor for worker loops; status + clean shutdown | Task creation, worker logic | [docs/local-dev.md](../docs/local-dev.md) |
| [approval-reviewer/](approval-reviewer/) | approval reviewer | `main.py` | Review-side helpers for the approval surface | Approval decisions (the magic-link endpoint is the only writer) | [docs/approval-flow.md](../docs/approval-flow.md), [docs/approval-policy.md](../docs/approval-policy.md) |

## Cross-cutting rules

- Workers must not own policy. Policy lives in
  [packages/policies/](../packages/policies/).
- Workers must not invent schemas. Schemas live in
  [packages/schemas/](../packages/schemas/).
- Workers read and write `state/` through the writers documented in
  [state/README.md](../state/README.md). They do not write source.
- iOS and App Store are separate lanes by design. A worker in one lane
  must not silently span the other.
- The runtime supervisor manages worker loop lifecycles. It does not
  claim tasks or perform work.

## Per-app READMEs

The pattern: each worker app gets a short README documenting its lane
boundary, entrypoint, task type, allowed boundaries, forbidden areas,
and validation expectations. See
[worker-engineering/README.md](worker-engineering/README.md) for the
reference shape. Other workers will follow.

## When to add a new app

When a genuinely new lane emerges that:

- has its own task type
- has different approval boundaries than existing lanes
- needs its own validation pipeline
- can be reasoned about in isolation

If a "new" responsibility can be served by extending an existing
worker without expanding its scope, prefer that. Worker proliferation
makes the system harder to reason about than worker reuse.
