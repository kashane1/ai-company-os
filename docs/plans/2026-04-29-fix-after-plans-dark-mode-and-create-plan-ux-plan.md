---
title: "fix: After Plans dark mode + onboarding pills + create-plan UX"
type: fix
status: active
date: 2026-04-29
origin: docs/plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md
deepened: 2026-04-29
---

# fix: After Plans dark mode + onboarding pills + create-plan UX

## Enhancement Summary

**Deepened on:** 2026-04-29
**Sections enhanced:** 4 (one per issue) + cross-cutting test/QA notes
**Research agents used:** best-practices-researcher (×3 — dark mode, FlowLayout, Form UX), learnings-researcher

### Key improvements from research

1. **Dark mode token strategy is now opinionated.** Use `Color(uiColor: .systemGroupedBackground)` for chrome and **Asset Catalog Color Sets with Any/Dark variants** for brand tokens — not a one-size-fits-all swap. Translucent `.white.opacity(0.84)` is the canonical dark-mode trap and needs a hard replacement, not a tweak.
2. **Issue #3 is a documented anti-pattern.** [docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md](docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md) names this exact failure: "the new capability is gated behind the old requirement it was supposed to eliminate." Carrying that lesson forward — relax all enforcement sites of the old rule in one go, don't just patch the toolbar gate.
3. **Visibility belongs early in the form**, not buried mid-page. Confirmed against Apple HIG, Airbnb, Partiful conventions; Eventbrite is the cited counter-example. This reverses one ambiguity in the original plan (which had visibility *after* core details).
4. **Concrete `FlowLayout.swift`** body is now in the plan — ~75 lines, no dependency, with a measured-cache that only re-flows on width change. Avoids the most common pitfall (recursive `sizeThatFits` deadlock by passing parent proposal to children).
5. **Validation pattern updated** — keep Publish *enabled*, scroll to first invalid section on tap, show inline red footer text. Matches Apple Reminders/Calendar. Cleaner than the current "disabled with footnote orange text".

### New considerations discovered

- Verify `TARGETED_DEVICE_FAMILY = "1"` (iPhone-only) before assuming layout fixes will solve "looks cramped on iPad" reports — cross-reference with [docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md](docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md).
- Animation glitches with conditional `Section`s in `Form` — needs `.animation(.default, value: visibility)` or sections pop in abruptly.
- Focus loss when a `TextField` lives in a section that gets removed/re-added; mitigated here because we don't toggle TextFields across visibility changes.
- Brand accent (#1F63C7-ish) passes 4.5:1 against white as a fill, but as foreground text on `systemBackground` (dark), mid-blues fail — only matters if we ever use accent for body text (we don't currently).

## Overview

Bundled UI/UX fix for four user-reported issues in `products/after-plans-ios/` discovered while exercising the app post context-model refactor:

1. **Dark mode is unreadable** — fixed light-mode surface colors in `DesignTokens.swift` don't adapt to system color scheme; in dark mode the app renders adaptive `.primary`/`.secondary` text on near-white card backgrounds.
2. **Onboarding activity picker is a horizontal scroll bar of ~33 pills** — fails as a "pick the things you do regularly" surface; users can't see the full taxonomy at once.
3. **Public plan publish is blocked when only a freeform place is provided** — validation in `CreatePlanDraft.validationMessage` requires `venueID != nil`, but the form has no UI to set `venueID` (no `MKLocalSearchCompleter` typeahead). The store already materializes a freeform venue at publish time, so the gate is wrong.
4. **CreatePlan screen flow** — header reads "Start What's Next" instead of the requested "Plan What's Next"; section ordering puts "Plan mode" before the title and buries visibility/place mid-form, hurting scan-ability.

All four are scoped to four files. Targeting one PR.

## Problem Statement / Motivation

Issues 1–3 are user-blocking (1 makes the app unusable for dark-mode users; 3 makes public plans uncreatable). Issue 4 is polish but landed alongside the rest of the refactor work and the user has explicitly requested the rename.

These issues surfaced during user testing of the context-model refactor (see [docs/plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md](docs/plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md), which introduced public plans, the activity+venue model, and the freeform place fallback). #3 in particular is a regression: the refactor wired publish-time freeform venue creation in the store but left UI validation requiring a venue ID that the UI cannot produce.

## Proposed Solution

### Issue 1 — Dark mode legibility

Replace fixed-RGB surface tokens in [products/after-plans-ios/Sources/Shared/UI/DesignTokens.swift:5-13](products/after-plans-ios/Sources/Shared/UI/DesignTokens.swift) with semantic, adaptive colors. Two paths:

- **Path A (preferred — minimal, no asset edits):** map surface tokens to UIKit dynamic colors via `Color(uiColor:)`:
  - `appBackground` → `Color(uiColor: .systemGroupedBackground)`
  - `appCard` → `Color(uiColor: .secondarySystemGroupedBackground)` (drop the `.opacity(0.84)` — it was solving for layered translucency on a fixed white base)
  - `appCardStrong` → `Color(uiColor: .secondarySystemGroupedBackground)` (or `.tertiarySystemGroupedBackground` if a brighter contrast tier is wanted)
  - `appBorder` → `Color(uiColor: .separator)`
- **Path B (asset catalog):** add Color Sets to `Assets.xcassets` with explicit Any/Dark Appearance hex values. More work, more design control. Defer unless Path A produces a tone the user dislikes after a dark-mode walk-through.

Brand colors (`appAccent`, `appMomentum`, `appSafe`) are foreground tints on tinted backgrounds (`.opacity(0.12)`) and read fine in both schemes — leave unchanged.

Audit the four other hardcoded `Color.white` / `Color.black.opacity(...)` usages outside DesignTokens:
- [HomeView.swift:73](products/after-plans-ios/Sources/Features/Home/HomeView.swift) — `Color.black.opacity(0.055)` in Circle background; switch to `Color(uiColor: .quaternarySystemFill)`.
- [DesignTokens.swift:163](products/after-plans-ios/Sources/Shared/UI/DesignTokens.swift) — `ActionPillButtonStyle` non-prominent fill uses `Color.black.opacity(0.055/0.09)`; switch to `Color(uiColor: .secondarySystemFill)`.
- [DesignTokens.swift:166](products/after-plans-ios/Sources/Shared/UI/DesignTokens.swift) — `Color.white` for prominent pill foreground is correct (sits on `appAccent` fill); leave.
- [DesignTokens.swift:41](products/after-plans-ios/Sources/Shared/UI/DesignTokens.swift) — surface shadow uses `.black.opacity(0.07)`; in dark mode shadow on dark is invisible, which is fine. Leave.

**Out of scope:** redesigning the visual language for dark mode. Goal here is legibility, not aesthetic parity.

#### Research Insights — Issue 1

**Best practices (carried forward from research):**
- **Two color sources, not one.** Use `Color(uiColor: .systemGroupedBackground)` / `.secondarySystemGroupedBackground` / `.label` / `.secondaryLabel` / `.separator` for *chrome*. Use **Asset Catalog Color Sets** with explicit Any/Dark variants for *brand* tokens. Don't try to express brand colors via UIKit dynamic system colors — they're too gray.
- **Materials (`.regularMaterial`, `.thinMaterial`) are for true overlays only** (sheets, floating bars). Don't substitute them for flat card fills — they pick up whatever's behind, look muddy on a static background, and waste a GPU pass.
- **`Color.white.opacity(0.84)` is the canonical retrofit trap.** It doesn't flip in dark mode. The card stays near-white, body text flips to white via `.primary`, and the result is white-on-white. Hard replace, don't tweak opacity.
- **Shadows of `.black.opacity(0.07)` go invisible in dark mode.** Replace with `Color(uiColor: .label).opacity(0.15)`, OR drop the shadow in dark and substitute a 1pt separator. Both are acceptable.

**Tooling for WCAG AA (4.5:1) verification:**
- Xcode 15+ Accessibility Inspector → Audit → "Run Audit" — flags contrast issues live on simulator. Run once per scheme.
- macOS Digital Color Meter + WebAIM contrast calc for spot checks.

**Brand accent decision:** keep a single `Color("BrandAccent")` asset with Any/Dark variants pre-baked. Don't fork into `brandAccentLight`/`brandAccentDark` in code. For our existing `#1F63C7` accent: passes 4.5:1 against white in light fills (~6.4:1); add a slightly lighter Dark variant (~15-20% lift in L\*) only if we ever use accent for body text on `systemBackground`. We currently don't, so a single token suffices for v1.

**Updated implementation order for Issue 1:**
1. **Create Asset Catalog Color Sets** for `BrandAccent`, `Momentum`, `Safe` (Any + Dark). Quickest path: copy current hex values into Any, add a slightly lighter dark variant (or keep identical for v1).
2. Migrate `appAccent`, `appMomentum`, `appSafe` in `DesignTokens.swift` to `Color("BrandAccent", bundle: .main)` etc.
3. Migrate `appBackground`, `appCard`, `appCardStrong`, `appBorder` to `Color(uiColor: ...)` system equivalents (no asset edits needed for chrome).
4. Update shadow color in `AppSurface` to `Color(uiColor: .label).opacity(0.10)`.
5. Audit + fix three remaining hardcoded `Color.black.opacity(...)` / `Color.white` sites listed below.

**Reference:** Apple HIG — Dark Mode: https://developer.apple.com/design/human-interface-guidelines/dark-mode

### Issue 2 — Onboarding activity picker layout

Replace the `ScrollView(.horizontal)` + `HStack` in [ActivityVenueStepView.swift:22-48](products/after-plans-ios/Sources/Features/Onboarding/Steps/ActivityVenueStepView.swift) with a wrapping flow layout. iOS 16+ ships `Layout` protocol; SwiftUI 4 has no built-in flow container, so two options:

- **Option A (preferred — iOS 16+ stdlib):** use a custom `FlowLayout: Layout` (~40 lines) placed in `Shared/UI/`. Keeps deps zero.
- **Option B:** chunk activities into rows of ~3 in a `VStack` of `HStack`s. Cheaper but visually rigid; pills won't right-size.

Use Option A. Constrain horizontal padding to the parent surface so pills wrap inside the card. Keep the existing pill styling (capsule + accent stroke) — only the container changes.

If the parent `OnboardingView` clips vertically, wrap the step content in `ScrollView(.vertical)` so a tall wrapped grid still scrolls.

#### Research Insights — Issue 2

**Concrete `FlowLayout.swift` body to add to `Sources/Shared/UI/`:**

```swift
import SwiftUI

/// Wraps subviews into rows. Designed for tag/pill pickers.
/// Pass `.unspecified` to children — they size to intrinsic content.
struct FlowLayout: Layout {
    var hSpacing: CGFloat = Spacing.sm
    var vSpacing: CGFloat = Spacing.sm
    var alignment: HorizontalAlignment = .leading

    struct Cache {
        var rows: [[Int]] = []
        var rowSizes: [CGSize] = []
        var totalSize: CGSize = .zero
        var lastWidth: CGFloat = -1
    }

    func makeCache(subviews: Subviews) -> Cache { Cache() }
    func updateCache(_ cache: inout Cache, subviews: Subviews) { cache.lastWidth = -1 }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout Cache) -> CGSize {
        let maxWidth = proposal.replacingUnspecifiedDimensions(
            by: CGSize(width: .infinity, height: .infinity)
        ).width
        compute(maxWidth: maxWidth, subviews: subviews, cache: &cache)
        return cache.totalSize
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout Cache) {
        compute(maxWidth: bounds.width, subviews: subviews, cache: &cache)
        var y = bounds.minY
        for (row, rowSize) in zip(cache.rows, cache.rowSizes) {
            let xStart: CGFloat = {
                switch alignment {
                case .center:   return bounds.minX + (bounds.width - rowSize.width) / 2
                case .trailing: return bounds.minX + (bounds.width - rowSize.width)
                default:        return bounds.minX
                }
            }()
            var x = xStart
            for index in row {
                let sub = subviews[index]
                let size = sub.sizeThatFits(.unspecified)
                sub.place(
                    at: CGPoint(x: x, y: y + (rowSize.height - size.height) / 2),
                    anchor: .topLeading,
                    proposal: ProposedViewSize(size)
                )
                x += size.width + hSpacing
            }
            y += rowSize.height + vSpacing
        }
    }

    private func compute(maxWidth: CGFloat, subviews: Subviews, cache: inout Cache) {
        guard cache.lastWidth != maxWidth else { return }
        cache.lastWidth = maxWidth
        cache.rows.removeAll(keepingCapacity: true)
        cache.rowSizes.removeAll(keepingCapacity: true)

        var currentRow: [Int] = []
        var rowWidth: CGFloat = 0
        var rowHeight: CGFloat = 0
        var totalHeight: CGFloat = 0
        var widestRow: CGFloat = 0

        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let needed = currentRow.isEmpty ? size.width : rowWidth + hSpacing + size.width
            if !currentRow.isEmpty && needed > maxWidth {
                cache.rows.append(currentRow)
                cache.rowSizes.append(CGSize(width: rowWidth, height: rowHeight))
                totalHeight += rowHeight + vSpacing
                widestRow = max(widestRow, rowWidth)
                currentRow = [index]
                rowWidth = size.width
                rowHeight = size.height
            } else {
                currentRow.append(index)
                rowWidth = needed
                rowHeight = max(rowHeight, size.height)
            }
        }
        if !currentRow.isEmpty {
            cache.rows.append(currentRow)
            cache.rowSizes.append(CGSize(width: rowWidth, height: rowHeight))
            totalHeight += rowHeight
            widestRow = max(widestRow, rowWidth)
        }
        cache.totalSize = CGSize(width: min(widestRow, maxWidth), height: totalHeight)
    }
}
```

**Pitfalls actually hit in practice:**
1. **Don't pass parent's proposal to children.** Recursive `subview.sizeThatFits(proposal)` deadlocks measurement when children are flexible. For tag pills, pass `.unspecified` — they size to intrinsic content. The body above does this correctly.
2. **`proposal.width` can be `nil` or `.infinity`** during measurement passes. Always normalize via `replacingUnspecifiedDimensions`.
3. **Cache reflow on width change only** — `lastWidth` guard prevents wasted work in steady state but still re-flows on rotation/size-class change.
4. **Don't apply `.accessibilityElement(children: .contain)`** to FlowLayout — it collapses 33 pills into a single a11y element. Let each pill be its own element with `.isButton` / `.isSelected` traits.
5. **VoiceOver traversal** follows place order, which matches `ForEach` source order. No extra work needed.
6. **RTL** is deferred (English-only app); SwiftUI `Layout` does not auto-flip.

**Verify before optimizing:** check `TARGETED_DEVICE_FAMILY` in `project.yml` is `"1"` (iPhone-only). If somehow set to `"1,2"` and the app is running in iPad compatibility mode, layout fixes won't render correctly — see [docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md](docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md).

**Reference:** Apple — Composing custom layouts: https://developer.apple.com/documentation/swiftui/composing-custom-layouts-with-swiftui

### Issue 3 — Public plan publish unblocked

Two-line fix in [CreatePlanDraft.swift:33-35](products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanDraft.swift): the `venueID != nil` guard becomes `venueID != nil || !trimmedVenueHint.isEmpty`. The store at [AfterPlansStore.swift:417-422](products/after-plans-ios/Sources/App/AfterPlansStore.swift) already creates a freeform venue from `venueHint` and assigns `draft.venueID` before persisting, so this just unblocks the gate that was double-counting the precondition.

Verify by reading `createPlan` end-to-end: the freeform path runs only when `isPublicMatch && draft.venueID == nil && !trimmed.isEmpty`. With the validation relaxed, the empty-hint case stays blocked (no publish), and the freeform case publishes successfully.

**Subtext copy fix while we're here** (issue user quoted): the brainstorm-source copy in [CreatePlanView.swift:97](products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanView.swift) currently reads "A typed place becomes a freeform venue. We'll line it up with a real one when someone confirms the location." That's accurate — keep.

**Future (out of scope):** wire `MKLocalSearchCompleter` typeahead from `VenueSearchService` into the Place section so users can pick a real venue (sets `venueID` directly). The brainstorm calls for this; it's a separate plan.

#### Research Insights — Issue 3

**This is a documented anti-pattern.** [docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md](docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md) names this exactly:

> "The new capability is gated behind the old requirement it was supposed to eliminate."

The pattern: a refactor adds an auto-creation path (here: store materializes a freeform venue at publish time), but the old requirement gate (here: `validationMessage` requires `venueID != nil`) was not removed. Result: the auto-creation runs, but the UI gate blocks the user from ever triggering it — feature is silently dead.

**Lesson carried forward:** before patching the toolbar gate, search for *all* sites enforcing the old "venue required" rule and relax them in one pass. Confirm the new contract: is venue optional now, or does auto-creation guarantee it's never nil at write time? Both are valid; we need to commit to one.

**Decision for this plan:** the new contract is **"venue is required at write time, but the UI accepts either a chosen venueID or a non-empty freeform name; the store materializes the freeform venue on publish."** The validation gate should reflect that contract, not the pre-refactor "user must pick a venueID" contract.

**Audit checklist** (sites enforcing the old rule):
- `CreatePlanDraft.validationMessage` line 33-35 — relax (primary fix).
- `CreatePlanView` — the Publish `.disabled(validationMessage != nil)` is a downstream consumer; no change needed once validation is correct.
- `AfterPlansStore.createPlan` — already correct; freeform path runs when `venueID == nil && !trimmed.isEmpty`.
- Backend `plans.createPlan` — verify it doesn't reject plans with no venueID before the store can materialize one. (Read-only audit; no change expected.)

**Validation UX upgrade (optional, can defer):** current pattern is "Publish disabled + orange validation footnote." Apple HIG 2025 prefers "Publish enabled + scroll-to-first-invalid + inline red footer" (matches Reminders/Calendar). Defer to a follow-up unless we want it in this PR.

### Issue 4 — CreatePlan screen flow

Two parts:

**4a. Header rename** — [CreatePlanView.swift:125](products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanView.swift) `.navigationTitle("Start What's Next")` → `.navigationTitle("Plan What's Next")`. Audit other surfaces for "Start What's Next" copy and align (likely none; verify).

**4b. Section reordering** — current order:
1. Intro blurb
2. Plan mode (Loose / Exact)
3. Core details (title, summary, place, timing)
4. Visibility
5. Visibility-conditional anchor (Context | Activity+Place | nothing)
6. What people will see (preview)
7. Validation message

Two problems with this order:
- "Plan mode" before the user has typed anything is abstract — they don't know what they're picking a mode *for*.
- "Place" appears in Core details *and* in the publicMatch anchor section, so for public plans the user sees two place fields with the same binding — confusing and redundant.

Proposed reorder:
1. Intro blurb
2. **Headline + summary** (was buried in "Core details")
3. **Visibility** (decides what comes next)
4. Visibility-conditional anchor:
   - `.sameContextOnly` → Context
   - `.publicMatch` → Activity, Place
   - `.inviteOnly` → nothing
5. **Timing** (always asked, last)
6. **Plan mode** (Loose/Exact — moved late; it's a refinement of an already-formed plan)
7. Preview
8. Validation message

And: **remove the duplicate Place field** from Core details. Place lives only in the publicMatch anchor section. For non-public plans, Exact mode's "Exact plans should name the place up front" validation needs a Place field too — add a third anchor case for `.sameContextOnly + mode == .exact` showing a single Place TextField bound to `venueHint`. Or keep the Core-details Place field but hide it when `visibility == .publicMatch` to avoid the double binding.

Pick the simpler one: **keep one Place field in Core details, hide it when `visibility == .publicMatch`** (the publicMatch anchor section already has its own). Net change: a `if draft.visibility != .publicMatch` around the Place TextField in Core details.

#### Research Insights — Issue 4

**Ordering principle (industry-validated):** *decision-first, then detail.* Apple HIG ("Entering Data" — ask only what you need, in the order it's needed), Material 3 form guidelines, Airbnb "Create listing", and Partiful event creation all front-load the structural questions that change downstream fields. Eventbrite is the cited counter-example — asks visibility late, users fill details, then the form reshuffles. Don't be Eventbrite.

**Visibility belongs *early*, alongside Mode.** This **reverses one ambiguity in the original plan** (which placed visibility after core details). Reasons:
- Visibility conditionally reveals new sections (activity picker for `.publicMatch`). Filling core details first then watching new required sections appear is the failure mode.
- Visibility shapes the user's mental model — public match is a different *kind* of plan than a private context drop, and users word their headline/summary differently.
- One-line descriptors under each visibility option mitigate the "user doesn't know visibility yet" objection.

**Updated proposed order (final):**
1. Intro blurb (compact)
2. **Plan mode** (loose / exact) — structural
3. **Visibility** (sameContextOnly / publicMatch / inviteOnly) — structural, gates section 5
4. **Core details:** headline, summary, place (hidden when `.publicMatch`), timing
5. **Visibility-conditional anchor:**
   - `.sameContextOnly` → Context display
   - `.publicMatch` → Activity picker + Place (single binding to `venueHint`)
   - `.inviteOnly` → empty
6. Preview ("What people will see")
7. Validation footer (when present)

This order leaves Mode at the top (it's quick — two options) and Visibility right after, before any text input. The user makes both structural decisions in seconds, then writes content with full knowledge of the audience and shape.

**Conditional Section pitfalls in `Form` (carry into implementation):**
- **Animation glitches:** without `.animation(.default, value: draft.visibility)` on the `Form`, sections pop in abruptly with broken separators. Add it.
- **Focus loss:** if a `TextField` lives inside a section that gets removed/re-added, focus is lost. Our reshuffle doesn't toggle TextFields across visibility transitions (place stays in core details, hidden via `if`), so this isn't hit. If we ever move place into the anchor switch, use `@FocusState` to restore.
- **Don't put `LazyVStack` inside `Form`** — breaks Form's grouped styling. iOS 16+ `Form` already lazy-loads sections.

**Duplicate `@Binding` rule:** each `@Binding` appears in *exactly one editable site* per form. The current bug (Place in two places, both bound to `venueHint`) violates this and produces visual confusion. Fix: one editable Place field, hidden when `.publicMatch`; the publicMatch anchor section gets its own Place field bound to the same property. Net: still one editable Place field at any given time.

**Disabled-button affordance — keep current pattern for v1.** The current "disabled Publish + orange footer text" is acceptable. The HIG-preferred "enabled + scroll-on-tap + inline red footer" is a follow-up. Don't expand scope.

**Reference:** Apple HIG — Entering Data: https://developer.apple.com/design/human-interface-guidelines/entering-data

## Technical Considerations

- **No model changes.** Pure view/validation changes.
- **No new dependencies.** `FlowLayout` is hand-rolled against the iOS 16 `Layout` protocol.
- **Snapshot/UI tests:** the project has a `Tests/` folder — check whether snapshot tests of `OnboardingView` or `CreatePlanView` exist; if yes, they'll need re-baselining for the layout changes. If no, the user has been doing manual QA — we add no new test infra in this PR (matches repo convention of "lightweight frameworks until architecture proves itself").
- **Color scheme preview:** add `.preferredColorScheme(.dark)` previews next to existing previews on `HomeView`, `OnboardingView`, `CreatePlanView` so future regressions are visible at edit time. Two-line additions per file.

## System-Wide Impact

- **Interaction graph:** validation flow is `CreatePlanDraft.validationMessage` → `CreatePlanView.toolbar` Publish button `.disabled` → `store.createPlan(from:)` → `backend.venues.upsertVenue` (freeform path) → `backend.plans.createPlan`. Relaxing the gate exposes the freeform venue path, which is already implemented and unit-tested per the context-model refactor plan.
- **Error propagation:** none new. Freeform venue upsert can fail; existing `try?` in store swallows to `false` return. No change needed.
- **State lifecycle risks:** none. Plan is a single-shot create.
- **API surface parity:** `CreatePlanView` is the only surface that creates plans. `OnboardingView` uses the same activity taxonomy via `ActivityVenuePickerView` — the FlowLayout change here will also need to apply if `ActivityVenuePickerView` is reused in CreatePlan (it's not currently, but there's an `iOS Activity Picker` in onboarding only). Verified: `ActivityVenuePickerView` is referenced only by `ActivityVenueStepView`.
- **Integration test scenarios** (manual, since no UI test harness):
  1. Toggle iOS Settings → Display → Dark; launch app; verify every screen has readable text.
  2. Run onboarding to step 3; verify activity pills wrap into a grid with no horizontal scroll.
  3. Create a public plan with a typed place name (e.g. "The Standard"); verify Publish enables and the plan persists.
  4. Create a `.sameContextOnly` plan with mode `.exact`; verify Place is required, validation message correct.
  5. Create a `.sameContextOnly` plan with mode `.loose`; verify no Place needed.

## Acceptance Criteria

- [ ] Dark mode: every screen (`OnboardingView`, `HomeView`, `ActivityView`, `PlanDetailView`, `ConfirmationRoomView`, `SafetyCenterView`, `ProfileView`, `CreatePlanView`) renders with text/background contrast ≥ WCAG AA (4.5:1) at body size.
- [ ] Light mode visually unchanged from current state (subjective; user signs off).
- [ ] Onboarding activity step shows all activities in a wrapping grid; no horizontal scroll on devices ≥ iPhone SE (3rd gen) width (375pt).
- [ ] Public plan creation: typing a place name and a headline enables the Publish button; tapping publish creates a plan and returns to Home.
- [ ] Public plan creation: leaving place empty keeps Publish disabled with the existing copy.
- [ ] Same-context plan with mode `.exact`: Place required, mode `.loose`: not required (existing behavior preserved).
- [ ] CreatePlanView header reads "Plan What's Next".
- [ ] Section order matches the proposed reorder; no duplicate Place field visible at any visibility.
- [ ] Dark mode previews added for `OnboardingView`, `HomeView`, `CreatePlanView`.

## Success Metrics

Bug — user signs off after a manual walk-through covering the five integration scenarios above.

## Dependencies & Risks

- **Risk:** dynamic `Color(uiColor:)` may render slightly differently on visionOS or Mac Catalyst. Project targets iOS only ([products/after-plans-ios/project.yml](products/after-plans-ios/project.yml) — verify) so low risk.
- **Risk:** `FlowLayout` width/height calculation edge cases (single very long pill, RTL languages). Activity titles are short English strings; defer RTL handling.
- **Risk:** removing the duplicate Place field changes the binding shape for `.sameContextOnly + .exact`. Validation message at line 46 of `CreatePlanDraft.swift` still references `trimmedVenueHint` — need to confirm the Place field stays visible for that case, or move the field into the anchor switch.
- **Dependency:** none external.
- **Out of scope (future plans):**
  - Real `MKLocalSearchCompleter` typeahead in CreatePlan Place section.
  - Visual design pass for dark mode (going beyond "legible" to "branded").
  - Migrating brand colors to asset catalog Color Sets.

## Implementation order

1. **Asset Catalog Color Sets** — add `BrandAccent`, `Momentum`, `Safe` color sets in `Sources/Assets.xcassets/` with Any + Dark variants (Dark variants ~15% lighter than current hex).
2. **DesignTokens.swift — chrome migration** — `appBackground`, `appCard`, `appCardStrong`, `appBorder` → `Color(uiColor:)` system equivalents. Drop `.opacity(0.84)` from card fills.
3. **DesignTokens.swift — brand migration** — `appAccent`, `appMomentum`, `appSafe` → `Color("BrandAccent", bundle: .main)` etc.
4. **DesignTokens.swift — shadow + pill button fix** — `AppSurface` shadow color → `Color(uiColor: .label).opacity(0.10)`; `ActionPillButtonStyle` non-prominent fill → `Color(uiColor: .secondarySystemFill)`.
5. **Audit `Color.black.opacity` / `Color.white` usages** outside DesignTokens — fix `HomeView.swift:73`.
6. **CreatePlanDraft.swift** — relax `venueID` validation: `venueID != nil || !trimmedVenueHint.isEmpty`.
7. **CreatePlanView.swift** — header rename to "Plan What's Next"; section reorder (mode → visibility → core details (place hidden when public) → conditional anchor → preview → validation); add `.animation(.default, value: draft.visibility)` on the Form; conditional `if draft.visibility != .publicMatch` around the Core-details Place TextField.
8. **FlowLayout.swift** — add to `Sources/Shared/UI/`. Body provided in Issue 2 research insights.
9. **ActivityVenueStepView.swift** — swap `ScrollView(.horizontal) + HStack` for `FlowLayout { ForEach(...) }`. Wrap step content in `ScrollView(.vertical)` if onboarding clips.
10. **Dark previews** — add `#Preview("Dark")` blocks for `OnboardingView`, `HomeView`, `CreatePlanView`.
11. **Verify `TARGETED_DEVICE_FAMILY = "1"`** in `project.yml` before iPad QA.
12. **Manual QA pass** — five scenarios listed above, run in light + dark on iPhone simulator.

## Sources & References

### Origin

- **Context-model refactor plan:** [docs/plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md](docs/plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md) — introduced public plans, activity+venue model, freeform venue path. This plan fixes a regression (#3) and polish issues (#1, #2, #4) discovered while testing the refactor.

### Internal references

- [products/after-plans-ios/Sources/Shared/UI/DesignTokens.swift:5-13](products/after-plans-ios/Sources/Shared/UI/DesignTokens.swift) — surface color tokens to migrate.
- [products/after-plans-ios/Sources/Features/Onboarding/Steps/ActivityVenueStepView.swift:22-48](products/after-plans-ios/Sources/Features/Onboarding/Steps/ActivityVenueStepView.swift) — horizontal scroll to replace.
- [products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanView.swift:95-100,125](products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanView.swift) — duplicate Place field, header rename.
- [products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanDraft.swift:33-35](products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanDraft.swift) — validation gate to relax.
- [products/after-plans-ios/Sources/App/AfterPlansStore.swift:409-443](products/after-plans-ios/Sources/App/AfterPlansStore.swift) — freeform venue materialization, already wired.
- [products/after-plans-ios/Sources/Services/VenueSearchService.swift:40-46](products/after-plans-ios/Sources/Services/VenueSearchService.swift) — freeform venue factory.

### Institutional learnings carried forward

- [docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md](docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md) — direct match to Issue 3. "The new capability is gated behind the old requirement it was supposed to eliminate." Carry forward: relax all enforcement sites of the old rule in one go.
- [docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md](docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md) — contextual for Issue 2. Verify `TARGETED_DEVICE_FAMILY` before assuming layout fixes solve "looks cramped on iPad" reports.

### External references

- Apple HIG — Dark Mode: https://developer.apple.com/design/human-interface-guidelines/dark-mode
- Apple HIG — Color (incl. WCAG AA contrast targets): https://developer.apple.com/design/human-interface-guidelines/color
- Apple HIG — Entering Data (form-ordering principles): https://developer.apple.com/design/human-interface-guidelines/entering-data
- Apple — `Color(uiColor:)` and adaptive UIColors: https://developer.apple.com/documentation/uikit/uicolor/standard_colors
- Apple — `Layout` protocol (iOS 16+): https://developer.apple.com/documentation/swiftui/layout
- Apple — Composing custom layouts in SwiftUI: https://developer.apple.com/documentation/swiftui/composing-custom-layouts-with-swiftui
