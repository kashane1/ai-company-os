---
id: supervisor-goal-decomposition
name: Supervisor Goal Decomposition
purpose: Turn a founder goal into structured, routable worker tasks while preserving worker boundaries and keeping routing legible.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
inputs:
  - goal record (title, description, priority, product context if applicable)
  - current worker lanes available (from AGENTS.md)
  - current product state (from product artifact chain if product-scoped)
outputs:
  - ordered list of typed task records ready for persistence
  - routing annotations (target worker lane per task)
  - dependency graph between tasks (if any)
  - escalation notes (anything requiring founder approval before work begins)
allowed_edit_boundaries:
  - state/checkpoints/platform/tasks/
  - state/checkpoints/platform/goals/
  - state/artifacts/supervisor/
forbidden_areas:
  - packages/policies/
  - packages/schemas/
  - infra/
  - products/
  - apps/
dependencies:
  - AGENTS.md must exist and define current worker lanes
  - docs/architecture.md must define the task flow
  - if product-scoped: product artifact chain should be assessed first (product-artifact-chain skill)
validation_steps:
  - every output task has a single target worker lane
  - no task spans multiple worker lanes
  - every task has a clear objective, constraints list, and risk level
  - no task contains hidden orchestration (no "then coordinate with X" embedded in task body)
  - dependency ordering is acyclic
  - tasks requiring approval are flagged explicitly
handoff_contract:
  what_is_handed_off: typed task records with routing annotations and dependency order
  handed_to: platform for persistence and queue routing
claude_adaptation_notes: |
  Claude is the natural runtime for this skill. The supervisor uses Claude to
  inspect a goal, reason about decomposition, and produce structured task output.
  The adapter should provide a streamlined decomposition checklist and output
  format template.
---

## Instructions

### 1. Load the goal

Read the goal record. Extract title, description, priority, and product context.

If the goal references a managed product, load the product's current artifact chain state from `docs/products/<product-id>/`. Run the product-artifact-chain skill first if you have not assessed the chain in this session.

### 2. Identify the worker lanes

Reference `AGENTS.md` for the current worker boundaries:

- **engineering**: code changes, tests, builds, Codex-driven implementation (platform code, shared packages, non-iOS repos)
- **ios**: iOS-specific implementation, Xcode workflows, build artifacts (SwiftUI views, SwiftData models, iOS-native features)
- **appstore**: TestFlight, metadata, screenshots, App Store Connect, release management

**Lane selection for iOS products**: For an iOS-only product like fishing-logbook, most code tasks route to `ios`, not `engineering`. Use `engineering` only for platform-level or shared-package work. Use `ios` for anything that lives in `products/<product-id>/` and requires Xcode or iOS-specific knowledge.

Each task must target exactly one lane. If work naturally spans lanes, split into separate tasks with explicit handoff points.

### 3. Decompose into tasks

Break the goal into the smallest set of concrete tasks that fully covers the goal. For each task, define:

| Field | Description |
|-------|-------------|
| `title` | Short imperative title (e.g. "Add trip deletion confirmation dialog") |
| `summary` | 1-3 sentence description of what the task accomplishes |
| `target_lane` | Exactly one of: `engineering`, `ios`, `appstore` |
| `constraints` | Explicit boundaries — for code tasks: files to touch, files to avoid, patterns to follow; for non-code tasks (appstore, positioning): artifact inputs, output format expectations, what not to invent |
| `risk_level` | `low` (safe to automate), `medium` (review before merge), `high` (requires approval) |
| `depends_on` | List of task titles this task blocks on, or empty |
| `acceptance` | Concrete criteria for task completion |

### 4. Check for anti-patterns

Before finalizing, verify the decomposition avoids these:

- **Lane-spanning tasks**: A single task should not ask engineering to "implement and then prepare the App Store listing." Split it.
- **Hidden orchestration**: Task instructions must not embed coordination logic like "after this, tell the iOS worker to..." — that is the platform's job.
- **Vague scope**: "Improve the UI" is not a task. "Add loading states to the trip list screen per mvp-spec.md acceptance criteria" is.
- **Missing constraints**: Every task touching code must specify which files/directories are in scope.
- **Approval gaps**: Any task that merges to a protected branch, deploys, or submits to App Store must be flagged `high` risk.

### 5. Order and annotate

Produce a final ordered list respecting dependency edges. Annotate:

- Which tasks can run in parallel (no dependency edges between them)
- Which tasks form a critical path
- Which tasks require founder approval before starting

### 6. Escalate uncertainties

If the goal is ambiguous, under-specified, or implies work outside current worker capabilities:

- Do not invent scope — flag the ambiguity
- Produce the decomposition for the parts that are clear
- List specific questions for the founder alongside the task list

### 7. Produce output

Write the decomposition to `state/artifacts/supervisor/<goal-id>-decomposition.md` containing:

1. **Goal summary** (one line)
2. **Task list** (table with all fields from step 3)
3. **Dependency graph** (text or list form)
4. **Parallel execution opportunities**
5. **Escalation notes** (if any)
6. **Approval gates** (which tasks need approval and why)

### Output format template

```markdown
# Goal Decomposition: <goal title>

## Goal
<one-line summary>

## Tasks

| # | Title | Summary | Lane | Risk | Constraints | Depends On | Acceptance |
|---|-------|---------|------|------|-------------|------------|------------|
| 1 | ...   | ...     | ...  | ...  | ...         | —          | ...        |
| 2 | ...   | ...     | ...  | ...  | ...         | 1          | ...        |

## Dependency Order
1. Task 1 (no dependencies — can start immediately)
2. Task 2 (blocked by: Task 1)
3. Tasks 3, 4 (parallel — no mutual dependency)

## Escalation Notes
- <any ambiguities or founder decisions needed>

## Approval Gates
- Task N requires approval because: <reason>
```
