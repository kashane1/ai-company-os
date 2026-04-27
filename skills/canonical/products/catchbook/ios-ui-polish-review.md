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

## Severity taxonomy

Use these exact severity labels — the validator and downstream tooling
key off the headings, so divergence breaks parsing.

| Severity | Heading in review doc | Definition |
|----------|------------------------|------------|
| blocking | `## Blocking issues` | Must be fixed before release. Examples: tappable area below 44pt on a primary action, no error state for a network call, content clipped on smallest supported device, accessibility label missing on critical control. |
| should-fix | `## Should-fix issues` | Degrades quality but not a release blocker. Examples: inconsistent spacing across two sister screens, missing dynamic-type support on secondary text, generic empty-state copy that could be more specific. |
| nice-to-have | `## Nice-to-have improvements` | Polish that elevates the experience. Examples: tighter copy, micro-interactions, improved transitions, better dark-mode contrast on non-critical surfaces. |
| no-issues | `## Items checked with no issues` | Explicit confirmation that a checklist category passed. Required to demonstrate full coverage. |

A finding with no severity heading is invalid output. The post-review
worker can refuse to triage findings that lack severity classification.

## Required output template

Every review document MUST include all four severity sections, even if
empty. An empty section is rendered as:

```markdown
## Should-fix issues

_None._
```

This is intentional — it forces the reviewer to confirm coverage
rather than silently omit.

## Failure modes

- **Source files missing.** If a referenced source path does not exist
  in `products/catchbook-ios/`, halt the review and emit a single
  finding under "Blocking issues" naming the missing path. Do NOT
  fabricate findings against guessed file content.
- **No simulator screenshot available.** Many polish checks (clipping,
  dark mode, dynamic type) need visual evidence. If screenshots cannot
  be obtained, the review document must include a top-level note:
  "_Visual checks performed via static-source inspection only;
  re-run with simulator screenshots before release._"
- **Spec-implementation drift.** If the implementation diverges from
  `mvp-spec.md` acceptance criteria, surface as a Blocking issue and
  link to both the spec line and the source line. Do not silently
  re-derive the intended behavior.

## Worked example

For a hypothetical `TripDetailView` review, the output structure would be:

```markdown
# iOS UI Polish Review: TripDetailView

## Summary
TripDetailView meets MVP acceptance criteria. Two blocking issues
(tappable area, missing error state). Three should-fix items around
dynamic-type and locale formatting.

## Blocking issues
- products/catchbook-ios/Catchbook/Trips/TripDetailView.swift:142 —
  Edit button frame is 36×36pt; iOS HIG requires ≥44pt.
- products/catchbook-ios/Catchbook/Trips/TripDetailView.swift:201 —
  No error state for `loadCatches()` failure; user sees indefinite
  spinner.

## Should-fix issues
- products/catchbook-ios/Catchbook/Trips/TripDetailView.swift:78 —
  Date label uses fixed font size 14pt; should respect dynamic type.
- ...

## Nice-to-have improvements
_None._

## Items checked with no issues
- Layout & spacing: padding consistent across detail rows.
- Colors: theme palette honored throughout.
- ...
```

## References

- HIG: https://developer.apple.com/design/human-interface-guidelines/
- Catchbook spec: `docs/products/catchbook/mvp-spec.md`
- iOS architecture: `docs/products/catchbook/ios-architecture.md`
- Sibling handoff skill: `skills/canonical/handoffs/ios-to-appstore-handoff.md`
