# Start Here For Claude: After Plans

This file is the bootloader for a brand new Claude instance working inside `ai-company-os` on the After Plans product.

Use it when Claude needs to start useful work quickly without re-deriving the repo architecture, the product wedge, or the current phase boundary.

## What This Repo Is

`ai-company-os` is a local-first, policy-driven platform for running an AI-driven software business.

Non-negotiable repo rules:

- the platform owns orchestration
- workers specialize by lane
- policy lives in shared code, not hidden prompt behavior
- runtime state belongs under `state/`
- product artifacts belong under `docs/products/<product-id>/`
- product source belongs under `products/<product-id>/`
- iOS implementation and App Store release work are separate lanes

Claude is not here to redesign the operating system. Claude is here to execute a bounded task inside the existing product and repo structure.

## What After Plans Is

After Plans is an iPhone-first social continuation app for the moment right after a real-world activity, when people are still nearby, shared context is fresh, and the next plan often dies from awkwardness or coordination friction.

The v1 wedge:

- post-activity continuation
- join-first social coordination
- low-pressure participation
- bounded-context trust
- free consumer core

The core product promise:

- make the next plan easier right after the current one ends

## What After Plans Is Not

Do not drift the product into any of the following:

- event planning platform
- broad social network
- anonymous meetup app
- dating product
- group chat replacement
- payments or ticketing system
- organizer CRM
- public map-wide discovery

Shared context, known people, and prior plan partners should outrank strangers. Identity should stay lightweight but not anonymous.

## Current Project State

After Plans is currently in Phase 6.

What is already true:

- the managed product docs exist under `docs/products/after-plans/`
- the managed iOS source tree exists under `products/after-plans-ios/`
- the app is a compile-safe SwiftUI shell backed by in-memory state
- the continuation loop, trust cues, lifecycle clarity, invite/share scaffolding, and recap/social-memory surfaces have already been deepened
- lane-matching unit tests already exist for the current logic-bearing areas

Default next-step posture:

- continue with one narrow Phase 6 refinement
- prefer app-layer improvements over architecture changes
- preserve the in-memory shell unless explicitly tasked otherwise
- avoid backend, chat, premium, notifications, release operations, and cross-lane redesign

## Claude's Role

Claude should operate like a bounded product implementation partner.

Claude should:

- inspect first
- use the existing docs as source of truth
- implement one narrow slice at a time
- preserve repo boundaries and lane separation
- add or update lane-matching tests for logic-bearing changes
- report clearly what changed, what was validated, and what remains

Claude should not:

- invent a new architecture for the whole repo
- widen product scope
- merge iOS work with App Store work
- add backend systems unless the task explicitly requires it
- replace repo conventions with Claude-specific structure

## Read Order For A Fresh Claude Instance

Read these files in order before proposing changes:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/products/after-plans/PHASE_STATUS.md`
4. `docs/products/after-plans/README.md`
5. `docs/products/after-plans/FOUNDER_BRIEF.md`
6. `docs/products/after-plans/MVP_SPEC.md`
7. `docs/products/after-plans/IOS_ARCHITECTURE.md`
8. `docs/products/after-plans/RESUME_PROMPT.md`
9. `state/artifacts/after-plans/codex-append-log.md`

Then inspect the live app files that match the task:

- `products/after-plans-ios/Sources/App/ContinuationLoop.swift`
- `products/after-plans-ios/Sources/App/AfterPlansStore.swift`
- `products/after-plans-ios/Sources/Models/AfterPlansModels.swift`
- relevant feature views under `products/after-plans-ios/Sources/Features/`
- matching tests under `products/after-plans-ios/Tests/`

## Working Rules

### Repo Boundaries

- keep product docs under `docs/products/after-plans/`
- keep iOS code under `products/after-plans-ios/`
- keep runtime notes and append-only execution logs under `state/artifacts/after-plans/`

### Product Guardrails

- joining should feel easier than creating
- the feed should feel like "people you know or were just around"
- trust and bounded visibility must be explicit
- confirmation should feel like convergence, not chat
- do not make the product feel like anonymous stranger discovery

### Implementation Guardrails

- preserve the feature-oriented SwiftUI shell
- preserve service protocols and in-memory implementations unless the task explicitly widens scope
- keep trust/safety entrypoints reachable
- prefer derived state and small view-model logic over broad rewrites
- avoid speculative abstractions

### Testing Guardrails

- logic-bearing Swift changes under `products/after-plans-ios/Sources/` need lane-matching tests under `products/after-plans-ios/Tests/`
- targeted validation is preferred after each narrow slice
- use broader test reruns when the touched area or wiring risk justifies it

## Preferred Response Format

When Claude finishes a task, the response should be compact and operational:

1. what changed
2. what files were touched
3. what tests or validation ran
4. any open questions, follow-ups, or risks

If Claude is asked to plan before implementing, the plan should still stay narrow and phase-aware.

## Good Task Shapes For Claude

Good:

- tighten onboarding copy or flow inside the existing continuation loop
- refine feed trust cues, ranking presentation, or lifecycle clarity
- improve profile, activity, or invite/share surfaces without widening the product
- add tests for a narrow logic slice
- update product docs when implementation changes the source of truth

Bad:

- build the full backend
- add chat or DMs
- add payments or subscriptions
- redesign the multi-worker operating system
- perform App Store submission work from the iOS lane

## Paste-Ready Prompt A: Bounded Feature Implementation

Use this prompt when you want Claude to implement the next narrow slice inside the existing After Plans iOS app:

```text
You are working inside /Users/simons/ai-company-os on the After Plans product.

Before making changes, read these files in order:
- AGENTS.md
- CLAUDE.md
- docs/products/after-plans/START_HERE_FOR_CLAUDE.md
- docs/products/after-plans/PHASE_STATUS.md
- docs/products/after-plans/MVP_SPEC.md
- docs/products/after-plans/IOS_ARCHITECTURE.md
- docs/products/after-plans/RESUME_PROMPT.md
- state/artifacts/after-plans/codex-append-log.md

Then inspect the relevant live code in:
- products/after-plans-ios/Sources/App/
- products/after-plans-ios/Sources/Models/
- products/after-plans-ios/Sources/Features/
- products/after-plans-ios/Tests/

Work inside the existing managed product boundary. Do not redesign the repo, do not widen scope into backend/chat/payments/public discovery, and do not merge iOS implementation with App Store work.

Product guardrails:
- After Plans is a join-first post-activity continuation app
- shared context, known people, and prior plan partners outrank strangers
- trust and bounded visibility must stay explicit
- the product must not drift toward dating, anonymous meetup, or generic social networking

Task:
[INSERT ONE NARROW PHASE 6 SLICE HERE]

Requirements:
- inspect first, then implement
- preserve the in-memory SwiftUI shell unless the task explicitly says otherwise
- keep the change narrow and phase-aware
- add or update lane-matching tests for any logic-bearing code change
- run appropriate validation for the touched area

Return:
1. a short summary of the change
2. the files you modified
3. the tests/validation you ran
4. any follow-up recommendations
```

## Paste-Ready Prompt B: UI Polish Or Product-Fit Pass

Use this prompt when you want Claude to refine an existing surface without widening the feature set:

```text
You are working inside /Users/simons/ai-company-os on the After Plans iOS app.

Read first:
- docs/products/after-plans/START_HERE_FOR_CLAUDE.md
- docs/products/after-plans/PHASE_STATUS.md
- docs/products/after-plans/FOUNDER_BRIEF.md
- docs/products/after-plans/MVP_SPEC.md
- docs/products/after-plans/SCREEN_MAP.md
- docs/products/after-plans/IOS_ARCHITECTURE.md

Then inspect the relevant SwiftUI files and their tests.

Your job is to improve one existing surface so it better matches the product wedge:
- join-first
- low-pressure
- bounded-context
- trust-aware
- continuation, not broad social discovery

Do not add unrelated features. Do not redesign the app architecture. Do not widen into backend, messaging, payments, or release work.

Focus surface:
[INSERT SURFACE, SUCH AS HOME, ACTIVITY, ONBOARDING, PROFILE, OR INVITE/SHARE]

Goals:
[INSERT 2-4 SPECIFIC GOALS]

Requirements:
- keep the pass narrow
- preserve existing repo conventions
- keep trust, visibility, and lifecycle clarity explicit where relevant
- add or update tests if logic changes
- report validation results clearly

Return:
1. what you changed and why it better fits After Plans
2. files modified
3. tests/validation run
4. any residual product or UX risks
```

## Optional Prompt C: Handoff Reconciliation

Use this when Claude has finished a slice and should leave a clean resume boundary for the next agent:

```text
Summarize the current After Plans state after your changes.

Update, if needed:
- docs/products/after-plans/PHASE_STATUS.md
- docs/products/after-plans/RESUME_PROMPT.md
- state/artifacts/after-plans/codex-append-log.md

Only make updates that reflect the real work completed. Keep the notes append-only where appropriate. Preserve the current repo conventions and phase framing.
```

## Recommendation

If you only use one thing from this file, use Prompt A plus a single narrow task. That is the safest and most productive way to start a new Claude instance in this repo.
