# ADR 0001: Foundation Choices

- Status: Accepted
- Date: 2026-03-27

## Context

`ai-company-os` is intended to become a durable operating system for an AI-first or AI-only software company.

Earlier attempts in this problem space tend to fail in predictable ways:

- orchestration gets hidden in prompts
- one oversized agent absorbs too much responsibility
- interface layers become de facto backends
- release and engineering concerns blur together
- runtime state leaks into source code

This ADR records the foundational decisions meant to avoid those failure modes.

## Decisions

### 1. Codex Is The Engineer, Not The Orchestrator

Codex is used for implementation work inside bounded worker lanes.

Codex does not own:

- goal selection
- policy
- routing
- approvals
- durable state

Reason:

- implementation quality benefits from Codex
- system coherence requires orchestration to remain explicit and inspectable

### 2. OpenClaw Is Optional And External

OpenClaw may later provide chat, remote commands, notifications, and approvals.

OpenClaw does not own:

- orchestration
- memory
- queue coordination
- worker control logic

Reason:

- the system should remain coherent even if no chat interface exists
- interface layers should adapt into the platform, not become the platform

### 3. iOS And App Store Lanes Stay Separate

The iOS worker handles implementation and build workflows.

The App Store worker handles distribution and release operations.

Reason:

- building software and shipping software are related but distinct responsibilities
- keeping them separate reduces hidden authority and clarifies approval boundaries

### 4. Runtime State Lives Under `state/`

Repos, worktrees, artifacts, logs, and checkpoints belong under `state/`.

Reason:

- runtime data should be easy to inspect and easy to ignore in source control
- source folders should describe the system, not accumulate operational residue

## Consequences

Positive:

- clearer architecture
- safer automation boundaries
- easier debugging through explicit state
- easier future extension without rewriting core assumptions

Tradeoffs:

- more explicit plumbing up front
- less apparent short-term magic
- some future integrations will require adapters instead of shortcuts

These tradeoffs are acceptable because the goal is a durable operating system, not a fast demo.
