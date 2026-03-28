# Implementation Phases

This document exists to keep `ai-company-os` lean while still making progress toward a real operating system.

The goal is to add capability in layers, not scaffold the whole future at once.

## Phase 1: Core Skeleton

Objective:

- establish repo shape
- document architecture
- define worker boundaries
- define shared task and policy contracts
- separate runtime state from source code

Deliverables:

- root docs
- architecture docs
- `apps/` worker and API entrypoints
- `packages/` shared contracts
- initial tool namespaces for Codex, GitHub, iOS, and App Store integration
- `infra/` buckets for db, scripts, fastlane, and launchd
- `state/` runtime directories

Exit criteria:

- the repo is understandable without prompt context
- worker lanes are explicit
- approval policy has a clear home

## Phase 2: Codex Engineering Lane

Objective:

- make the engineering lane real end-to-end

Deliverables:

- task persistence in Postgres
- queue-backed task routing in Redis
- repo registration and sync logic
- worktree creation and cleanup
- Codex task packet rendering
- validation pipeline for lint, tests, and builds
- PR preparation output

Exit criteria:

- a founder goal can become an engineering task
- the engineering worker can execute against a managed repo in an isolated worktree
- results are stored as explicit task run state

## Phase 3: iOS And App Store Flow

Objective:

- make the Apple delivery path real without collapsing its boundaries

Deliverables:

- iOS-specific task types
- Xcode and simulator execution support
- build artifact tracking
- App Store metadata and release-state tracking
- TestFlight support
- approval-gated submission flow

Exit criteria:

- iOS implementation work and App Store release work move through separate lanes
- release artifacts and submission state are queryable
- final submission remains approval-gated

## Phase 4: Control Plane And Approvals

Objective:

- turn the platform into a real operational control plane

Deliverables:

- task and approval APIs
- founder-facing system inspection
- health and worker status views
- approval state transitions
- audit logs
- a lightweight dashboard if it clarifies operations

Exit criteria:

- operator oversight is possible without reading raw logs
- risky actions are visibly paused behind approval gates

## Phase 5: Optional OpenClaw Bridge

Objective:

- add remote control surfaces without moving orchestration out of the platform

Deliverables:

- bridge APIs for commands and approvals
- notification and status integrations
- remote approval actions

Exit criteria:

- OpenClaw can interact with the platform
- the system still works cleanly if OpenClaw is disabled or removed

## Guardrails Across All Phases

- do not introduce a monolithic super-agent
- do not hide orchestration in prompts
- do not duplicate policy inside workers
- do not merge iOS implementation and App Store release concerns
- do not put runtime state in source directories
- do not add future workers before current lanes justify them
