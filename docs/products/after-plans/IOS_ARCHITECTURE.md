# iOS Architecture: After Plans

## Implementation Baseline

- UI framework: SwiftUI
- target device: iPhone first
- architecture style: feature-oriented SwiftUI with clear service protocols
- state approach: app shell plus feature-local view models or reducers
- release boundary: App Store metadata and submission stay outside this lane

## Product Architecture Stance

The iOS lane should first build a clean shell around the continuation loop, not the full social system.

That means:

- client contracts and feature modules first
- stubbed services are acceptable early
- trust and visibility states must be first-class in the UI model
- chat, public discovery, and premium layers stay out of scope

## Suggested Module Layout

- `Sources/App/`
- `Sources/Features/Onboarding/`
- `Sources/Features/Home/`
- `Sources/Features/ContextSelection/`
- `Sources/Features/PlanDetail/`
- `Sources/Features/CreatePlan/`
- `Sources/Features/Confirmation/`
- `Sources/Features/InviteShare/`
- `Sources/Features/Profile/`
- `Sources/Features/Safety/`
- `Sources/Models/`
- `Sources/Services/`
- `Sources/Shared/UI/`
- `Tests/`

## Core Service Protocols

The first shell should define these interfaces even if the initial backing implementations are mock or in-memory:

- `AuthService`
- `ProfileService`
- `ContextService`
- `DiscoveryFeedService`
- `PlanComposerService`
- `PlanParticipationService`
- `InviteService`
- `SafetyService`
- `AnalyticsService`

## UI Flow Priorities

1. onboarding
2. context selection
3. home feed
4. create plan
5. plan detail
6. confirmation room
7. invite/share
8. safety center

## State And Navigation Rules

- the app should always know the current context anchor or why none is selected
- plan cards should surface trust cues, visibility mode, and momentum clearly
- the create flow should branch into three plan modes without becoming a wizard maze
- the confirmation room should feel like convergence, not chat

## Trust And Privacy Requirements

- no anonymous participation state in the client
- location permission should be requested only when it improves relevance for context or place selection
- visibility mode should be shown wherever it affects who can see or join a plan
- block and report actions must be reachable from plan and profile surfaces

## Testing Expectations

When Phase 4 begins and logic-bearing Swift files are added under `products/after-plans-ios/Sources/`, lane-matching tests must ship under `products/after-plans-ios/Tests/` per repo policy.

Initial iOS test targets should cover:

- lifecycle state transitions
- ranking presentation logic
- visibility gating
- create-plan validation
- safety action handling

## Deferred Decisions

- final persistence and sync model
- final networking stack
- live venue suggestion integration
- handoff-to-text implementation details
- any rich messaging layer

## Product Source Of Truth

Before iOS implementation starts, read:

- `PRODUCT_BRIEF.md`
- `PRD.md`
- `MVP_SPEC.md`
- `SCREEN_MAP.md`
- `DATA_MODEL.md`
- `TRUST_SAFETY_GUARDRAILS.md`
