---
description: Review iOS feature code for UI polish, consistency, and platform conventions. Run this before marking a feature as release-ready.
canonical_source: skills/canonical/products/fishing-logbook/ios-ui-polish-review.md
---

# iOS UI Polish Review

You are running the ios-ui-polish-review skill from `skills/canonical/products/fishing-logbook/ios-ui-polish-review.md`. Follow the canonical definition.

## Context to load

- `docs/products/fishing-logbook/mvp-spec.md` — acceptance criteria
- `docs/products/fishing-logbook/ios-architecture.md` — tech constraints
- Target feature source files in `products/fishing-logbook-ios/`

## Polish checklist

Review each screen/component against:

1. **Layout**: padding, margins, safe areas, alignment, no clipping
2. **Typography**: consistent sizes/weights, dynamic type, contrast
3. **Colors**: palette consistency, dark mode, no hardcoded colors
4. **Interaction**: 44pt tap targets, loading/empty/error states, keyboard avoidance
5. **Platform conventions**: iOS HIG, system controls, SwiftUI environment
6. **Data display**: correct units, locale-aware dates, graceful empty optionals

## Output format

Write review to `state/artifacts/ios/<feature-name>-polish-review.md`:

```
# iOS UI Polish Review: <feature>
## Summary
## Blocking issues (must fix before release)
## Should-fix issues
## Nice-to-have improvements
## Items checked with no issues
```

Every finding must include a file:line reference.

## Boundaries

- **May write**: `state/artifacts/ios/` only
- **May read**: `products/fishing-logbook-ios/`, `docs/products/fishing-logbook/`
- **Must not modify**: source code (review only)
