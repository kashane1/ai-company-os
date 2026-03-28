# Codex Worker

This document explains how Codex should fit into the engineering lane.

## Role

Codex is the engineering engine inside the worker system.

It is used for:

- code editing
- implementation drafts
- bugfixes
- refactors
- test updates
- implementation summaries

It is not used for:

- orchestration
- policy definition
- approval decisions
- durable memory
- queue routing

## Expected Flow

The engineering worker should wrap Codex in a controlled sequence:

1. load a typed task
2. prepare repo context
3. create or select an isolated worktree
4. render a task packet with constraints
5. invoke Codex CLI
6. inspect the resulting diff
7. run lint, tests, and builds
8. prepare PR output and structured results

The worker owns the operational wrapper. Codex owns the code-writing step.

## Shared Tooling

V1 should keep Codex-facing helpers under `packages/tools/codex_tools/`.

That namespace is the right home for:

- CLI invocation
- task packet rendering
- output parsing
- safety checks

This keeps Codex integration consistent across engineering and iOS lanes.

## Safety Expectations

Codex should always run under explicit constraints:

- task scope
- repo target
- worktree path
- approval boundaries
- validation requirements

The system should reject unsafe plans rather than assuming the model will self-limit.
