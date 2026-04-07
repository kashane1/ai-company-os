# After Plans iOS

This directory contains the managed iOS source tree for After Plans.

Current status:

- product registry entry exists
- product docs are the source of truth for scope
- `project.yml` defines the managed XcodeGen project
- the app currently ships a compile-safe SwiftUI shell backed by in-memory sample state
- the shell covers onboarding, discovery, create plan, plan detail, confirmation, profile, activity, invite/share, and safety entrypoints

Read these first before starting Phase 4 or any iOS build work:

- `docs/products/after-plans/PHASE_STATUS.md`
- `docs/products/after-plans/PRODUCT_BRIEF.md`
- `docs/products/after-plans/MVP_SPEC.md`
- `docs/products/after-plans/IOS_ARCHITECTURE.md`

Scope guardrails:

- do not implement the full social product in one pass
- do not merge iOS implementation and App Store release work
- keep trust and bounded-visibility requirements explicit from the start
- keep backend ranking, moderation operations, messaging, payments, and App Store work out of this source tree until explicitly scheduled

Current contents:

- `project.yml` for `xcodegen`
- generated `AfterPlans.xcodeproj`
- a single SwiftUI iPhone app target
- an in-memory continuation-loop shell for seeded MVP development
- unit tests for lifecycle, visibility, create-plan validation, and shell state mutations
