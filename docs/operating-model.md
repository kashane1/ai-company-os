# Operating Model

`ai-company-os` should feel like an operating platform, not a collection of prompts.

This document describes how the system is expected to run day to day.

## Five Zones

The repo is easiest to reason about as five zones:

1. `apps/` for runnable services
2. `packages/` for shared platform logic
3. `infra/` for machine and environment setup
4. `state/` for runtime-owned data
5. `docs/` for the human operating manual

Each zone has a different job. Confusion starts when they bleed into each other.

## Founder-To-Worker Flow

A healthy operating loop looks like this:

1. A founder creates a goal through the control plane.
2. The supervisor turns that goal into typed tasks.
3. Tasks are persisted and queued.
4. A specialist worker claims the next task.
5. The worker executes using shared tools and shared policy.
6. Artifacts, logs, and results are written to `state/`.
7. If a risky next step exists, approval is requested.
8. The API exposes current status and next actions.

This makes the system debuggable by inspecting state and events instead of inferring intent from prompts.

## Core Lanes

V1 cares about four lanes:

- supervisor
- engineering
- iOS
- App Store

The supervisor coordinates. The engineering lane wraps Codex for general repo work. The iOS lane owns Apple-platform implementation. The App Store lane owns distribution and release handling.

## Runtime On The Mac

The intended local runtime shape is:

- API process
- supervisor worker
- engineering worker
- iOS worker
- App Store worker
- Postgres
- Redis

Optional later surfaces:

- dashboard
- OpenClaw bridge

This operating model treats the Mac as the host where local repos, worktrees, Xcode, simulator tooling, Codex CLI, and release helpers all coexist.

## Why This Matters

Attempt three stays sane only if three things remain true:

1. workers do not own policy
2. OpenClaw does not own orchestration
3. Codex does not own business logic

Everything else in the repo should reinforce those boundaries.
