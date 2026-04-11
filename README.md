# ai-company-os

An AI company operating system for running an AI-first or AI-only business from an always-on Mac.

## Overview

`ai-company-os` is a local-first, policy-driven platform for running a software business with persistent AI workers, explicit task state, approval gates, repo automation, and dedicated delivery lanes.

The intended runtime is an always-on MacBook Air M1. The long-term goal is not a prompt bundle or a monolithic super-agent. It is a durable operating system for an AI-driven company with clear ownership boundaries:

- The platform is the brain.
- Codex is the engineer.
- Postgres is memory.
- Redis is the queue.
- GitHub is the delivery lane.
- OpenClaw is an optional interface, not the orchestration layer.

## Architectural Rules

These rules are non-negotiable:

1. The platform owns orchestration.
2. Codex writes code but does not own business logic or policy.
3. Workers execute tasks but do not define what is allowed.
4. Policies are explicit, shared, and versioned in code.
5. Runtime state lives in `state/`, not in source folders.
6. iOS engineering and App Store release handling are separate lanes.
7. OpenClaw is optional and external to orchestration.

The goal is intentionally boring architecture: readable, modular, safe to extend, and understandable without hidden prompt logic.

## Why This Exists

Most agent systems fail for predictable reasons:

- hidden orchestration inside prompts
- one oversized agent doing everything poorly
- unclear ownership between planning, execution, and approval
- unsafe repo mutations
- weak auditability
- runtime state mixed into source code
- delivery workflows collapsed into a single lane

This repo exists to avoid those failure modes from the start.

## Lean V1

The first version is intentionally small. It focuses on the smallest useful foundation:

- `apps/api`
- `apps/worker-supervisor`
- `apps/worker-engineering`
- `apps/worker-ios`
- `apps/worker-appstore`
- `products/`
- `packages/policies`
- `packages/tools`
- `packages/db`
- `packages/queue`
- `packages/schemas`
- `packages/config`
- `infra`
- `state`
- `docs`

Two deliberate v1 choices:

- The dashboard is described architecturally but not scaffolded yet. The API is enough to establish platform boundaries without adding speculative frontend code.
- OpenClaw is documented as an optional future bridge, but there is no integration code yet. That keeps orchestration owned by this repo.

## End-to-End Shape

A healthy v1 should support this flow:

1. A founder creates a goal such as fixing an iOS onboarding bug or preparing an App Store submission.
2. The supervisor converts that goal into one or more typed tasks.
3. The platform routes each task to the appropriate worker lane.
4. The engineering or iOS worker creates a worktree, prepares a task packet, invokes Codex, validates output, and prepares a PR-ready result.
5. The App Store worker prepares metadata and release state, then pauses at human approval before irreversible submission steps.
6. The API exposes health, task state, approvals, and worker status.

## Repository Layout

```text
ai-company-os/
  apps/
    api/
    worker-supervisor/
    worker-engineering/
    worker-ios/
    worker-appstore/
  packages/
    config/
    db/
    policies/
    queue/
    schemas/
    tools/
      codex_tools/
      github_tools/
      ios_tools/
      appstore_tools/
  products/
    catchbook-ios/
  docs/
    architecture.md
    operating-model.md
    codex-worker.md
    ios-lane.md
    approval-policy.md
    local-dev.md
    products/
  infra/
    db/
    scripts/
    fastlane/
    launchd/
  state/
    repos/
    worktrees/
    artifacts/
    checkpoints/
    logs/
    cache/
```

The full mock tree is a useful north star, but v1 intentionally implements only the subset that clarifies the operating model today. Support, growth, research, ops, dashboard, and OpenClaw stay documented future lanes until the core engineering and release path is real.

## First Managed Product

The first managed product is a private fishing logbook for iPhone.

That product now has:

- a product registry entry in `infra/products.json`
- a managed source root in `products/catchbook-ios/`
- durable product artifacts in `docs/products/catchbook/`
- checkpoint-backed product and release records under `state/checkpoints/platform/`
- an iOS worker path that mirrors the engineering lane

## What Each Layer Owns

### Apps

Worker and API entrypoints. These are thin runtime surfaces that depend on shared contracts and shared policy.

### Packages

Versioned shared code for configuration, task schemas, queue contracts, policy rules, database contracts, and operational tools.

Within `packages/tools/`, v1 already reserves distinct homes for Codex, GitHub, iOS, and App Store helpers. That keeps lane-specific integrations from dissolving into one generic utilities folder.

### Docs

Human-readable architectural anchors. `README.md` explains the system at a high level. `AGENTS.md` defines worker boundaries. `docs/architecture.md` bridges the docs to the code layout.

### Infra

Local infrastructure notes and future deployment helpers for Postgres, Redis, launch agents, and machine setup.

### State

Runtime-owned data only: repos, worktrees, artifacts, checkpoints, and logs.

## Python-First V1

V1 is Python-first unless a stronger reason emerges. That choice keeps the first pass easy to inspect and straightforward to run on macOS:

- simple worker entrypoints
- explicit task contracts
- clear local tooling
- easy process supervision

Framework choices should stay lightweight until the architecture proves itself.

## Current Status

Early control-plane phase.

The immediate priorities are:

- make the architecture legible
- lock in worker boundaries
- encode shared policy in code
- establish Codex integration shape
- keep iOS and App Store responsibilities separate
- keep the repo safe to extend without hidden orchestration
- make goals, tasks, approvals, events, and worker claims real enough to support a minimal control-plane runtime

## Testing

The repo now has a staged automated testing foundation for both the Python platform code and the iOS product.

Current stage:

- tests are required to pass in both lanes
- Python coverage is enforced at `55%`
- iOS coverage is enforced at `20%`

Local commands:

```bash
python3 -m pip install -e ".[test]"
./scripts/test_python.sh
./scripts/test_ios.sh
```

Coverage model:

- Python coverage is measured across `apps/` and `packages/`
- iOS coverage is measured from the `Catchbook` target result bundle with `xccov`
- `PYTHON_COVERAGE_MIN` and `IOS_COVERAGE_MIN` control staged threshold enforcement without changing the scripts
- CI enables the current Stage 1 floors with `PYTHON_COVERAGE_MIN=55` and `IOS_COVERAGE_MIN=20`

Testing policy:

- deterministic logic gets unit tests first
- persistence and orchestration flows get integration tests
- UI-heavy snapshot testing and browser-style end-to-end flows are intentionally deferred for now
- logic-bearing Python changes under `apps/` or `packages/` must ship with created or modified tests under `tests/python/`
- logic-bearing iOS changes under `products/catchbook-ios/Sources/` must ship with created or modified tests under `products/catchbook-ios/Tests/`
- valid no-test exceptions must be declared explicitly with a machine-readable `no_test_reason_code`
- workers persist structured `testing_policy` and `failure_codes` data so missing tests fail as `VALIDATION_FAILED` with a specific reason such as `missing_tests_for_logic_change`

Runtime-state isolation:

- production code still writes to the repo `state/` tree by default
- Python tests set an isolated repo-root override so stateful tests write into a temporary `state/` tree instead of the real repo runtime directories

## Getting Started

This repo currently provides a minimal real control-plane slice, three lane worker loops, and a thin local runtime supervisor with a CLI operator surface.

Local runtime operator workflow:

```bash
./scripts/runtime start
./scripts/runtime status
./scripts/runtime stop
```

Current runtime truth:

- `./scripts/runtime` is a thin wrapper around `apps/runtime-supervisor/cli.py`
- `start` launches the local runtime supervisor in the background
- `status` reads the persisted supervisor status file
- `stop` writes a stop-request file that the running supervisor honors for clean shutdown
- the runtime supervisor manages the existing engineering, iOS, and App Store worker loops only

Suggested next implementation steps after this scaffold:

1. Point `AI_COMPANY_OS_DATABASE_URL` at Postgres to move the control-plane records off the default local SQLite file.
2. Replace the current durable queue table with Redis once worker daemons are running continuously.
3. Add a richer operator surface only after the local runtime loop proves stable in day-to-day use.
4. Expand approval persistence and enforcement from the current narrow task/release actions to more public workflows.

## Read Next

- [AGENTS.md](/Users/simons/ai-company-os/AGENTS.md)
- [docs/architecture.md](/Users/simons/ai-company-os/docs/architecture.md)
- [docs/implementation-phases.md](/Users/simons/ai-company-os/docs/implementation-phases.md)
- [docs/approval-policy.md](/Users/simons/ai-company-os/docs/approval-policy.md)
- [docs/local-dev.md](/Users/simons/ai-company-os/docs/local-dev.md)
- [docs/operating-model.md](/Users/simons/ai-company-os/docs/operating-model.md)
- [docs/codex-worker.md](/Users/simons/ai-company-os/docs/codex-worker.md)
- [docs/ios-lane.md](/Users/simons/ai-company-os/docs/ios-lane.md)
- [docs/engineering-flow.md](/Users/simons/ai-company-os/docs/engineering-flow.md)
- [docs/approval-flow.md](/Users/simons/ai-company-os/docs/approval-flow.md)
- [docs/decisions/0001-foundation.md](/Users/simons/ai-company-os/docs/decisions/0001-foundation.md)
