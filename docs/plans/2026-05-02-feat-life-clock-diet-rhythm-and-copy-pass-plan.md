---
title: Life Clock — diet rhythm axis, whole-food anchor, life-impact framing, tone copy pass
type: feat
status: shipped
date: 2026-05-02
shipped_pr: https://github.com/kashane1/ai-company-os/pull/21
origin: ChatGPT brainstorm audit, 2026-05-01 — items A–D salvaged from a near-empty-context brainstorm against the actual reveal-onboarding shipped state. The brainstorm's larger restructure (drop HealthKit, retarget 17–25, two-plan paywall, 15-screen onboarding) was rejected as contradicting recent shipped decisions; this plan only carries the four scoped changes that survived audit.
related:
  - docs/products/life-clock/PHASE_STATUS.md
  - docs/products/life-clock/ux-audit-2026-04-30.md
  - docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md
  - docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md
---

# Life Clock — diet rhythm axis, whole-food anchor, life-impact framing, tone copy pass

## Enhancement Summary

**Deepened on:** 2026-05-02
**Sections enhanced:** Phases 1, 3, 4, 5; Acceptance Criteria; Risk Analysis. Open Questions removed.
**Research agents used:** data-integrity-guardian, data-migration-expert, code-simplicity-reviewer, architecture-strategist, performance-oracle, pattern-recognition-specialist, best-practices-researcher (SwiftData iOS 17), framework-docs-researcher (App Review disclaimer placement, SwiftUI conditional rendering).

### Material corrections from review

1. **Migration test was theater.** Under the in-place `LifeClockSchemaV1` convention, the existing `LifeClockSchemaMigrationTests` write/read round-trip does **not** exercise V1.1 → V1.2 lightweight migration — by the time the test runs, the V1.1 shape no longer exists in the binary. Phase 1 now requires either (a) a bundled `Tests/Fixtures/v1_1_baseline.store` captured from a real V1.1 build, or (b) renaming the test to reflect that it validates codec round-trip only and relying on the manual install-over-previous device test for real verification. Recommended: (b) — the in-place-bump convention is documented as tech debt, the fixture path is high-effort for one PR, and the device test is already in acceptance criteria.
2. **`"unset"` sentinel broke codebase convention.** Existing `HabitLog` defaults are *meaningful neutral values* (`dietQuality="okay"`, `alcoholLevel="none"`, `stressLevel="medium"`), not sentinels. Phase 1 now uses `dietAmountRhythm: String = "right"` (meaningful neutral, engine treats as zero contribution) and `wholeFoodMeal: String = "unknown"` (matches the existing `"unknown"` token referenced at `QuestEngine.swift:121`).
3. **Sign-cap-by-quality was invented complexity.** Tests had to construct hypothetical inputs to trigger the clamp. Phase 3 drops the floor/ceiling — additive composition with the documented coefficients keeps the range at `-15..+15`, well within the existing dynamic range. Two tests collapsed into the existing matrix.
4. **Engine title-routing logic over-engineered.** Three branches collapsed to: keep the existing quality title when `qualityDelta != 0`; otherwise emit a single generic `"Diet check-in logged"` title.
5. **Confidence downgrade added.** When only rhythm/anchor contribute (`qualityDelta == 0 && (rhythmDelta != 0 || anchorDelta != 0)`), the entry now writes `Confidence.low`, not `medium` — preserves the codebase's confidence-by-evidence invariant.
6. **Tone method renamed.** `roughDayRescueLine()` → `todayRescueBody()` to match the existing `<surface><Aspect>` naming convention (`wrapUpPositiveBody`, `todayInterpretation`).
7. **Tautological tests removed.** Dropped `testRoughDayRescueLine_AllThreeModesReturnNonEmpty`, `_ThreeLinesAreDistinct`, and `testDisclaimerBannerRendersOnce` — Swift's exhaustive switch + literal strings make them framework tests, and visual review catches paste-twice mistakes. Trigger-condition tests retained.
8. **Disclaimer placement strengthened.** Per App Review trends post-2024, lifespan-adjacent framing requires explicit "not a prediction, illustrative model only" copy **near the number itself**, not just bottom-of-scroll. Phase 5 now places a one-line caption immediately under the signed delta on Today, with the full `DisclaimerBanner` still mounted at the bottom of the scroll. Both render via the central `LifeClockConfiguration.medicalDisclaimer` so they stay in sync.
9. **Rescue line uses a separate `RescueLine` View struct** with `Equatable`-conformant inputs and `EmptyView()` for the false branch — best SwiftUI diffing per current community guidance, and unit-testable in isolation.
10. **TestFlight downgrade-loss risk documented.** A user on V1.2.0 who reinstalls V1.1.0 loses the new fields on next save. Acceptable given fields are user-recoverable per-day; documented in Risk Analysis.

### New considerations discovered

- **In-place `versionIdentifier` bump is non-canonical.** WWDC25 Session 291 + community consensus prefer chained `VersionedSchema` types with `MigrationStage.lightweight(...)`. The codebase has shipped two in-place bumps (V1.0 → V1.1) without incident, but the next non-additive change (rename, custom migration) will force a real V1/V2 split. Flagged as tech debt in Risk Analysis. Not in scope for this PR.
- **Disclaimer-fatigue mitigation strengthened.** Two render slots on Today (caption near delta + bottom banner) is more disclaimer surface than the prior single-banner plan. Both are short, both pull from the same canonical string, neither is full-card. Mitigation passes the 2026-04-30 audit's "no momentum-blocking banners after positive actions" rule because they're informational, not action-blocking.
- **`store.isAdultUser` returns `false` when DOB is unset.** A user who skipped DOB during onboarding sees no rhythm picker. Acceptable: rhythm is the more sensitive question. Documented in Phase 2.
- **Open Questions section removed.** All three questions resolved as "default-as-stated" in the prior round; carrying the section was noise.

---

## Overview

Four bundled changes to the daily check-in surface and surrounding copy:

- **(A) Diet rhythm axis** — split diet logging from one axis (`dietQuality`: great/okay/rough) into two by adding `dietAmountRhythm` (right / overate / undereate / skipBinge / irregular). Captures patterns the current model is blind to: skip-then-overeat, chronic undereating, irregular meals.
- **(B) Whole-food anchor** — one positive-framed question added to the daily check-in: "At least one solid whole-food meal today? (Yes / Almost / No)".
- **(C) Life-impact minutes framing** — edit the canonical `LifeClockConfiguration.medicalDisclaimer` to add explicit "not a lifespan prediction" language, and surface it on Today via the existing shared `DisclaimerBanner` (already used on QuickLog, Onboarding, Profile, SafetyNet, Paywall).
- **(D) Tone copy additions** — three new "patterns, not perfection" lines added to all three tone modes (`gentle`, `coach`, `firmDirect`) for a narrow rough-day-rescue trigger.

This is **not** a new feature surface. No new screens, no new tabs, no engine rewrite, no HealthKit/paywall changes. It is a daily-check-in expansion + a copy pass + a small additive engine refinement, all inside the existing ship-state.

## Problem statement

Three concrete gaps in the shipped product:

1. **Diet model is one-dimensional.** [QuickLogSheet.swift](products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) and [HabitLog (LifeClockSchema.swift:200)](products/life-clock-ios/Sources/Models/LifeClockSchema.swift) collapse all diet behavior into a 3-way `dietQuality` enum. [ClockEngine.dietDriver (ClockEngine.swift:447)](products/life-clock-ios/Sources/Engines/ClockEngine.swift) maps that directly to ±10/12-minute deltas. A user who skipped lunch and binged at 11pm has the same logging vocabulary as a user who ate three balanced meals — both can shrug "okay." The model can't see disordered-eating-adjacent rhythm patterns at all.

2. **Disclaimer copy is incomplete and unevenly placed.** The canonical [LifeClockConfiguration.medicalDisclaimer (Services/LifeClockConfiguration.swift:49)](products/life-clock-ios/Sources/Services/LifeClockConfiguration.swift) reads "It is not medical advice, diagnosis, treatment, or a forecast of lifespan…" — strong but spread across QuickLog, Onboarding, Profile, SafetyNet, and Paywall via the shared [DisclaimerBanner](products/life-clock-ios/Sources/Shared/DisclaimerBanner.swift). It does **not** appear on Today, which is where the signed minute count is shown daily and where the App Store-defensible framing matters most. The legacy [OnboardingView.swift:86](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift) toggle still uses an older one-line copy ("I understand Life Clock is not medical advice") that drifted from the canonical disclaimer.

3. **Tone copy lacks a "patterns, not perfection" anchor.** [ToneMode.swift](products/life-clock-ios/Sources/App/ToneMode.swift) has tone-modulated copy on wrap-ups, headlines, and several other surfaces, but **no dedicated rough-day rescue line** for the case where today netted negative AND a diet signal was the cause. This is the single highest-leverage missing line for users who break a streak — exactly where retention bleeds in habit apps.

## Non-goals

- Calorie / macro / barcode / meal-photo logging. Not now, not later.
- Touching the just-shipped reveal-onboarding flow. The new diet-amount baseline is **only** added to the daily check-in, not to onboarding. Onboarding's `UserProfile.dietQualityBaseline` stays as-is.
- Adding a disclaimer toggle to the reveal-onboarding flow. The flow currently sets `disclaimerAccepted: true` implicitly via [OnboardingCoordinator.swift:173](products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift) and renders `DisclaimerBanner()` on `paywallPrimary`. That decision stays. Only the legacy `OnboardingView` toggle gets a copy refresh.
- Reworking the engine's healthspan model. Diet-rhythm becomes a small additive modifier on the existing `dietDriver`, not a new top-level driver category.
- HealthKit / paywall / new tab / animation changes.
- Localization. Strings stay inline (matches current codebase).
- New analytics events. Daily check-in does not currently emit telemetry; this plan does not introduce any.

## Phases

### Phase 1 — Schema (V1.2.0 in-place version bump)

**Files:** [Sources/Models/LifeClockSchema.swift](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)

The repo uses a single `LifeClockSchemaV1` enum whose `versionIdentifier` is bumped in place (V1.0 → V1.1.0 already shipped under reveal-onboarding). There is **no `LifeClockSchemaV2`** to create — this is the codebase's convention for additive lightweight migrations.

Bump `versionIdentifier` from `(1, 1, 0)` → `(1, 2, 0)`. `LifeClockMigrationPlan.stages` stays `[]` (lightweight migration only).

Add to `HabitLog` (alongside the existing `dietQuality: String = "okay"` defaults at line 204):

```swift
// New in V1.2.0. Defaults match the codebase convention of *meaningful
// neutral values* — not sentinels — same pattern as
// dietQuality="okay", alcoholLevel="none", stressLevel="medium".
// "right" is the engine's zero-delta case for rhythm; "unknown" matches
// the existing token referenced at QuestEngine.swift:121.
var dietAmountRhythm: String = "right"     // "right" | "overate" | "undereate" | "skipBinge" | "irregular"
var wholeFoodMeal: String = "unknown"      // "yes" | "almost" | "no" | "unknown"
```

**Why non-optional with meaningful default, not `String?`:** matches existing `HabitLog` convention. Best-practices research notes Apple Forums reports of `String?`-on-existing-store quirks under explicit migration plans, but this codebase has `LifeClockMigrationPlan.stages = []` (no plan — pure inference), and the prior V1.0 → V1.1 add shipped the same pattern without incident. The [SwiftData mandatory-attribute migration landmine doc](docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md) requires every non-optional stored property to have a property-level default or migration silently no-ops on upgraded devices (NSCocoaErrorDomain 134110). The defaults above satisfy the invariant.

**Engine handling of defaults:** because `"right"` and `"unknown"` are now the on-disk defaults, the engine **must not** distinguish "user answered 'right'/'unknown'" from "user never logged" — both are zero contribution. This is consistent with the existing pattern: `dietQuality="okay"` already conflates default and explicit-okay-answer with zero delta.

**Migration tests:** the in-place `LifeClockSchemaV1` convention means the V1.1 shape no longer exists in the binary by the time tests run. The existing `testNewFieldsRoundTripThroughFileBackedStore` validates **codec round-trip**, not lightweight migration. To honestly verify V1.1 → V1.2:

1. **(Required, low effort)** Add `testHabitLogReadsBackDefaultsForUnsetFields` to `LifeClockSchemaMigrationTests.swift`: open file-backed container with V1.2 schema, write a `HabitLog` *without* setting the two new fields, close, reopen, assert defaults persisted. This is what the existing test pattern actually validates and is sufficient for the additive-only change.
2. **(Required, low effort)** Add `testSiblingFieldsRoundTripUnchanged`: assert `dietQuality`, `alcoholLevel`, `stressLevel`, `smokingVaping`, `strengthTraining`, `notes` all round-trip with their original values when read back through V1.2 schema. Catches a regression that would silently reset existing rows.
3. **(Mandatory before ship)** Manual install-over-previous device test per the SwiftData landmine doc: install a V1.1 build, log a HabitLog, upgrade to the V1.2 build, verify the prior row reads correctly with new fields defaulted. This is the only path that actually exercises lightweight migration end-to-end under the in-place-bump convention. Captured in Acceptance Criteria.
4. **(Optional, deferred)** Bundling a `Tests/Fixtures/v1_1_baseline.store` captured from a real V1.1 build would let CI exercise migration. High effort for one PR; flagged in Risk Analysis as future improvement.

**Pre-commit guard:** the existing grep recipe from the SwiftData landmine doc (`grep -nE '^\s*var\s+[a-zA-Z_][a-zA-Z0-9_]*:\s*(String|Bool|Int|Date|Double)\s*$'`) catches bare non-optional properties. The two new fields satisfy it; no new guard needed.

### Phase 2 — QuickLog UI

**Files:** [Sources/Features/QuickLog/QuickLogSheet.swift](products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift)

The existing UI labels its diet section "Fuel," not "Diet." Match that label.

Add two new sections after the existing "Fuel" section (ends ~line 64), before "Extras" (~line 65):

**Diet rhythm section** (gated to adults via `if store.isAdultUser`):

```
Section header: "Rhythm"
Subhead: "How much did you eat for your body's needs today?"
Picker (segmented):
  Right amount        → "right"
  A little too much   → "overate"
  A little too little → "undereate"
  Skipped then overate → "skipBinge"
  Irregular           → "irregular"
```

**Whole-food anchor section** (visible to all ages):

```
Section header: "Whole-food anchor"
Subhead: "At least one solid whole-food meal today?"
Picker (segmented):
  Yes    → "yes"
  Almost → "almost"
  No     → "no"
```

**Under-18 gate:** use `store.isAdultUser` (defined at [LifeClockStore.swift:60](products/life-clock-ios/Sources/App/LifeClockStore.swift)) — **not** the plan's previous `profile.ageYears < 18`. This is the existing convention used by alcohol/smoking suppression in QuickLog (line 107). When `isAdultUser == false`, the rhythm section is omitted entirely; the whole-food anchor stays visible (positively framed, ED-neutral).

**DOB-missing behavior:** `store.isAdultUser` returns `false` when DOB is unset, which means a user who skipped DOB during onboarding sees no rhythm section. Acceptable: rhythm is the more sensitive question. Whole-food anchor remains accessible to them.

**State plumbing:**
- Add `@State private var dietAmountRhythm: String = "right"` and `@State private var wholeFoodMeal: String = "unknown"` alongside lines 33-38.
- Hydrate in `hydrateFromStore()` (line 162) from `existing.dietAmountRhythm` / `existing.wholeFoodMeal`.
- Save in `save()` (line 170) by setting `habits.dietAmountRhythm = dietAmountRhythm` and `habits.wholeFoodMeal = wholeFoodMeal` before `await store.setTodayHabits(habits)`.

**Re-edit semantics:** opening QuickLog later in the same day pre-fills from the prior `HabitLog`. This matches the existing `dietQuality` re-edit path. No special handling needed.

**Sheet-dismiss vs save semantics:** dismiss-without-save discards in-memory state (existing pattern via the explicit Save button). No partial persistence.

**Accessibility:** new pickers get `accessibilityIdentifier` of `quickLog.dietAmountRhythm` and `quickLog.wholeFoodMeal` and `accessibilityValue` mirroring the selection (matches existing line ~ 25 pattern for `quickLog.dietQuality`).

### Phase 3 — Engine

**Files:** [Sources/Engines/ClockEngine.swift](products/life-clock-ios/Sources/Engines/ClockEngine.swift) (the existing `dietDriver(habits:date:)` at line 447)

Refactor `dietDriver` to compose three contributions into a single `TimeLedgerEntry`. Conservative deltas — this should not become a giant new lever.

```
quality contribution (unchanged signs/magnitudes):
  great   → +12
  okay    →   0   (also the "user never logged" case via default)
  rough   → -10

rhythm contribution (additive):
  right       →   0   (also the default — zero contribution)
  overate     →  -3
  undereate   →  -3
  skipBinge   →  -5
  irregular   →  -2

whole-food anchor contribution (additive):
  yes     →  +3
  almost  →  +1
  no      →   0
  unknown →   0   (default — zero contribution)
```

**Composition policy:**
- `composite = qualityDelta + rhythmDelta + anchorDelta`. Pure additive. No clamps.
- Range bounded by inputs: max negative `-10 + -5 + 0 = -15`; max positive `+12 + 0 + +3 = +15`. Both inside the existing driver dynamic range (sleep can swing >20). The "conservative" property is preserved by the small coefficients, not by clamps.
- `qualityDelta` already sets the dominant sign in every realistic combination. The earlier "sign-cap by quality" was reviewed as invented complexity — its tests had to construct hypothetical inputs (e.g. `+1 + -5`) the actual coefficients can't produce. Dropped.

**Short-circuit fix at line 468:** the existing code returns `nil` when `delta == 0` ("no neutral noise in the ledger"). Tighten this so it only fires when **all three** contributions are zero. New rule:

```swift
let composite = qualityDelta + rhythmDelta + anchorDelta
if composite == 0 && rhythmDelta == 0 && anchorDelta == 0 {
    return nil  // no diet signal at all → no ledger noise
}
// otherwise emit one TimeLedgerEntry with the composite delta
```

**Confidence policy:** when only rhythm or anchor contribute (`qualityDelta == 0 && (rhythmDelta != 0 || anchorDelta != 0)`), emit the entry at `Confidence.low` instead of the existing `Confidence.medium`. Preserves the codebase's confidence-by-evidence invariant — a self-report of rhythm without quality is weaker signal than a full quality answer.

**Title strings:** keep it simple. Two cases only:

```
qualityDelta != 0  → existing quality title ("Great diet quality logged" / "Rough diet quality logged")
qualityDelta == 0  → "Diet check-in logged"   (single generic title; shape matches existing "<noun phrase> logged" pattern)
```

Composite still emits exactly **one** `TimeLedgerEntry` per day. The downstream rendering branch at [TodayView.swift:216](products/life-clock-ios/Sources/Features/Today/TodayView.swift) (the `dietDriver.deltaMinutes > 0` celebration) keeps working unchanged — it checks the sign of the composite.

**Tests (new in `ClockEngineTests.swift`, four cases):**
- `testDietLegacyBehaviorWhenOnlyQualitySet` — given only `dietQuality` set (rhythm=`"right"`, anchor=`"unknown"`), composite equals the old single-axis delta exactly. Regression guard for existing user flows.
- `testDietRhythmContributesWhenQualityIsOkay` — `quality=okay, rhythm=skipBinge` produces a `-5` entry at `Confidence.low` (was previously `nil`). Validates both the line-468 short-circuit fix and the confidence-downgrade rule.
- `testDietAnchorContributesWhenQualityIsOkay` — `quality=okay, anchor=yes` produces a `+3` entry at `Confidence.low`. Symmetric to the rhythm test.
- `testDietAllDefaultsReturnsNil` — quality=`"okay"`, rhythm=`"right"`, anchor=`"unknown"` → returns `nil`. No ledger noise when nothing is signaled.

Other cases (great-day-with-skipBinge stays positive, rough-day-with-anchor stays negative, etc.) are arithmetic over the documented coefficients — Swift's exhaustive switch makes them tautological. Skipped.

### Phase 4 — Tone copy and rough-day rescue line (item D)

**Files:** [Sources/App/ToneMode.swift](products/life-clock-ios/Sources/App/ToneMode.swift), [Sources/Features/Today/TodayView.swift](products/life-clock-ios/Sources/Features/Today/TodayView.swift)

`ToneMode` is structured as per-property switches on `self`, not a copy table. **There is no existing motivational-line slot on the Today drivers card** — this plan adds one.

**Three tone modes exist** (per [ToneMode.swift:14-17](products/life-clock-ios/Sources/App/ToneMode.swift)): `gentle`, `coach`, `firmDirect`. All three must get a rough-day rescue line. (The earlier audit incorrectly listed only two modes — `firmDirect` is real and shipping per the 2026-05-01 commit `589ea81`.)

**Add a new method on `ToneMode`:**

```swift
/// Returns a tone-modulated "patterns, not perfection" line for use on
/// Today when the user logged a rough day driven by diet signals.
///
/// Method name follows the existing <surface><Aspect> convention
/// (compare: wrapUpPositiveBody, wrapUpNegativeBody, todayInterpretation).
/// Returns a string per `ToneMode` convention; the *trigger* lives in the
/// caller (TodayView), so this method is unconditional once invoked.
///
/// Per ToneMode's Foundation-only boundary, takes no parameters and
/// returns a primitive String.
func todayRescueBody() -> String {
    switch self {
    case .gentle:
        return "Rough day? Log it and move on. Tomorrow still counts."
    case .coach:
        return "You don't need a perfect diet. You need a repeatable one."
    case .firmDirect:
        return "Your Life Clock responds to patterns, not perfection."
    }
}
```

The three lines are tonally compatible with each mode (gentle = forgiving, coach = pragmatic, firmDirect = matter-of-fact).

**Trigger condition (caller-side):** the rescue is shown when:

```
netDeltaMinutes < 0
  AND (
    habits.dietQuality == "rough"
    OR habits.dietAmountRhythm == "skipBinge"
    OR habits.wholeFoodMeal == "no"
  )
```

Note: anchor=`no` alone is included as a trigger (an oversight in the prior plan). It's a meaningful negative signal even when quality is "okay."

**Where shown on Today:** add a new view in [TodayView.swift](products/life-clock-ios/Sources/Features/Today/TodayView.swift) **between** the existing `headline` (lines ~66-87) and the drivers card (~141). Caption-sized text, secondary color.

**Implementation pattern — separate `RescueLine` struct, not inline `if` or `@ViewBuilder`:**

```swift
private struct RescueLine: View, Equatable {
    let netDelta: Int
    let dietQuality: String
    let rhythm: String
    let anchor: String
    let tone: ToneMode

    private var shouldShow: Bool {
        netDelta < 0 &&
        (dietQuality == "rough" || rhythm == "skipBinge" || anchor == "no")
    }

    var body: some View {
        if shouldShow {
            Text(tone.todayRescueBody())
                .font(.caption)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("today.rescueLine")
        } else {
            EmptyView()
        }
    }
}
```

`Equatable` conformance lets SwiftUI's diffing skip body re-evaluation when inputs are unchanged (per current SwiftUI community guidance — the inline-`if` and computed-`some View` alternatives both re-run the parent's body on unrelated state changes). Add `.equatable()` at the call site if profiling shows wasted recomputation.

**Live recompute behavior:** the rescue line tracks the current `HabitLog` value. If the user re-opens QuickLog and changes "rough" → "okay," the rescue line disappears on next render. No "stuck banner" state. Multi-day: line is computed against today's HabitLog only.

**Tests (new in `Tests/ToneModeTests.swift` — file does not exist; create it):**
- `testTodayRescueBody_GentleReturnsLogItAndMoveOn` — gentle mode returns the specific gentle string. Pinning copy, not testing exhaustive switch.
- `testRescueLine_NegativeDeltaPlusRoughDietShows` — `RescueLine.shouldShow` is true when delta < 0 and quality == "rough".
- `testRescueLine_NegativeDeltaPlusSkipBingeShows` — same with rhythm == "skipBinge".
- `testRescueLine_NegativeDeltaPlusAnchorNoShows` — same with anchor == "no".
- `testRescueLine_PositiveDeltaSuppresses` — delta > 0 → `shouldShow` false even with rough diet. Edge case: HK steps drove a big positive on a rough-diet day.
- `testRescueLine_DeltaZeroSuppresses` — boundary: delta == 0 → `shouldShow` false.

(Tests for "all three modes return non-empty" and "three lines are distinct" removed as tautological — Swift's exhaustive switch + literal strings can't fail those silently. Code review catches them.)

### Phase 5 — Life-impact framing (item C)

**Files:** [Sources/Services/LifeClockConfiguration.swift:49](products/life-clock-ios/Sources/Services/LifeClockConfiguration.swift), [Sources/Features/Today/TodayView.swift](products/life-clock-ios/Sources/Features/Today/TodayView.swift), [Sources/Features/Onboarding/OnboardingView.swift:86](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift)

This is **only a copy and placement pass.** No data model change. No engine change.

**1. Edit canonical disclaimer copy.** `LifeClockConfiguration.medicalDisclaimer` already says "not medical advice…not a forecast of lifespan." Tighten to also use the framing the audit recommended:

```
Old: "It is not medical advice, diagnosis, treatment, or a forecast of lifespan…"
New: "Life-impact minutes are educational estimates based on population-level
      research. Life Clock is not medical advice, diagnosis, or treatment, and
      does not predict your lifespan."
```

This single edit propagates to **all five existing call sites** (QuickLog, legacy Onboarding, Profile, SafetyNet, Paywall) for free.

**2. Add disclaimer surface to TodayView in two short slots.** Today is the highest-frequency surface in the app and it currently does not show the disclaimer. Per App Review trends post-2024, lifespan-adjacent framing requires the "not a prediction, illustrative model only" copy **near the number itself** — bottom-of-scroll alone is insufficient for surfaces that show derived health metrics:

- **Slot A — short caption directly under the signed delta** (`TodayView.swift` ~line 75, immediately below the `TimeDeltaFormatter.format(minutes:)` render). Single line, `.caption2`, `.secondary` color: **"Educational estimate, not a lifespan prediction."** Pulled from a new `LifeClockConfiguration.lifespanShortDisclaimer` constant that's a 1-sentence sibling of `medicalDisclaimer`.
- **Slot B — full `DisclaimerBanner()` at the bottom of the Today scroll content.** The existing shared component, low-emphasis treatment, terminal position. Renders the full `medicalDisclaimer`.

**Disclaimer-fatigue mitigation:**
- Both slots are **informational, not action-blocking** — they pass the 2026-04-30 audit's "no momentum-blocking banners after positive actions" rule.
- Slot A is a single line; Slot B is the existing low-emphasis banner used on QuickLog/Profile/Paywall. Total disclaimer surface on Today is ~3 lines of caption text.
- No per-driver footer; no first-launch modal; no toggle on Today.
- Both slots pull from `LifeClockConfiguration` so copy stays in sync.

**Why two slots not one:** App Review has rejected health/lifespan apps where derived metrics appear on a tab with no nearby disclaimer and only a Settings-buried full disclaimer. The pattern that survives review is "short caption near the number + reachable full disclaimer." For an app whose central artifact is a signed minute count framed as "life-impact," this is the conservative posture before TestFlight submission.

**3. Update legacy `OnboardingView` toggle copy** ([OnboardingView.swift:86](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift)):

```
Old: "I understand Life Clock is not medical advice."
New: "I understand Life Clock provides educational estimates — not medical advice or a lifespan prediction."
```

[PHASE_STATUS.md](docs/products/life-clock/PHASE_STATUS.md) flags that the legacy `OnboardingView` is no longer reachable but still present, pending 48h TestFlight soak. Update its copy regardless — cheap, prevents drift if the kill-switch ever fires.

**4. Reveal-onboarding has no toggle to update.** [OnboardingCoordinator.swift:173](products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift) hardcodes `disclaimerAccepted: true` and renders `DisclaimerBanner()` on the paywall screen. The banner copy update from step 1 propagates into reveal-onboarding automatically.

**5. Where the unit "life-impact min" is displayed.** Today shows the signed delta via `TimeDeltaFormatter.format(minutes:)` at [TodayView.swift:75](products/life-clock-ios/Sources/Features/Today/TodayView.swift). The plan does **not** touch the formatter inline — Slot A's caption establishes the framing immediately under the number. No per-card unit rename.

**Tests (new):**
- `LifeClockConfigurationTests.testMedicalDisclaimerContainsLifeImpactPhrase` — string-presence assertion on the canonical `medicalDisclaimer`. Catches accidental rollback.
- `LifeClockConfigurationTests.testLifespanShortDisclaimerExists` — string-presence assertion on the new `lifespanShortDisclaimer` constant.

(Snapshot test for "banner renders once" dropped — that's a paste-twice mistake catchable by code review, not a behavior worth a test.)

### Phase 6 — Docs

**Files:** [docs/products/life-clock/CLOCK_MODEL.md](docs/products/life-clock/CLOCK_MODEL.md), [docs/products/life-clock/PHASE_STATUS.md](docs/products/life-clock/PHASE_STATUS.md)

1. Update `CLOCK_MODEL.md` "diet" section to document:
   - The two-axis diet model (quality + amount rhythm + whole-food anchor).
   - The conservative additive composition with sign-cap-by-quality.
   - The "missing data never penalizes" rule extended to all three fields.

2. Update `PHASE_STATUS.md` "Implemented" list with the new fields and "Resolved decisions" if relevant. Schema bump V1.1.0 → V1.2.0 should be noted in the same line that mentions V1.1.0 today (last paragraph of "Implemented").

3. **No changes** to the onboarding-funnel telemetry doc. Daily check-in is out of that doc's scope.

## System-wide impact

### Interaction graph

`QuickLog Save` → `LifeClockStore.setTodayHabits(habits)` → `HabitLog` upsert (SwiftData) → `LifeClockStore.recompute()` → `ClockEngine.computeDailyDelta(...)` → `dietDriver(habits:date:)` → composite `TimeLedgerEntry` → `LifeClockEstimate` row updated → `TodayView.@Observable` repaints → drivers card + new rescue-line slot re-evaluate the trigger.

The new fields ride this existing pipeline. No new pipeline, no new Observable boundary.

### Error & failure propagation

- **SwiftData migration failure** → app launches but persists nothing (the documented landmine). Mitigated by property-level defaults + the file-backed migration test. This is the only error path that could silently corrupt — every other path is in-memory SwiftUI state that can't fail invisibly.
- **Engine input out-of-range** → `default: return nil` fall-through inside the rhythm/anchor switches. Fail-quiet, never throw. Matches existing `dietDriver` style.
- **ToneMode rescue-line trigger evaluating against partial state** → the trigger reads three `String` fields, all of which always have a defined value (`"unset"` or the user's choice). No nil-check needed.

### State lifecycle risks

- **Schema migration on existing devices**: the only real risk. The existing `LifeClockSchemaMigrationTests` file-backed pattern catches it. Add the new test case BEFORE merging Phase 1.
- **17 → 18 birthday transition mid-history**: a user who first logged at age 17 (rhythm field absent because suppressed in UI; field stored as `"unset"` because it's the model-level default) will, on their 18th birthday, see the rhythm picker appear in QuickLog. Old rows stay `"unset"` (zero contribution). No retroactive backfill. Acceptable.
- **DailyCheckInMapping (Tests/DailyCheckInMappingTests.swift)** — verify mapping helpers don't rely on a closed-set assumption about `dietQuality` / `alcoholLevel`. The new fields are not currently mapped through `DailyCheckInMapping`; if they need to be (e.g. for future reflection prompts), that's a follow-up.

### API surface parity

- `LifeClockStore.setTodayHabits(_:)` is the single write API for HabitLog. No second path exists. Plan does not introduce one.
- The shared `DisclaimerBanner` is the single read surface for the disclaimer copy. Editing `LifeClockConfiguration.medicalDisclaimer` updates all five existing call sites + the new Today site automatically.
- `ToneMode` exposes per-tone copy via methods on the enum. The new `roughDayRescueLine()` follows that convention.

### Integration test scenarios

1. **End-to-end QuickLog → Today render**: open QuickLog as adult user, set quality=rough + rhythm=skipBinge + anchor=no, save, dismiss. Today should show the diet driver entry with the composite delta and the rescue line should appear in the new view section.
2. **End-to-end QuickLog as under-18 user**: same flow with `isAdultUser == false`. Rhythm section is not visible; whole-food anchor is. Save persists `dietAmountRhythm == "unset"` and the user's anchor choice.
3. **Migration from V1.1 fixture**: pre-V1.2 store with HabitLog rows containing only `dietQuality` opens under V1.2 schema; rows read back with `"unset"` defaults; `dietDriver` returns the legacy single-axis result; rescue line does not fire.
4. **Rescue line live-recompute**: log rough day → rescue line appears → re-open QuickLog, change quality from "rough" to "okay" → save → rescue line is gone on next render. (No stuck-state.)
5. **Disclaimer banner once-per-Today**: navigate to Today, scroll to bottom, verify exactly one `DisclaimerBanner` in the hierarchy. Navigate away and back, verify still exactly one.

## Acceptance criteria

### Functional

- [ ] `LifeClockSchemaV1.versionIdentifier == Schema.Version(1, 2, 0)`.
- [ ] `HabitLog` has `dietAmountRhythm: String = "right"` and `wholeFoodMeal: String = "unknown"`.
- [ ] `testHabitLogReadsBackDefaultsForUnsetFields` passes — file-backed round-trip confirms defaults persist.
- [ ] `testSiblingFieldsRoundTripUnchanged` passes — non-diet HabitLog fields round-trip with their original values.
- [ ] **Manual install-over-previous device test passes** — V1.1 build → V1.2 build with prior HabitLog rows preserved and new fields defaulted. Required before TestFlight submission.
- [ ] QuickLog shows the rhythm section iff `store.isAdultUser`.
- [ ] QuickLog shows the whole-food anchor section regardless of age.
- [ ] QuickLog re-edit pre-fills both new pickers from the stored `HabitLog`.
- [ ] `ClockEngine.dietDriver` returns at most one `TimeLedgerEntry` per day with the documented additive composite (no clamps).
- [ ] `dietDriver` returns `nil` only when all three contributions are zero (line-468 short-circuit fixed).
- [ ] When `qualityDelta == 0 && (rhythmDelta != 0 || anchorDelta != 0)`, the entry is emitted at `Confidence.low`, not `medium`.
- [ ] All four new `ClockEngineTests` cases pass.
- [ ] `ToneMode.todayRescueBody()` exists and returns a tone-modulated string for each of `gentle`, `coach`, `firmDirect`.
- [ ] Today renders `RescueLine` iff `netDelta < 0` AND any of (`quality=="rough"`, `rhythm=="skipBinge"`, `anchor=="no"`).
- [ ] `RescueLine` is implemented as a separate `View`-conforming struct with `Equatable` inputs, returning `EmptyView` when the predicate is false.
- [ ] Rescue line live-recomputes; re-edit from "rough" → "okay" hides the line on next render.
- [ ] `LifeClockConfiguration.medicalDisclaimer` contains "Life-impact minutes" and "not medical advice" and "does not predict your lifespan."
- [ ] `LifeClockConfiguration.lifespanShortDisclaimer` exists and contains "Educational estimate, not a lifespan prediction."
- [ ] Today shows the short-caption disclaimer immediately below the signed delta number, AND the full `DisclaimerBanner` at the bottom of the scroll.
- [ ] Legacy `OnboardingView` toggle uses the new copy.
- [ ] Reveal-onboarding flow continues to render `DisclaimerBanner` on `paywallPrimary` with the updated copy.

### Non-functional

- [ ] No new analytics events fire.
- [ ] No new third-party dependencies.
- [ ] Build remains iOS 17.0 deployment-target compatible.
- [ ] No new `@Query` sites; all reads/writes go through `LifeClockStore`.
- [ ] All existing tests (`LifeClockStoreTests`, `ClockEngineTests`, `LifeClockSchemaMigrationTests`, `OnboardingFlowIntegrationTests`, `OnboardingTelemetryTests`, etc.) still pass unchanged.
- [ ] Pre-merge: install-over-previous device test on a real device with a V1.1 store, per the SwiftData landmine doc's mandatory check.

### Quality gates

- [ ] New tests for engine composition matrix (8 cases).
- [ ] New `Tests/ToneModeTests.swift` file with 7 cases.
- [ ] New schema migration test paired with the existing file-backed pattern.
- [ ] `CLOCK_MODEL.md` and `PHASE_STATUS.md` updated.

## Risk analysis

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| SwiftData migration silently fails on existing devices | low | high | Property-level defaults + file-backed migration test + install-over-previous device test. Pattern matches the V1.0 → V1.1 add already in the codebase. |
| Two new questions hurt daily-check-in completion rate | medium | medium | Both are tap-to-select segmented pickers. Whole-food anchor is positive-framed. Total added time ≤ 5s. Watch completion rate post-TestFlight; if it drops, demote the rhythm question to a settings-gated opt-in. |
| Diet-rhythm framing feels ED-adjacent for under-18 | medium | high | Suppress rhythm entirely for under-18 via `store.isAdultUser`. Anchor stays — it's positively framed. Copy avoids "too much" / "too little" as moral terms; uses "for your body's needs." |
| Rhythm modifier double-penalizes rough days | low | low | Conservative additive coefficients keep range at -15..+15, inside existing driver range. No clamps needed. |
| Line-468 short-circuit regression | low | medium | `testDietRhythmContributesWhenQualityIsOkay` is the explicit guard. |
| ToneMode missing `firmDirect` line breaks build / surfaces empty string | very low | low | Switch on `ToneMode` is exhaustive in Swift; compiler enforces all-cases. |
| TestFlight downgrade-loss | low | low | A user on V1.2.0 reinstalling V1.1.0 loses `dietAmountRhythm` / `wholeFoodMeal` on next save. Acceptable: fields are user-recoverable per-day inputs. Document "no downgrade" in TestFlight release notes; optionally gate V1.2.0 behind a separate TestFlight group during initial soak. |
| Migration test as written validates only codec round-trip, not real V1.1→V1.2 lightweight migration | medium | medium | The in-place `LifeClockSchemaV1` convention makes a true file-backed migration test structurally impossible without a bundled `.store` fixture. Accepted for this PR; the manual install-over-previous device test (mandatory in acceptance criteria) is the real verification path. Bundled-fixture migration test flagged as future improvement. |
| In-place `versionIdentifier` bump pattern accumulates tech debt | low | medium | Codebase has shipped V1.0 → V1.1 in place without incident. The next non-additive change (rename, custom migration) will force a real `SchemaV1` / `SchemaV2` split per WWDC25 guidance. Out of scope for this PR; flag in `CLOCK_MODEL.md`. |
| Disclaimer fatigue worsens despite mitigation | low | medium | Banner placed bottom-of-scroll; no per-card footer; no above-the-fold treatment. UX-audit-2026-04-30 flagged the fatigue pattern; plan follows the audit's guidance. |
| Diet title strings drift from rest of `DayDetailView` | low | low | Plan keeps existing short metric-shaped titles ("Rough diet quality logged"). No human-friendly title experiments. |
| Existing dead test (`ClockEngineTests:148` writes `dietQuality = "poor"`) hides regressions | low | low | Out of scope for this PR. Note for future cleanup. |
| iOS 17 API boundary violation | very low | high | Plan uses no Calendar / date-arithmetic APIs. No iOS 18-only surface in scope. |

## Sources & references

### Origin

- **Brainstorm audit:** ChatGPT brainstorm from 2026-05-01, audited against actual reveal-onboarding ship-state. Items A–D (rhythm axis, anchor, life-impact framing, three tone lines) were the four scoped changes that survived audit. Items rejected: dropping HealthKit, retargeting 17–25, two-plan paywall rework, 15-screen onboarding rewrite, calorie-tracking surface.

### Internal references

- [docs/products/life-clock/PHASE_STATUS.md](docs/products/life-clock/PHASE_STATUS.md) — current ship state including reveal-onboarding (V1.1.0), single-tier paywall, two tone modes (firmDirect added 2026-05-01).
- [docs/products/life-clock/CLOCK_MODEL.md](docs/products/life-clock/CLOCK_MODEL.md) — current diet model (single-axis).
- [docs/products/life-clock/ux-audit-2026-04-30.md](docs/products/life-clock/ux-audit-2026-04-30.md) — disclaimer fatigue finding that this plan follows.
- [docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md](docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md) — the schema-V1.1.0 add and the in-place-version-bump convention.
- [docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md](docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md) — property-level default invariant + file-backed migration test pattern + install-over-previous device test.
- [products/life-clock-ios/Sources/Models/LifeClockSchema.swift](products/life-clock-ios/Sources/Models/LifeClockSchema.swift) — `HabitLog` @Model.
- [products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift](products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) — daily check-in sheet.
- [products/life-clock-ios/Sources/Engines/ClockEngine.swift](products/life-clock-ios/Sources/Engines/ClockEngine.swift) — `dietDriver` at line 447.
- [products/life-clock-ios/Sources/App/ToneMode.swift](products/life-clock-ios/Sources/App/ToneMode.swift) — three tone modes, per-property switches.
- [products/life-clock-ios/Sources/Features/Today/TodayView.swift](products/life-clock-ios/Sources/Features/Today/TodayView.swift) — Today screen, signed-delta render.
- [products/life-clock-ios/Sources/Services/LifeClockConfiguration.swift](products/life-clock-ios/Sources/Services/LifeClockConfiguration.swift) — canonical disclaimer copy at line 49.
- [products/life-clock-ios/Sources/Shared/DisclaimerBanner.swift](products/life-clock-ios/Sources/Shared/DisclaimerBanner.swift) — shared banner component.
- [products/life-clock-ios/Sources/App/LifeClockStore.swift](products/life-clock-ios/Sources/App/LifeClockStore.swift) — `isAdultUser` at line 60.
- [products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift](products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift) — two-tier test pattern to mirror.
- [products/life-clock-ios/Tests/ClockEngineTests.swift](products/life-clock-ios/Tests/ClockEngineTests.swift) — engine tests.
- [products/life-clock-ios/Tests/DailyCheckInMappingTests.swift](products/life-clock-ios/Tests/DailyCheckInMappingTests.swift) — closest existing pattern for QuickLog-adjacent logic.

## Estimated scope

Single PR, ~7 files modified + ~3 test files modified or created. No new screens. No new dependencies. No StoreKit / HealthKit / paywall / new-tab surface area touched.
