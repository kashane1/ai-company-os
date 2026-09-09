# After Plans iOS

This directory contains the managed iOS source tree for After Plans.

Current status (source and local-development evidence, reconciled 2026-09-08):

- registry phase is `mvp-build`; the Phase 7 local-Supabase slice is in progress
- product registry entry exists
- product docs are the source of truth for scope
- `project.yml` defines the managed XcodeGen project
- the app defaults to in-memory state for offline development; an optional
  Supabase adapter has a local integration path
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

## Tests

From the repository root, run the offline/hermetic scheme with an available
simulator:

```bash
./scripts/test_ios.sh --product after-plans
```

The default project deliberately omits the remote `supabase-swift` package, so
the shared command can build and test without network access. The adapter source
remains present behind `canImport(Supabase)` and falls back to the in-memory
backend when the package is absent.

Simulator builds are unsigned and require no Apple development team or local
signing configuration. Verified 2026-09-09 with Xcode 26.6 and an iPhone 17 Pro
simulator on iOS 26.5: **91 total, 88 passed, 0 failed, 3 skipped**. The scheme
now includes a hermetic UI test that completes real onboarding, rejects an
invalid draft, creates an invite-only plan against the in-memory backend, and
checks the dismissed sheet's visible home-card state. It uses no signed-in
account, Supabase endpoint, or key. The three skips are live Supabase integration
tests, which require the explicit local endpoint and key shown below. This run
reported 51.56% app-target line coverage. The result bundle is written to
`build/ios/after-plans.xcresult`.

To run `SupabaseBackendIntegrationTests`, start the local Supabase stack, generate
the separately named integration project, and pass its URL and anon key explicitly:

```bash
cd products/after-plans-ios
xcodegen --spec project-supabase.yml
AFTERPLANS_SUPABASE_URL=http://127.0.0.1:54321 \
AFTERPLANS_SUPABASE_KEY="$LOCAL_SUPABASE_ANON_KEY" \
xcodebuild test \
  -project AfterPlansSupabase.xcodeproj \
  -scheme AfterPlans \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

No Supabase endpoint or key is enabled in the shared scheme.
