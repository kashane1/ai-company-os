---
description: Prepare the handoff from iOS implementation to App Store release operations. Run this when a build is ready for TestFlight or submission.
canonical_source: skills/canonical/handoffs/ios-to-appstore-handoff.md
---

# iOS to App Store Handoff

You are running the ios-to-appstore-handoff skill from `skills/canonical/handoffs/ios-to-appstore-handoff.md`. Follow the canonical definition.

## Build readiness checklist

Confirm before proceeding:

- [ ] Build compiles without errors
- [ ] All tests pass
- [ ] Xcode archive succeeds
- [ ] Version and build number set correctly
- [ ] No debug flags in release scheme

## Steps

1. Walk through the build readiness checklist with the user
2. Create a feature manifest (new features, fixes, known issues, deferrals)
3. Read `docs/products/<product-id>/app-store-positioning.md`
4. Draft release notes and metadata updates
5. Write metadata draft to `state/artifacts/appstore/<product-id>-<version>-metadata-draft.md`
6. Create release candidate record at `state/checkpoints/platform/releases/<product-id>-<version>.json`
7. Confirm handoff: build validated, record exists, metadata ready

## Boundaries

- **May edit**: `state/artifacts/ios/`, `state/artifacts/appstore/`, `state/checkpoints/platform/releases/`
- **Must not modify**: `products/` source code, `packages/policies/`, `infra/`
- **Read-only**: `docs/products/`, `products/fishing-logbook-ios/` (for version info)
