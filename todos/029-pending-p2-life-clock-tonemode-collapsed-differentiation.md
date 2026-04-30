---
status: pending
priority: p2
issue_id: "029"
tags: [code-review, life-clock, ios, simplicity, ux]
dependencies: []
---

# Problem Statement

The UX audit copy refresh collapsed `ToneMode` differentiation. Several tones now produce identical strings, making the enum dispatch dead code in those properties.

## Findings

In `products/life-clock-ios/Sources/App/ToneMode.swift`:

- `todayHeadline`: `.coach` and `.mementoMori` both return "Today's progress"
- `deltaPositivePrefix`: `.coach` and `.mementoMori` both return "Progress today"
- `deltaNegativePrefix`: `.coach` and `.mementoMori` both return roughly the same intent
- `ledgerTitle`: all three tones return "Progress" — full collapse
- `questsTitle`: `.coach` and `.mementoMori` both return "Plan"

The `.mementoMori` case had its display name changed to "Direct" — suggesting the original "memento mori" concept is being abandoned but the case wasn't deleted.

## Proposed Solutions

### Option 1 (recommended): Delete `.mementoMori` and collapse `ledgerTitle`

If the product no longer wants mortality-framed copy, delete the case entirely. Inline `ledgerTitle` to a literal "Progress" since all tones agree.

Pros: removes ~30 lines of dead branching; UI tests get simpler; less surface to keep coherent.
Cons: rawValue migration for any user with `toneMode = "memento_mori"` saved — fall back to `.coach` on read.
Effort: Small.
Risk: Low (guarded by rawValue fallback in UserProfile read path).

### Option 2: Restore differentiation

If the product wants three tones, give each meaningfully distinct strings across all properties. Otherwise the enum is misleading.

Pros: keeps optionality.
Cons: requires product-direction decision; risks reintroducing mortality framing the audit explicitly removed.
Effort: Medium (copy work).
Risk: Low.

### Option 3: Collapse to two tones (`.gentle`, `.coach`)

Keep `.gentle` as the soft option, `.coach` as default. Drop `.mementoMori`.

Pros: simpler than Option 1 if some "Direct"-style copy is wanted in `.coach` already.
Cons: same migration concern.
Effort: Small.
Risk: Low.

## Recommended Action

(leave blank for triage; this needs a product call)

## Technical Details

- Affected files: `ToneMode.swift`, `OnboardingView.swift` (tone picker), `UserProfile` migration path.
- Persistence: `UserProfile.toneMode: String` — handle legacy value `"memento_mori"` by mapping to default on next read.

## Acceptance Criteria

- [ ] No `ToneMode` property returns identical strings across all cases (or the property is deleted).
- [ ] Any removed case has a documented migration path for stored values.
- [ ] Onboarding tone picker still works.

## Work Log

(to be filled in)

## Resources

- Code-simplicity review (this audit), 2026-04-30
