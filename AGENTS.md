# AGENTS.md

This document defines the intended agent model, worker responsibilities, system boundaries, and operating rules for `ai-company-os`.

Its purpose is to keep the system legible as it grows and to prevent drift into a vague multi-agent mess.

## Guiding Principle

This system is not one agent that does everything.

It is a platform with explicit orchestration and specialized workers.

The platform decides:

- what work exists
- what work is allowed
- what worker should handle it
- what requires approval
- what state should be persisted

Workers decide:

- how to execute an assigned task within the allowed boundary

Codex is a powerful execution engine inside the system, but it is not the system.

## Core Roles

### 1. The Platform

The platform is the operating system.

It owns:

- goal intake
- task creation
- routing
- persistence
- queueing
- approval state
- policies
- auditability
- runtime coordination

It must not outsource those responsibilities to Codex or OpenClaw.

### 2. The Supervisor Worker

The supervisor is the coordination worker.

It is responsible for:

- inspecting goals and current state
- decomposing goals into tasks
- prioritizing work
- selecting worker lanes
- escalating risky actions for approval
- summarizing progress and blockers

It should not directly mutate repos or perform specialist delivery work.

### 3. The Engineering Worker

The engineering worker handles general software implementation tasks.

It is responsible for:

- preparing engineering task packets
- syncing repos
- creating isolated worktrees
- calling Codex CLI
- validating diffs
- running lint, tests, and builds
- preparing commits and PR-ready outputs
- reporting structured results back to the platform

It must not:

- define product strategy
- bypass approval policy
- own release policy
- own deployment policy

### 4. The iOS Worker

The iOS worker handles iOS-specific product implementation.

It is responsible for:

- processing iOS bugfix and feature tasks
- invoking Codex for iOS code changes
- running Xcode and simulator workflows
- performing iOS-specific validation
- preparing build artifacts
- handing release-ready work to the App Store lane

It is separate from the general engineering worker because iOS has distinct build, signing, packaging, and simulator concerns.

### 5. The App Store Worker

The App Store worker handles release operations.

It is responsible for:

- preparing TestFlight state
- drafting release notes and metadata
- managing screenshots and localization assets
- interacting with App Store Connect
- drafting review responses
- requesting human approval before final submission or release

It must remain separate from the iOS implementation lane.

### 6. Future Workers

Possible future lanes include:

- support
- growth
- research
- ops

Each should be narrow in scope, schema-driven, and policy-bound.

## Codex's Role

Codex is the engineering engine, not the operating system.

Codex is responsible for:

- editing code
- generating implementation drafts
- applying bugfixes and feature work
- assisting with tests and refactors
- operating inside isolated worktrees
- returning results that can be validated

Codex is not responsible for:

- defining architecture policy
- deciding what tasks matter
- deciding what is safe to automate
- storing durable system state
- controlling approvals
- owning release strategy

In short:

- Codex writes code.
- The platform decides what code should be written and under what constraints.

## OpenClaw's Role

OpenClaw is optional and external to orchestration.

It may later be used for:

- founder chat
- remote commands
- notifications
- approvals
- high-level status checks

It must not own:

- orchestration
- queue state
- durable memory
- repo lifecycle
- worker routing
- approval policy
- business logic

If an OpenClaw bridge is added later, it should adapt into platform APIs instead of replacing them.

## Worker Design Rules

Every worker should follow these rules:

1. Single lane of responsibility
2. Structured input through typed task payloads
3. Structured output with status, artifacts, and next-step signals
4. No hidden authority beyond assigned policy
5. No policy ownership
6. Observable execution with logs and audit trails

## Approval Boundaries

Examples usually safe to automate:

- creating tasks
- drafting implementation plans
- creating worktrees
- running tests
- preparing PRs
- drafting release notes
- preparing screenshots

Examples that usually require approval:

- merging to protected branches
- production deploys
- destructive database operations
- billing changes
- App Store submission
- App Review responses
- pricing changes
- security-sensitive config changes
- domain or DNS changes
- large spend changes

Approval rules should live in shared policy code and be enforced consistently across workers.

## Repo Rules For New Workers

When adding a new worker lane, include:

- clear scope
- clear task types
- shared schema usage
- policy integration
- structured output
- documentation updates

Preferred structure:

- `apps/worker-<name>/`
- reusable helpers in `packages/tools/` only when genuinely shared
- schema changes in `packages/schemas/`
- policy hooks in `packages/policies/`

Avoid:

- broad catch-all workers
- hidden behavior living only in prompts
- duplicating policy logic inside workers
- mixing runtime state into source folders

## Runtime State Rules

Runtime state belongs under `state/`.

This includes:

- cloned repos
- worktrees
- generated artifacts
- logs
- checkpoints
- temporary outputs

Do not store runtime-generated state in source directories unless there is a very specific reason.

## Product Workspace Rules

Managed product source may live under `products/` when the platform is hosting an in-repo product.

When doing this:

- register the product explicitly
- keep product planning artifacts under `docs/products/<product-id>/`
- keep runtime execution under `state/`
- do not hide product requirements only in prompts

## Documentation Rules

When the architecture changes materially, update:

- `README.md`
- `AGENTS.md`
- `docs/architecture.md`
- any additional architecture or decision docs introduced later

## Success Criteria

This system is successful when:

- goals become structured tasks
- tasks are routed to specialized workers
- workers execute within bounded responsibilities
- Codex performs implementation inside controlled lanes
- approvals gate irreversible actions
- iOS and App Store workflows remain cleanly separated
- OpenClaw can plug in later without taking over orchestration

## Summary

The intended model is simple:

- the platform is the brain
- the supervisor coordinates
- workers specialize
- Codex engineers
- policies govern
- state persists
- OpenClaw interfaces

Future implementation should preserve those boundaries.
