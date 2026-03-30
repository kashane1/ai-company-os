---
description: Decompose a founder goal into structured, routable worker tasks. Run this when a new goal needs to be broken into concrete engineering, iOS, or App Store tasks.
canonical_source: skills/canonical/shared/supervisor-goal-decomposition.md
---

# Supervisor Goal Decomposition

You are running the supervisor-goal-decomposition skill from `skills/canonical/shared/supervisor-goal-decomposition.md`. Follow the canonical definition.

## Quick reference

Worker lanes (from AGENTS.md):
- **engineering** — platform code, shared packages, non-iOS repos, Codex-driven
- **ios** — iOS implementation, SwiftUI, SwiftData, Xcode workflows, build artifacts
- **appstore** — TestFlight, metadata, screenshots, App Store Connect

For iOS-only products (e.g. fishing-logbook): route code tasks to `ios`, not `engineering`. Use `engineering` only for platform-level or shared-package work.

Each task targets exactly one lane. If work spans lanes, split into separate tasks.

## Steps

1. Read the goal record (title, description, priority, product context)
2. If product-scoped, load relevant artifacts from `docs/products/<product-id>/`
3. Decompose into concrete tasks — each with: title, summary, target lane, constraints, risk level, dependencies, acceptance criteria
4. Check for anti-patterns: lane-spanning tasks, hidden orchestration, vague scope, missing constraints, approval gaps
5. Order tasks by dependency, annotate parallel opportunities
6. Flag anything requiring founder approval
7. Write decomposition to `state/artifacts/supervisor/<goal-id>-decomposition.md`

## Anti-pattern checklist

Before finalizing, verify:
- [ ] No task spans multiple worker lanes
- [ ] No task embeds coordination instructions ("then tell X to...")
- [ ] Every task has specific file/directory scope
- [ ] Every task has testable acceptance criteria
- [ ] High-risk tasks (merge, deploy, submit) are flagged for approval

## Boundaries

- **May edit**: `state/checkpoints/platform/tasks/`, `state/checkpoints/platform/goals/`, `state/artifacts/supervisor/`
- **Must not touch**: `packages/policies/`, `infra/`, `products/`, `apps/`
- **Do not invent** product scope — flag ambiguities for founder review
