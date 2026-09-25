# After Plans iOS

This directory contains the managed iOS source tree for After Plans.

Current status:

- product registry entry exists
- product docs are the source of truth for scope
- `project.yml` defines the managed XcodeGen project
- the app defaults to in-memory state for offline development; an optional Supabase adapter is implemented
- the shell covers onboarding, discovery, create plan, plan detail, confirmation, profile, activity, invite/share, and safety entrypoints

For a code review, start with [backend selection](Sources/Services/AfterPlansConfiguration.swift),
[the Supabase adapter](Sources/Services/SupabaseBackend.swift), and
[service tests](Tests/Services/). The live Supabase integration test needs a
configured backend and is separate from the offline path. Source presence does
not establish a deployed service or an App Store release.

For product context:

- [docs/products/after-plans/PHASE_STATUS.md](../../docs/products/after-plans/PHASE_STATUS.md)
- [docs/products/after-plans/PRODUCT_BRIEF.md](../../docs/products/after-plans/PRODUCT_BRIEF.md)
- [docs/products/after-plans/MVP_SPEC.md](../../docs/products/after-plans/MVP_SPEC.md)
- [docs/products/after-plans/IOS_ARCHITECTURE.md](../../docs/products/after-plans/IOS_ARCHITECTURE.md)

Scope guardrails:

- do not implement the full social product in one pass
- do not merge iOS implementation and App Store release work
- keep trust and bounded-visibility requirements explicit from the start
- keep backend operations, payments, and App Store release work scoped separately from UI implementation

Current contents:

- `project.yml` to generate `AfterPlans.xcodeproj` with XcodeGen
- a single SwiftUI iPhone app target
- a continuation loop with an offline in-memory backend and optional Supabase adapter
- unit tests for lifecycle, visibility, create-plan validation, and shell state mutations
