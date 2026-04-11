---
id: ios-ui-polish-review
name: iOS UI Polish Review
purpose: Review an iOS feature implementation for UI polish, consistency, and platform conventions before release readiness.
owner_agent: ios
target_runtimes: [claude]
stage: active
inputs:
  - feature_name or screen_name to review
  - source path within products/fishing-logbook-ios/
  - reference to the relevant mvp-spec acceptance criteria
  - reference to ios-architecture.md for tech constraints
outputs:
  - a review document listing polish issues categorized by severity
  - specific file:line references for each issue
allowed_edit_boundaries:
  - products/fishing-logbook-ios/ (review notes only — do not modify source)
  - state/artifacts/ios/
forbidden_areas:
  - packages/
  - infra/
  - apps/
  - docs/ (read-only reference is fine)
dependencies:
  - ios-architecture.md must exist at docs/products/fishing-logbook/
  - mvp-spec.md must exist at docs/products/fishing-logbook/
  - the target feature code must exist in products/fishing-logbook-ios/
validation_steps:
  - review document exists and contains at least one finding or explicit "no issues found"
  - every finding references a specific file and line number
  - findings are categorized (blocking, should-fix, nice-to-have)
  - review checked all items in the polish checklist below
handoff_contract:
  what_is_handed_off: review document with prioritized findings
  handed_to: engineering or ios worker for fixes
claude_adaptation_notes: |
  Claude runs this skill by reading the SwiftUI source files, comparing
  against the spec and architecture docs, and producing the review document.
  Claude should use screenshots or simulator output when available.
---

## Instructions

### 1. Load context

Read:
- `docs/products/fishing-logbook/mvp-spec.md` for acceptance criteria
- `docs/products/fishing-logbook/ios-architecture.md` for tech constraints
- The target feature source files in `products/fishing-logbook-ios/`

### 2. Run the polish checklist

For each screen or component being reviewed, check:

**Layout and spacing**
- consistent padding and margins
- proper safe area handling
- correct alignment of elements
- no clipped or overflowing content

**Typography**
- consistent font sizes and weights
- proper dynamic type support
- readable contrast ratios

**Colors and theming**
- consistent use of the app color palette
- proper dark mode support if applicable
- no hardcoded color values that bypass the theme

**Interaction**
- tappable areas are at least 44pt
- loading states are handled
- empty states are handled
- error states are handled
- keyboard avoidance works for text inputs

**Platform conventions**
- navigation follows iOS HIG patterns
- system controls used where appropriate (no custom reimplementations of standard iOS components)
- proper use of SwiftUI environment and preferences

**Data display**
- units displayed correctly (weight, length, temperature)
- dates formatted with user locale
- optional fields handled gracefully when empty

### 3. Write the review document

Output a review document with:

```markdown
# iOS UI Polish Review: <feature_name>

## Summary
<one paragraph overview>

## Blocking issues
<issues that must be fixed before release>

## Should-fix issues
<issues that degrade quality but don't block release>

## Nice-to-have improvements
<minor polish items>

## Items checked with no issues
<list of checklist items that passed>
```

Write to `state/artifacts/ios/<feature-name>-polish-review.md`.

### 4. Validate

- Review document exists
- Every finding has a file reference
- All checklist categories were addressed
