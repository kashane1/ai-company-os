---
title: Life Clock palette picker (lean)
type: feat
status: active
date: 2026-04-29
deepened: 2026-04-29
---

# Life Clock palette picker (lean)

## Enhancement summary (deepen pass)

**Deepened on:** 2026-04-29 (same day as initial plan)
**Agents consulted:** architecture-strategist, code-simplicity-reviewer,
pattern-recognition-specialist, data-migration-expert,
data-integrity-guardian, performance-oracle, spec-flow-analyzer,
learnings-researcher, best-practices-researcher, framework-docs-researcher.

### Key revisions vs initial plan

1. **Drop the singleton mirror + `.id(store.palette.id)`.** The `.id`
   modifier on the root container was framed as a perf trade-off, but
   it is a **correctness regression**: identity reset destroys
   `@State` inside the rebuilt subtree. `MainTabView.selection` would
   reset to `.today` on every palette switch (and the picker lives on
   Profile, so this fires on *every* user action), and any presented
   sheet (e.g. QuickLog) would dismiss with in-flight state lost.
   *Replaced with* a tiny `@Observable PaletteHolder` injected via
   environment; SwiftUI invalidates only the views that read palette
   tokens during their `body`, no tree rebuild.
2. **`LifeClockPalette` is an enum, not a struct.** Mirrors the
   existing `ToneMode: String` pattern line-for-line, gives stable
   `Hashable` (rawValue-based, not fragile `Color`-equality-based),
   collapses `resolve(id:)` to `LifeClockPalette(rawValue:) ??
   .defaultNavy` — exactly parallel to `ToneMode(rawValue:)` at
   `LifeClockStore.swift:73`.
3. **Drop speculative palette fields.** `surfaceTint`, `chrome`,
   `positiveTint` have zero existing call sites. Lean-v1 ships with
   `displayName` and `accent` only, propagated via `.tint(_:)` at
   the root. `DesignTokens.Palette` is **unchanged** — the 29 existing
   call sites need no edits at all. Estimated delta: ~190 LOC planned
   → ~70 LOC actual (≈60% reduction).
4. **Add reset-path palette restoration.** `resetForOnboarding()` must
   explicitly set `store.palette = .defaultNavy` to prevent a stale
   palette persisting across re-onboarding (data-integrity finding).
5. **Add `setPalette` write-side guard for missing profile.** When
   called pre-onboarding (no `profile` yet), update the in-memory
   palette only — do not silently no-op or crash on `profile?.paletteId`.
6. **Hedge the SwiftData migration claim.** Apple's *documented*
   `MigrationStage.lightweight(fromVersion:toVersion:)` is between
   `VersionedSchema`s. The "additive with default → no plan needed"
   path is empirically reliable and matches the team's `toneMode`
   precedent, but is not formally documented. Plan adds an explicit
   fall-back to `LifeClockSchemaV2` if the runtime store complains.
7. **Reconcile hex/RGB mismatch.** Original plan wrote `#234897` next
   to `Color(red: 0.137, green: 0.282, blue: 0.612)` — that RGB tuple
   actually resolves to `#23489C`. The current `AccentColor.colorset`
   value (`0.612` blue) is the source of truth; corrected hex.
8. **Flag WCAG-AA contrast as a known gap.** Default Navy on dark
   `.systemBackground` measures ≈2.6:1 (fails AA text, fails AA UI).
   Sunset Warm amber on light bg is borderline. *Not blocking lean
   v1*, but tracked under "Risks & follow-ups" with concrete remedy.

### Findings that confirmed initial plan

- **SwiftData lightweight migration is safe in practice** for an
  additive `String` field with a property-level default — established
  team pattern, verified against
  `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`.
- **iPad inheritance is correct** — `TARGETED_DEVICE_FAMILY = "1,2"`
  is already set; picker section needs no extra work.
- **Tone-mode pattern is the right template** for store + persistence
  + picker integration, but the *value type* in the original plan
  diverged from it; the revised enum-based palette aligns.

---

## Overview

Ship three user-selectable color palettes for Life Clock — **Default
Navy** (current), **Aurora Cool**, **Sunset Warm** — surfaced as a
Profile-screen picker, persisted on `UserProfile.paletteId`, restored
on cold start, and applied across the app via `.tint(_:)` propagation
from the root container. The founder-pack rule "never alarming red"
is preserved structurally: `LifeClockPalette` has no `negative` field
to mis-set; the orange negative-delta color stays as a `static let`
constant on `DesignTokens.Palette`.

This is the **lean** scope. Out of scope (deferred):

- Per-palette light/dark variants beyond what `Color(.systemBackground)`
  already gives via system-color adaptation.
- Custom palettes / hex pickers / community palettes.
- Animated transitions on palette switch.
- Tone-mode-aware default palettes (e.g. memento-mori → Sunset).
- iCloud / cross-device palette sync (forbidden in v1).
- Per-palette `chrome` / `surfaceTint` / `positiveTint` overrides
  (no existing call sites; revisit when a view actually needs them).

## Problem statement / motivation

The new app icon (`life-clock-icon-idea1.png`, just copied to
`Assets.xcassets/AppIcon.appiconset/Icon-1024.png`) introduces chrome
blue/red metallic vibes that align well with the current navy accent
but invite a cooler/aurora aesthetic for users who want it. The
founder wants:

1. The icon to ship without forcing a palette change for users who
   like the current navy.
2. A way to swap palette for users who'd prefer warmer or cooler tones.
3. A pattern that makes future palette additions cheap (one new enum
   case + one accent color).

This unblocks shipping the new icon without coupling icon-design to a
single in-app aesthetic.

## Proposed solution (revised architecture)

### High-level approach

Define `LifeClockPalette` as a `String`-backed enum with three cases.
Persist the selected raw value on `UserProfile.paletteId` (additive,
property-level default — mirrors `toneMode` exactly). Restore on
`bootstrap()`. Inject a tiny `@Observable PaletteHolder` (held by
`LifeClockStore`) into the SwiftUI environment; the root view applies
`.tint(store.palette.accent)`, which propagates accent overrides to
all descendant SwiftUI controls. Views that need palette-specific
colors beyond `accent` (none today) can read
`@Environment(\.lifeClockPalette)` directly when added.

### Why no static-mirror + `.id()` rebuild

The original architecture used a `@MainActor static var currentMirror`
read by `DesignTokens.Palette.*` static getters, with
`.id(store.palette.id)` on the root forcing a tree rebuild. Two
problems made this wrong:

1. **State loss on switch.** `.id` change tears down the subtree.
   `MainTabView.selection` (`@State`) snaps back to `.today`, any
   presented sheet (QuickLog) dismisses, scroll positions reset.
   Because the palette picker lives on the Profile tab, *every*
   palette change would kick the user out of Profile.
2. **Static getters bypass observation.** A `static var` getter is
   not tracked by `@Observable`; views reading
   `DesignTokens.Palette.accent` would only redraw because of the
   `.id()` rebuild — a hidden coupling that breaks silently if the
   `.id` modifier is later removed.

The revised approach has neither problem: `@Observable` tracks every
view that reads `store.palette.accent` during render and invalidates
exactly those views. `.tint(_:)` is the SwiftUI-idiomatic accent
propagation mechanism (Apple HIG, iOS 17+).

### What varies per palette vs what stays constant

**Varies (palette-controlled, lean v1):**

- `accent` — primary tint, propagated via root `.tint(_:)` to all
  controls (Buttons, Toggles, Pickers, NavigationStack chevrons,
  TabView selection, segmented Pickers, ProgressView, links).
- `displayName` — picker label.

**Constant (cross-palette, type-enforced absence of palette field):**

- `negative` = `Color.orange` — founder-pack rule, see
  `docs/products/life-clock/PHASE_STATUS.md` "agency over fear, never
  alarming red".
- `positive` = `Color.green.opacity(0.85)` — current default.
- `muted` = `.secondary`.
- `surface` = `Color(.systemBackground)`.
- `elevated` = `Color(.secondarySystemBackground)`.

`LifeClockPalette` deliberately has **no** `negative`/`positive`/
`surface`/`elevated`/`muted`/`chrome`/`surfaceTint` fields. The
absence of these fields is the orange-not-red invariant.

## Technical considerations

### File touch list (revised)

**New files (2):**

- `products/life-clock-ios/Sources/Design/LifeClockPalette.swift`
  - `enum LifeClockPalette: String, CaseIterable, Identifiable`
  - Cases: `.defaultNavy = "default-navy"`, `.auroraCool = "aurora-cool"`,
    `.sunsetWarm = "sunset-warm"`.
  - Computed `displayName: String` and `accent: Color` per case.
- `products/life-clock-ios/Tests/LifeClockPaletteTests.swift`
  - Restoration + reset + onboarding-default + setPalette-no-profile
    tests (see Testing section).

**Modified files (5):**

- `products/life-clock-ios/Sources/Models/LifeClockSchema.swift`
  - Add `var paletteId: String = "default-navy"` to `UserProfile`,
    line 43-area (next to `var toneMode: String = "coach"`).
- `products/life-clock-ios/Sources/App/LifeClockStore.swift`
  - New observable property: `var palette: LifeClockPalette = .defaultNavy`.
  - New method `func setPalette(_ palette: LifeClockPalette)` — see
    pseudocode below; guards against missing profile.
  - `bootstrap()`: inside `if let profile { ... }` (parallel to the
    existing `ToneMode(rawValue: profile.toneMode)` restore at lines
    72-74), restore palette **before** `await refreshFromHealthKit()`
    to avoid a one-frame palette flicker.
  - `resetForOnboarding()`: append `palette = .defaultNavy` so a user
    who picked Sunset Warm and resets sees default colors during the
    re-onboarding flow.
- `products/life-clock-ios/Sources/App/LifeClockApp.swift`
  - Apply `.tint(store.palette.accent)` to the root container view.
    No `.id(...)` modifier.
- `products/life-clock-ios/Sources/Features/Profile/ProfileView.swift`
  - New "Appearance" section with `Picker` over
    `LifeClockPalette.allCases`, bound through `setPalette(_:)`.
- `products/life-clock-ios/Tests/LifeClockStoreTests.swift`
  - Tests for cold-restart restore, garbage-ID fallback, reset-path
    palette restoration (see Testing section).

**Untouched:**

- `products/life-clock-ios/Sources/Shared/DesignTokens.swift` — no
  changes. The 29 existing `DesignTokens.Palette.*` call sites continue
  to work as-is.

### Pseudocode (revised)

#### `Sources/Design/LifeClockPalette.swift`

```swift
import SwiftUI

enum LifeClockPalette: String, CaseIterable, Identifiable {
    case defaultNavy = "default-navy"
    case auroraCool  = "aurora-cool"
    case sunsetWarm  = "sunset-warm"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .defaultNavy: "Default Navy"
        case .auroraCool:  "Aurora Cool"
        case .sunsetWarm:  "Sunset Warm"
        }
    }

    /// Primary tint color. Propagated via root `.tint(_:)` to all
    /// SwiftUI controls. The negative-delta color is intentionally
    /// not exposed here — it is a constant on `DesignTokens.Palette`,
    /// type-enforcing the founder-pack "never alarming red" rule.
    var accent: Color {
        switch self {
        case .defaultNavy:
            // Matches AccentColor.colorset (R 0.137, G 0.282, B 0.612 → #23489C)
            Color(red: 0.137, green: 0.282, blue: 0.612)
        case .auroraCool:
            // Cooler indigo, picks up the icon's blue chrome side
            Color(red: 0.231, green: 0.357, blue: 0.749)
        case .sunsetWarm:
            // Warm amber — see Risks for dark-mode contrast follow-up
            Color(red: 0.85, green: 0.42, blue: 0.20)
        }
    }
}
```

#### `Sources/App/LifeClockStore.swift` (additions)

```swift
// In the @Observable class:
var palette: LifeClockPalette = .defaultNavy

// In bootstrap(), inside the existing `if let profile { ... }` block,
// BEFORE `await refreshFromHealthKit()` (which is currently the last
// statement in bootstrap()):
if let profile {
    if let restored = LifeClockPalette(rawValue: profile.paletteId) {
        self.palette = restored
    }
    // (existing tone-mode + ledger restore stays unchanged)
}

// New mutation method, parallel to setToneMode at LifeClockStore.swift:160
func setPalette(_ palette: LifeClockPalette) {
    self.palette = palette
    profile?.paletteId = palette.rawValue
    try? modelContext.save()
}

// In resetForOnboarding(), append (after existing resets):
palette = .defaultNavy
```

#### `Sources/App/LifeClockApp.swift` (root modifier)

```swift
RootContainerView()
    .tint(store.palette.accent)   // SwiftUI accent override
    // NOTE: no .id(store.palette.id). @Observable + .tint propagation
    // handles redraw without destroying tab/sheet state.
```

#### `Sources/Features/Profile/ProfileView.swift` (new section)

```swift
Section("Appearance") {
    Picker(
        "Color palette",
        selection: Binding(
            get: { store.palette },
            set: { store.setPalette($0) }
        )
    ) {
        ForEach(LifeClockPalette.allCases) { p in
            HStack {
                Circle().fill(p.accent).frame(width: 16, height: 16)
                Text(p.displayName)
            }
            .tag(p)
        }
    }
}
```

## System-wide impact

- **Interaction graph:** User taps palette in Profile →
  `store.setPalette(.auroraCool)` → assigns observable
  `store.palette` (SwiftUI invalidates views reading the property
  during render) → writes `profile.paletteId = "aurora-cool"` →
  `try? modelContext.save()` persists. The root `.tint(_:)` modifier
  re-resolves to the new accent because `store.palette.accent` is
  read inside the App view body. No tree rebuild, no state loss.
- **Error propagation:** `try? modelContext.save()` is identical to
  every other store mutation — failure leaves in-memory ahead of disk;
  cold restart reverts to last saved value. Acceptable, matches the
  existing pattern.
- **State lifecycle risks:** None new. Three potential divergence
  axes are now closed:
  1. *Pre-onboarding `setPalette` call*: in-memory palette updates,
     `profile?.paletteId` no-ops harmlessly because `profile == nil`,
     no crash. (Defended by test
     `testSetPaletteWithNoProfileUpdatesInMemoryOnly`.)
  2. *Reset path*: `resetForOnboarding()` explicitly resets palette
     and the new profile starts at default-navy via the property-level
     default. (Defended by test `testResetForOnboardingRestoresDefaultPalette`.)
  3. *Garbage / absent paletteId on disk*: `LifeClockPalette(rawValue:)`
     returns `nil` for unknown strings; bootstrap's `if let restored`
     leaves `palette` at the in-memory default `.defaultNavy`.
     (Defended by test
     `testBootstrapFallsBackToDefaultNavyForUnknownPaletteId`.)
- **API surface parity:** All 29 existing `DesignTokens.Palette.*`
  call sites are *unchanged*. New code paths use
  `store.palette.accent` directly when needed (currently only the
  root `.tint`).
- **Integration test scenarios:**
  1. Pick Aurora Cool → kill app → relaunch → still Aurora Cool.
  2. Tamper persisted `paletteId` to garbage value → relaunch → falls
     back to Default Navy (no crash).
  3. Pick Sunset Warm → reset onboarding → re-onboard → palette is
     Default Navy (not stale Sunset).
  4. Open Profile → tap palette → assert tab does NOT snap back to
     Today and any in-flight sheet remains presented (regression test
     for the discarded `.id()` approach).
  5. Switch palettes 3× in a row → each switch is non-destructive,
     no carry-over from prior switch.

## Acceptance criteria

- [x] Three palette cases defined: `.defaultNavy`, `.auroraCool`,
      `.sunsetWarm` (`String`-backed enum, `CaseIterable`,
      `Identifiable`).
- [x] `UserProfile.paletteId` field added with property-level default
      `"default-navy"` (lightweight migration in practice; matches
      established `toneMode` precedent).
- [x] `LifeClockStore` exposes observable `palette: LifeClockPalette`
      and `setPalette(_:)` parallel to `setToneMode(_:)`.
- [x] `bootstrap()` restores palette from persisted profile via
      `LifeClockPalette(rawValue:)`, falling back to `.defaultNavy` on
      unknown / missing IDs, **before** `await refreshFromHealthKit()`.
- [x] `resetForOnboarding()` resets palette to `.defaultNavy`.
- [x] Profile screen has an "Appearance" section with a working palette
      picker showing accent swatches and palette display names.
- [x] Selection persists across cold restart.
- [x] Switching palette while QuickLog sheet is presented from Today
      does *not* dismiss the sheet, and the user's tab stays on
      Profile.
- [x] CI grep gates pass: no new `HKHealthStore()` outside service, no
      new `Date()`/`.current` outside `EngineClock`, no
      `diagnose`/`prescribe`/`guarantee`, no iCloud refs.
- [x] No edits to `DesignTokens.swift` (29 existing `Palette.*` call
      sites untouched).
- [x] All new tests below pass.

## Testing requirements (revised)

**`Tests/LifeClockPaletteTests.swift` (new):**

- `testInitFromKnownRawValue` — each of three raw values
  (`"default-navy"`, `"aurora-cool"`, `"sunset-warm"`) resolves to the
  corresponding case via `LifeClockPalette(rawValue:)`.
- `testInitFromUnknownRawValueReturnsNil` — `"ghost"` →
  `LifeClockPalette(rawValue: "ghost") == nil`. (Note: this is enum
  framework behavior, but pinning it documents the contract that
  `bootstrap` relies on.)
- `testAllCasesHasThreeMembers` — `LifeClockPalette.allCases.count == 3`
  (catches accidental case removal).

Dropped vs initial plan: `testPresetsHaveDistinctIds` (tautological for
an enum), `testNegativeIsOrangeAcrossAllPalettes` (no `negative` field
exists on the type — invariant is structural, not testable),
`testResolveFallsBackToDefaultNavyForNilId` (collapsed into bootstrap
fallback test below).

**`Tests/LifeClockStoreTests.swift` (additions):**

- `testSetPalettePersistsAndRestoresAcrossColdRestart` — onboard,
  `setPalette(.auroraCool)`, build a fresh store on the same in-memory
  container, bootstrap, assert `store2.palette == .auroraCool` and
  `store2.profile?.paletteId == "aurora-cool"`.
- `testBootstrapFallsBackToDefaultNavyForUnknownPaletteId` — onboard,
  reach into the persisted `UserProfile`, set `paletteId = "ghost"`,
  save, build a fresh store, bootstrap, assert
  `store2.palette == .defaultNavy`.
- `testResetForOnboardingRestoresDefaultPalette` — onboard,
  `setPalette(.sunsetWarm)`, assert palette is sunset, then
  `resetForOnboarding()`, assert `store.palette == .defaultNavy`.
- `testSetPaletteWithNoProfileUpdatesInMemoryOnly` — fresh store, no
  profile, `setPalette(.auroraCool)`, assert
  `store.palette == .auroraCool` and no crash; bootstrap then
  completes onboarding and asserts `profile.paletteId` is set from the
  property-level default `"default-navy"` (because the in-memory
  palette change pre-onboarding does not retroactively write to the
  profile that didn't exist yet — documents this behavior).

## Success metrics

- Zero source changes at the 29 existing `DesignTokens.Palette.*`
  call sites.
- Switching palette is non-destructive: tab selection and presented
  sheets survive (regression test #4 above).
- Founder accepts the new icon shipping with all three palettes
  available (subjective sign-off).

## Dependencies & risks

**Dependencies:**

- New icon already at
  `products/life-clock-ios/Sources/Assets.xcassets/AppIcon.appiconset/Icon-1024.png`
  (committed in this session).
- No new third-party libraries.

**Risks:**

- **WCAG-AA contrast (medium, deferred to follow-up).** Three
  measurements at issue:
  - Default Navy (`Color(red: 0.137, green: 0.282, blue: 0.612)`)
    against dark `.systemBackground` ≈ 2.6:1 → **fails AA-text and
    AA-UI** (need ≥3:1 for UI, ≥4.5:1 for body text).
  - Sunset amber (`(0.85, 0.42, 0.20)`) on light bg ≈ 3.3:1 →
    passes AA-large/UI, fails AA-text.
  - Aurora indigo (`(0.231, 0.357, 0.749)`) on dark bg ≈ 4.0:1 →
    passes AA-large/UI, fails AA-text.

  **Remedy (post-merge follow-up, not blocking lean v1):** convert
  `accent` to per-mode `Color(uiColor: UIColor { trait in ... })`
  pairs and add `LifeClockPaletteContrastTests` that asserts ≥3:1
  for accent against both light and dark `.systemBackground`. Track
  as a follow-up plan; the current AccentColor used in production has
  the same contrast property (so we are not regressing — we are
  inheriting it).

- **Tab-bar tint on iOS 17+ (low).** `.tint(_:)` propagates to
  SwiftUI `TabView` items on iOS 17+. If QA spots a stale tint on
  the tab bar after switching palettes, fall back to setting
  `UITabBar.appearance().tintColor` inside `bootstrap()` and
  `setPalette()`. Not expected; flagged for QA.

- **SwiftData migration claim is empirical, not Apple-documented
  (low).** Apple's `MigrationStage.lightweight(fromVersion:toVersion:)`
  is between two `VersionedSchema`s. The "additive with default → no
  plan needed" path used by both `toneMode` and now `paletteId` is
  reliable in practice and matches the team's prior precedent
  (`docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`).
  If CI or device-install testing reports `NSCocoaErrorDomain
  134110` or similar, escalate to `LifeClockSchemaV2` with a
  `MigrationStage.lightweight(fromVersion: V1, toVersion: V2)` stage
  — the empty `LifeClockMigrationPlan` scaffold is already in place
  at `LifeClockSchema.swift:198-207` to receive this without further
  refactor.

- **Contrast hex/RGB drift (low).** The original plan's `#234897`
  comment did not match the RGB tuple. Source of truth is the existing
  `AccentColor.colorset` JSON (`blue: 0.612, green: 0.282, red:
  0.137`) which renders as `#23489C`. Fixed in revised pseudocode.

## Sources & references

### Internal references

- `products/life-clock-ios/Sources/Models/LifeClockSchema.swift:31` —
  `UserProfile` model (mirror `toneMode` pattern at line 43 for
  `paletteId`)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:22, 71-74,
  146-164, 212-222` — `toneMode` observable property, bootstrap
  restoration, `setToneMode`, `resetForOnboarding` — exact parallel
  pattern.
- `products/life-clock-ios/Sources/Shared/DesignTokens.swift` — current
  `Palette` enum, **untouched** by this plan.
- `products/life-clock-ios/Sources/Features/Profile/ProfileView.swift` —
  picker host, follows existing tone-mode picker structure.
- `products/life-clock-ios/Sources/Assets.xcassets/AccentColor.colorset/Contents.json` —
  source of truth for Default Navy RGB values.
- `docs/products/life-clock/PHASE_STATUS.md` — "agency over fear" /
  "never alarming red" rule (drives orange-not-red invariant via
  the structural absence of a `negative` field on the enum).
- `docs/products/life-clock/CLAUDE_HANDOFF.md` — CI grep gates and
  worktree conventions.

### Past learnings to apply

- `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md` —
  property-level defaults are required for backfilling legacy rows.
  Verified to apply; `paletteId: String = "default-navy"` is the
  correct form.
- `docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md` —
  `TARGETED_DEVICE_FAMILY = "1,2"` already set; picker inherits.
- `docs/solutions/integration-issues/catchbook-navigation-revamp-rollout.md`
  (parent worktree) — `@Observable` + `@Environment` + `@Bindable`
  pattern for cross-cutting state. Revised plan aligns: store is
  observable, palette is a property on it, picker creates a
  `Binding(get:set:)` wrapping `setPalette`.

### External references

- [SwiftUI `tint(_:)` modifier](https://developer.apple.com/documentation/swiftui/view/tint(_:)-93mfq)
  — *"Unlike an app's accent color … the tint color is always
  respected."*
- [SwiftUI `View.id(_:)` modifier](https://developer.apple.com/documentation/swiftui/view/id(_:))
  — *"When the proxy value … changes, the identity of the view —
  for example, its state — is reset."* (This is precisely why the
  initial plan's `.id` approach is wrong.)
- [SwiftData lightweight migration](https://developer.apple.com/documentation/swiftdata/preserving-your-app-s-model-data-across-launches)
  — `MigrationStage.lightweight(fromVersion:toVersion:)` is the
  documented surface; in-place additive defaults are reliable but not
  formally documented.
- [WCAG 2.2 contrast minimum (1.4.3)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
  — 4.5:1 body text, 3:1 large text and UI components.

### Related work

- Tone-mode persistence + restore (`UserProfile.toneMode` +
  `LifeClockStore.setToneMode`) — exact parallel pattern. The revised
  enum-based palette mirrors it line-for-line.
- Disclaimer-guard + clear-today-habits work just shipped on this
  branch — same write-side guard discipline applied to `setPalette`'s
  no-profile path.
- New app icon (`life-clock-icon-idea1.png` → `Icon-1024.png`,
  staged this session) — context that motivated this plan.
