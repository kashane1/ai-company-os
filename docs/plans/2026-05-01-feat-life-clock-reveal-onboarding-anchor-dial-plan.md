---
title: Brainrot-modeled Life Clock onboarding rebuild + healthspan anchor dial
type: feat
status: active
date: 2026-05-01
origin: docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md
---

# Brainrot-modeled Life Clock onboarding rebuild + healthspan anchor dial

## Enhancement Summary

**Deepened on:** 2026-05-01 (same day as initial draft)
**Sections enhanced:** Architecture, all 9 phases, Risk Analysis, Acceptance Criteria, Sources.
**Research agents used:** architecture-strategist, code-simplicity-reviewer, data-integrity-guardian, data-migration-expert, performance-oracle, security-sentinel, pattern-recognition-specialist, spec-flow-analyzer, best-practices-researcher, framework-docs-researcher.

### Key Improvements

1. **Two-stage paywall + "I'd rather pay full price" → SINGLE-TIER PAYWALL + intro pricing.** Cal AI was pulled from the App Store in April 2026 for the exact pattern originally proposed (Guidelines 3.1.2(c) + 5.6 — manipulative purchase flow, second-paywall-after-decline). Brainrot ships it but the rejection precedent is now documented. Replaced with a single paywall (annual/monthly toggle, equal-prominence pricing, visible auto-renewal terms) backed by App Store Connect introductory pricing for new subscribers — no JWS signing infrastructure required. (Source: [TechCrunch — Cal AI App Store crackdown, April 2026](https://techcrunch.com/2026/04/21/apples-cal-ai-crackdown-signals-its-still-policing-the-app-store/).)
2. **UserDefaults draft persistence STRUCK.** Storing `parentMotherAgeAtDeath`, `perceivedStressScore`, and `lonelinessScore` in UserDefaults — even transiently — leaks PII to iCloud device backup and violates the on-device privacy stance set by `cloudKitDatabase: .none`. Drop the persistence entirely; mid-onboarding crash = restart. (Confirmed independently by data-integrity-guardian and security-sentinel.)
3. **`applyAnchorAdjustment` race fix.** Original plan had two writes (`personalAdjustmentYears`, `anchorAdjustedAt`) under one `try? save()` — kill in between leaves the dial half-applied. Engine now gates the adjustment read on `anchorAdjustedAt != nil`, making the pair logically atomic.
4. **Telemetry hardened.** Switch `OSLogTelemetry` from `os_log` (default `%{public}s`) to `Logger` with `privacy: .private` on every value parameter (`choiceMade`, `dialAdjusted`, `purchased`). Sensitive PSS/UCLA scores get bucketed (`low/medium/high`) before logging. Add a hard rule in the protocol contract: keys public, values private.
5. **NavigationStack(path:) instead of hand-rolled screen-switch coordinator.** Existing codebase uses `NavigationStack` per feature root (`TodayView.swift:8`, `HistoryView.swift:22`); the original plan would have introduced a third pattern. Now uses `NavigationStack(path:)` + `.navigationDestination(for: OnboardingScreen.self)` — back-nav free, runningEstimate recompute on pop is automatic, matches the rest of the codebase.
6. **`.contentTransition(.numericText(value:))` replaces custom `AnimatedNumberView`.** iOS 17+ built-in primitive. Saves an entire component file + tests.
7. **Phase 1 splits into 1a (schema migration, irreversible) + 1b (engine + telemetry, reversible).** Migration is the highest-risk change in the whole plan; landing it standalone protects users if Phase 1b needs a rollback.
8. **Phase 8 (cold open + previews) moves to *before* Phase 4** so the coordinator's `OnboardingScreen` enum is wired up once, not twice.
9. **Phases 6 + 7 merge into a single paywall phase** (no separate ritual phase). Drops `CommitmentRitualView` (unproven, dark-pattern smell, gesture-detection maintenance burden), `LoadingPremiumView` (second fake-progress in one flow is App Store review smell), and `RatingAskView` mid-onboarding (Apple's rate-limited `requestReview` is wasted on pre-purchase users). `ResearchCredibilityView` becomes a tappable "How is this calculated?" link on the reveal screen, not a dedicated screen.
10. **EngineClock injection aligns to codebase pattern.** Original plan would have introduced `@Environment(\.engineClock)`; codebase uses init-parameter or `store.clock` access (e.g. [TimeLedgerView.swift:4](products/life-clock-ios/Sources/Features/TimeLedger/TimeLedgerView.swift), [QuestsView.swift:4](products/life-clock-ios/Sources/Features/Quests/QuestsView.swift)). Aligned.
11. **`PaywallProductsView` shared core extracted.** Single source of truth for product list, restore, §3.1.2 fineprint, `isPro`-flip auto-dismiss. `PaywallSheet` (re-engagement) and `PaywallPrimaryView` (onboarding) are thin wrappers around it.
12. **Schema bumps to `Schema.Version(1, 1, 0)`** for traceability — lightweight migration still applies, free metadata.
13. **Concrete file-backed migration test (not in-memory)** specified with code. In-memory containers never exercise lightweight migration — known false-negative trap per the landmine doc.
14. **GDPR Art. 9 consent UI** added as a priming screen before the family-longevity / stress / social blocks. PSS-10 / UCLA-3 / parental-mortality data is special-category under GDPR, requires explicit (not implicit) consent.
15. **HealthKit `Info.plist` audit task added to Phase 4.** Moving the auth screen requires `NSHealthShareUsageDescription` to accurately match the new "let your clock learn from your body" copy (Guideline 5.1.1(ii) — mismatched purpose strings reject).
16. **Reduce Motion gaps closed** for dial drag (snap to nearest 0.5 yr), 3-bar fake progress (collapse to 1.5s gate), recovery cycling (slower not faster — 3s/word).
17. **Spec-flow gaps filled**: back-nav from `engineRevealAndDial` (pre-confirm: dial resets; post-confirm: back disabled), HealthKit decline routing, force-quit-during-analyzing (always restart timer), under-18 user flow, both-parents-lost-young soft framing, "just curious" softening, offline-at-paywall, reinstall-with-existing-profile rule.
18. **Acceptance criteria tightened**: every "Spot-check 5 random screens" → grep-based hard gate; every numeric metric → measurement method specified.

### New Considerations Discovered

- **Strikethrough pricing must reflect a real prior price** (FTC guidance + Apple 3.1.1). If $11.99 is the only price ever offered, the strikethrough is deceptive. Tie founding-offer eligibility to a real cohort window enforced via App Store Connect intro pricing.
- **HealthKit completion `Bool` LIES.** `success: true` from `requestAuthorization` only means the sheet completed — not that anything was granted. Read permissions are deliberately opaque to apps (Apple privacy design). Don't infer grant state; query the data and handle empty results.
- **Apple won't re-prompt after decline.** If user declines HealthKit on the new auth screen, the only recovery is `UIApplication.openSettingsURLString`. Surface a "Open Settings" affordance in Profile.
- **Schema rollback is theoretical.** Apple doesn't allow user-initiated downgrades from a higher build; external rollback (developer pulls build) means new installers get V1 fresh. Document as "no supported downgrade path."
- **GDPR Art. 17 right-to-erasure** will become real when any analytics backend lands. Telemetry events including sensitive choice values must be aggregated/hashed before transport, or gated behind a consent toggle defaulted off in EU regions. Out of scope for this plan but flag for the analytics-backend plan.

## Overview

Replace the existing 7-step Life Clock onboarding ([OnboardingView.swift:39](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift)) with a ~25-screen flow modeled on Brainrot's $200K/mo onboarding pattern, ending in a personalized healthspan reveal that the user can fine-tune once via a bounded ±5-year **healthspan dial**, followed by a single-tier paywall with introductory pricing for new subscribers (the original two-stage / discount-overlay design was dropped during deepening — see Enhancement Summary §1). Extends `ClockEngine` ([ClockEngine.swift:19-79](products/life-clock-ios/Sources/Engines/ClockEngine.swift)) with five new lifestyle factors (BMI, cardio mins/week, family longevity, perceived stress, social connection). Adds a goal-driven persona archetype reveal, a reactive number that animates as the user answers, a five-step emotional escalator built on Life Clock's existing dot-grid mortality metaphor, and a one-time post-engine adjustment that becomes the user's personal Life Clock for the lifetime of the install.

(All design decisions carried forward from the brainstorm: see [docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md](docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md).)

## Problem Statement

Today's onboarding collects DOB and lifestyle inputs in 7 steps but the final "Reveal" screen ([OnboardingView.swift:261-269](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift)) is **static copy** — the personalized estimate that `ClockEngine.calculateBaseline` ([ClockEngine.swift:19-33](products/life-clock-ios/Sources/Engines/ClockEngine.swift)) already computes is never surfaced. The paywall ([PaywallSheet.swift](products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift)) is purely soft-gated, triggered only from Profile and locked-row taps in History; it never fires at the moment of peak emotional buy-in. `MONETIZATION.md:75-83` explicitly says "after first Life Clock reveal" should be the first conversion moment — but the reveal screen never delivers a clock estimate. There is also no path for a user to correct an inaccurate clock except a destructive "delete all data" reset.

The combined effect: free users finish onboarding without having seen the headline value of the product, and the paywall asks for money in a context divorced from any locked-in personal number.

## Proposed Solution

A nine-phase rebuild that:

1. Extends `UserProfile` and `ClockEngine` to capture and weight five new lifestyle factors with bounded, sourced coefficients.
2. Introduces a reactive estimate that animates per-answer with a one-line "why" caption.
3. Adds a five-step emotional escalator using Life Clock's existing dot-grid mortality metaphor as a first-class element — the metaphor Brainrot is *borrowing*, we already own.
4. Reveals a personalized healthspan estimate paired with a one-time, bounded ±5-year **healthspan dial** that the user can use to express gut-feel calibration the engine cannot capture.
5. Repositions HealthKit auth to immediately after the reveal+dial moment (high commitment, higher grant rate).
6. Replaces the post-onboarding paywall with a single-tier end-of-onboarding paywall (annual/monthly toggle, equal-prominence pricing, visible auto-renewal) backed by App Store Connect introductory pricing for new subscribers. (The original brainstorm decision was a two-stage paywall with a discount overlay; dropped during deepening after Cal AI was pulled from the App Store in April 2026 for the same pattern — see Enhancement Summary §1.)
7. Reuses the existing free vs Pro split from `MONETIZATION.md` so users land in the existing app post-paywall regardless of conversion outcome, with their locked-in clock and dial value visible.

**Critical tone constraint** (carried forward from brainstorm + `CLAUDE_HANDOFF.md:57-59`): the brainstorm chose "Full Brainrot" tactics, but Life Clock's founder rules require "agency over fear, no doom default, no medical claims." This plan resolves the tension by **adopting Brainrot's structural patterns** (escalator, archetype, fake-progress) **while adapting all copy** to agency framing AND **dropping the most aggressive Brainrot tactics** (two-stage paywall + discount overlay, commitment ritual, in-flow rating ask, second fake-progress) per deepening research — see Enhancement Summary §1, §9 (`see brainstorm: docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md`). Concretely:

| Brainrot copy | Life Clock copy |
|---------------|-----------------|
| "Your brain is being exploited" | "Most days slip through unnoticed" |
| "25 years rotting on this phone" | "~25 years of untracked time, on average" |
| "Get 18 years back" | "Showing up could add ~18 years" |
| "It's not about willpower" | "Visibility is the system" |
| "Limited time offer" | "Founding offer — first 30 days" |

CI grep gates ([CLAUDE_HANDOFF.md:38-46](docs/products/life-clock/CLAUDE_HANDOFF.md)) prohibit "diagnose/prescribe/guarantee/predict" in user-facing copy; all new screens MUST be reviewed against this list before merge.

## Technical Approach

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  OnboardingCoordinator                                               │
│    NavigationStack(path: $path)                                      │
│    .navigationDestination(for: OnboardingScreen.self) { … }          │
│  Holds @Observable OnboardingDraft (transient, not persisted)        │
└────────────┬─────────────────────────────────────────────────────────┘
             │
   ┌─────────┼─────────┐
   ▼         ▼         ▼
┌────────┐ ┌────────────────────┐ ┌────────────────────┐
│ Cold   │ │ Reactive question  │ │ EngineReveal +     │
│ open + │→│ screens (DOB, sex, │→│ HealthspanDial     │
│ app    │ │ BMI, smoking, …,   │ │ (one-time ±5 yrs)  │
│ preview│ │ goal, archetype)   │ └─────┬──────────────┘
└────────┘ └─────────┬──────────┘       │
                     │                  ▼
                     ▼                ┌──────────┐    ┌────────────┐
              OnboardingDraft         │ HealthKit│    │ Single-    │
              .runningEstimate ←──────│ Auth     │───→│ Paywall +  │
                     │                │ (priming │    │ Intro Offer│
                     │                │  screen) │    └─────┬──────┘
                     │                └──────────┘          │
                     ▼                                      ▼
              ClockEngine.partialEstimate(draft)    Free / Pro app
                     │                              (PaywallProductsView
                     ▼                               shared core)
              ClockEngine.computeArchetype(draft)
                     │
                     ▼
              ClockEngine.calculateBaseline(profile)
                     ↑
                     │ honors personalAdjustmentYears
                     │ ONLY IF anchorAdjustedAt != nil
                     │ (atomic gate — race-free)
```

Key new types:

- `OnboardingDraft` (`@Observable`, transient — not persisted, no UserDefaults, no draft recovery)
- `OnboardingScreen` enum (~25 cases — see Phase 4) used as the `NavigationStack` path value type
- `OnboardingTelemetry` protocol + `OSLogTelemetry` (built on `Logger` with `privacy: .private` on values; Phase 1b)
- `Archetype` enum: `.marathoner`, `.sprinter`, `.sleeper`, `.outlier` (per brainstorm)
- `OnboardingGoal` enum: `.liveLonger`, `.moreEnergy`, `.beThereForFamily`, `.beatFamilyHistory`, `.justCurious` (per brainstorm)
- `LifeGridDotView`, `ClockMascotView` (Phase 3 — `AnimatedNumberView` is no longer a standalone component; built-in `.contentTransition(.numericText(value:))` replaces it)
- `EngineRevealAndDialView` (Phase 5)
- `PaywallProductsView` (shared core: product list, restore, §3.1.2 fineprint, `isPro`-flip auto-dismiss)
- `PaywallPrimaryView` (Phase 7 — onboarding wrapper around `PaywallProductsView`, single tier with annual/monthly toggle)
- `PaywallSheet` (existing, becomes thin wrapper around `PaywallProductsView` for re-engagement)

### Implementation Phases

#### Phase 1a: Schema migration (irreversible — ship standalone)

**Files:**
- `products/life-clock-ios/Sources/Models/LifeClockSchema.swift`
- `products/life-clock-ios/Tests/LifeClockSchemaMigrationTests.swift` (new)

**Why standalone:** schema migration is the highest-risk change in the entire plan. Per the `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md` recurrence pattern, a bad migration silently no-ops and corrupts every install. Land this PR alone, soak in TestFlight ≥48h, then proceed to 1b.

**Tasks:**

- [ ] **Bump `LifeClockSchemaV1.versionIdentifier` from `Schema.Version(1, 0, 0)` to `Schema.Version(1, 1, 0)`** ([LifeClockSchema.swift:16](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)). Lightweight migration still applies (semver patch/minor doesn't trigger a stage). Free traceability for future archaeology.

- [ ] **Add new optional fields to `UserProfile`** ([LifeClockSchema.swift:30-87](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)). All MUST be optional or have property-level defaults per the in-file rule at `:5-13` and per the SwiftData migration landmine docs/solutions doc:
  ```swift
  // Cardio is the gap — strengthFrequencyPerWeek already exists
  var cardioMinsPerWeek: Int = 0
  // Family longevity (sensitive — "prefer not to say" → nil)
  var parentMotherAlive: Bool? = nil
  var parentMotherAgeAtDeath: Int? = nil
  var parentFatherAlive: Bool? = nil
  var parentFatherAgeAtDeath: Int? = nil
  // Stress & social — note `stressBaseline` (String enum) already exists; keep
  // and ADD numeric scores for finer-grained engine input
  var perceivedStressScore: Int? = nil   // 0–40 (PSS-10 short form)
  var lonelinessScore: Int? = nil        // 3–9 (UCLA-3)
  // Goal + archetype (raw strings; decoded via fromStored helper pattern)
  var primaryGoal: String? = nil         // OnboardingGoal.rawValue
  var archetype: String? = nil           // Archetype.rawValue
  // Healthspan dial — the heart of this feature
  var personalAdjustmentYears: Double? = nil
  var anchorAdjustedAt: Date? = nil
  // Migration signal for existing users (pre-rebuild) vs new users
  var onboardingV2CompletedAt: Date? = nil
  ```
  No `MigrationStage` needed; lightweight migration handles all of these. (See `swiftdata-mandatory-attribute-migration-landmine.md`.)

- [ ] **Note**: `heightCm` and `weightKg` already exist on `UserProfile` (`LifeClockSchema.swift`) — body composition is captured but never used in the engine. No new fields for body comp; just wire them into the engine.

- [ ] **Verification: file-backed migration test (NOT in-memory).** In-memory `ModelContainer` configurations never exercise lightweight migration — known false-negative trap per the landmine doc. Add `Tests/LifeClockSchemaMigrationTests.swift`:
  ```swift
  import XCTest
  import SwiftData
  @testable import LifeClock

  final class LifeClockSchemaMigrationTests: XCTestCase {
    func testV1SeededStoreOpensCleanlyUnderV1_1() throws {
      let storeURL = URL.temporaryDirectory
        .appendingPathComponent("migration-\(UUID()).store")
      defer { try? FileManager.default.removeItem(at: storeURL) }

      let config = ModelConfiguration(url: storeURL, cloudKitDatabase: .none)
      let container = try ModelContainer(
        for: UserProfile.self, DailyHealthSnapshot.self, HabitLog.self,
             LifeClockEstimate.self, TimeLedgerEntry.self,
             Quest.self, WeeklyReport.self,
        migrationPlan: LifeClockMigrationPlan.self,
        configurations: config
      )
      let ctx = ModelContext(container)
      let profile = UserProfile(birthDate: Date(timeIntervalSince1970: 0))
      ctx.insert(profile)
      try ctx.save()

      // Reopen — simulates upgrade-launch path
      let container2 = try ModelContainer(
        for: UserProfile.self, DailyHealthSnapshot.self, HabitLog.self,
             LifeClockEstimate.self, TimeLedgerEntry.self,
             Quest.self, WeeklyReport.self,
        migrationPlan: LifeClockMigrationPlan.self,
        configurations: config
      )
      let ctx2 = ModelContext(container2)
      let fetched = try ctx2.fetch(FetchDescriptor<UserProfile>())
      XCTAssertEqual(fetched.count, 1)
      let p = try XCTUnwrap(fetched.first)

      // New optional fields backfill as nil
      XCTAssertNil(p.parentMotherAlive)
      XCTAssertNil(p.perceivedStressScore)
      XCTAssertNil(p.personalAdjustmentYears)
      XCTAssertNil(p.anchorAdjustedAt)
      // New non-optional with default
      XCTAssertEqual(p.cardioMinsPerWeek, 0)
    }
  }
  ```
  For a fully realistic V1 → V1.1 migration test, commit a binary V1 store fixture (built via `git checkout main` of pre-Phase-1a code) into `Tests/Fixtures/` and open under V1.1. The above test verifies the lightweight path is registered and additive fields don't break load — sufficient pre-merge insurance per the landmine doc's §3 checklist.

- [ ] **App Store privacy disclosure update.** `parentMotherAgeAtDeath`, `parentFatherAgeAtDeath`, `perceivedStressScore`, `lonelinessScore` are health-adjacent / sensitive data classes under [Apple's privacy taxonomy](https://developer.apple.com/app-store/app-privacy-details/). Even though stored on-device only (`cloudKitDatabase: .none`), they must be declared in App Store Connect → Privacy → Data Types. Declare as: Health & Fitness / Sensitive Info / Other Data, purpose = App Functionality, linkage = Not linked to identity, tracking = No.

**Definition of done for Phase 1a**: schema migrates cleanly on a V1-seeded simulator (file-backed test passes), App Store Connect privacy declaration updated, no engine or UI changes shipped yet.

---

#### Phase 1b: Engine math + telemetry (reversible, follows 1a)

- [ ] **Extend `ClockEngine.lifestyleAdjustmentYears`** ([ClockEngine.swift:44-74](products/life-clock-ios/Sources/Engines/ClockEngine.swift)) with five new branches BEFORE the existing `return adjustment`:
  ```swift
  // BMI (NHANES + Global BMI Mortality Collaboration 2016)
  if let bmi = profile.bmi {
    switch bmi {
    case ..<18.5: adjustment -= 1.5
    case 18.5..<25: adjustment += 0.0
    case 25..<30: adjustment -= 0.5
    case 30..<35: adjustment -= 2.0
    case 35...: adjustment -= 4.0
    default: break
    }
  }
  // Cardio mins/week (PA Guidelines 2018; Lee et al. 2014)
  switch profile.cardioMinsPerWeek {
  case 0: adjustment -= 1.0
  case 1..<150: adjustment += 0.5
  case 150...300: adjustment += 1.5
  case 301...: adjustment += 2.0
  default: break
  }
  // Family longevity (Sebastiani et al. 2012; Atzmon et al. 2010)
  if let mAge = profile.parentMotherAgeAtDeath, mAge >= 90 { adjustment += 1.0 }
  if let fAge = profile.parentFatherAgeAtDeath, fAge >= 90 { adjustment += 1.0 }
  if let mAge = profile.parentMotherAgeAtDeath, mAge < 65 { adjustment -= 1.0 }
  if let fAge = profile.parentFatherAgeAtDeath, fAge < 65 { adjustment -= 1.0 }
  // Perceived stress (Cohen 1988 PSS-10; Holt-Lunstad meta 2010)
  if let pss = profile.perceivedStressScore {
    switch pss {
    case 27...: adjustment -= 1.5
    case 14..<27: adjustment -= 0.5
    default: break
    }
  }
  // Loneliness (Holt-Lunstad meta-analysis 2015)
  if let ucla = profile.lonelinessScore, ucla >= 6 { adjustment -= 1.5 }
  ```
  Bounded total: ±10 years from lifestyle. Engine baseline (CDC FastStats) at `:36-42` unchanged. Coefficients are tuning placeholders (see existing `:65-66`); cite sources in docstrings, not in user-facing copy. **Don't use the words "predict," "diagnose," "prescribe," or "guarantee" in any docstring or comment that could read as a medical claim.**

- [ ] **Add `ClockEngine.partialEstimate(draft:)`** for the reactive harness — same math but accepts an `OnboardingDraft` with optional fields and returns the running estimate without writing to `UserProfile`. Used by Phase 2.

- [ ] **Add `ClockEngine.computeArchetype(profile:)`** returning a tuple:
  ```swift
  struct ArchetypeResult {
    let archetype: Archetype  // .marathoner | .sprinter | .sleeper | .outlier
    let behavioralRisk: Double   // 0.0–1.0 sub-meter
    let recoveryCapacity: Double // 0.0–1.0 sub-meter
  }
  ```
  Decision logic (transparent, rules-based per `CLOCK_MODEL.md`):
  - Compute behavioralRisk from (smoking, alcohol, BMI, cardio, sleep, diet) — 0=ideal, 1=worst
  - Compute geneticAnchor from family longevity (when known) — 0=poor, 1=excellent
  - `.marathoner` if behavioralRisk ≤ 0.3 (steady, well-paced)
  - `.sprinter` if behavioralRisk > 0.6 AND age < 50 (high acute risk, recoverable)
  - `.sleeper` if behavioralRisk > 0.4 AND geneticAnchor < 0.5 (huge upside if engaged)
  - `.outlier` if geneticAnchor > 0.7 AND behavioralRisk > 0.4 (genetics carrying weight)
  - Default fallback: `.marathoner`
  - Recovery capacity = 1 - behavioralRisk (engine treats current behavior as proxy for recoverability)

- [ ] **Add `OnboardingTelemetry` protocol** (new file `Services/OnboardingTelemetry.swift`). **Use `Logger` (OSLog 2.0) with `privacy: .private`** on every value parameter — default `os_log` interpolation marks dynamic strings as `%{public}s` which persists in unified logs and is retrievable via Console.app, sysdiagnose, MDM log capture, and `log collect`. That's a PII leak vector for sensitive choices. The protocol contract: **keys public, values private.**
  ```swift
  import OSLog

  protocol OnboardingTelemetry {
    func screenAppeared(_ screen: String)
    func screenAdvanced(_ screen: String, durationMs: Int)
    func choiceMade(_ screen: String, key: String, valueBucket: String) // bucketed, never raw
    func dialAdjusted(yearsBucket: String) // e.g. "neg5_neg2", "neg2_neg1", …, "pos2_pos5"
    func paywallShown(stage: PaywallStage)
    func paywallDismissed(stage: PaywallStage, reason: PaywallDismissReason)
    func purchased(productID: String)
  }

  struct OSLogTelemetry: OnboardingTelemetry {
    private let logger = Logger(subsystem: "com.lifeclock.app", category: "Onboarding")

    func choiceMade(_ screen: String, key: String, valueBucket: String) {
      logger.info("""
        choice screen=\(screen, privacy: .public) \
        key=\(key, privacy: .public) \
        value=\(valueBucket, privacy: .private)
        """)
    }
    // ... other methods follow the same pattern: keys public, values private.
  }

  struct StubTelemetry: OnboardingTelemetry { var events: [String] = [] }
  ```
  **Bucketing rule:** raw PSS-10, UCLA-3, parent ages-at-death MUST NEVER be passed to `valueBucket`. Compute the bucket at the call site (e.g. `pss < 14 ? "low" : pss < 27 ? "medium" : "high"`) before calling `choiceMade`. Add a unit test that asserts no raw integer ever appears in the logger sink.

  Wire via init parameter on `OnboardingCoordinator` (matches existing pattern — see [TimeLedgerView.swift:4](products/life-clock-ios/Sources/Features/TimeLedger/TimeLedgerView.swift) for how the codebase plumbs services through views via `@Environment(LifeClockStore.self)` rather than custom env values). Default to `OSLogTelemetry` in app, `StubTelemetry` in tests.

- [ ] **Tests** (`Tests/ClockEngineTests.swift`):
  - BMI penalty boundary cases (17.9 / 18.5 / 24.9 / 25.0 / 29.9 / 30.0)
  - Cardio mins/week boundary cases (0 / 1 / 149 / 150 / 300 / 301)
  - Family longevity all four corners (both parents alive, both unknown, one < 65 other > 90, both unknown — should not adjust)
  - PSS boundary cases (13/14/26/27)
  - UCLA boundary cases (5/6)
  - All-five-new-factors-zero → equals current baseline (regression)
  - Archetype assignment for each archetype + fallback
  - Idempotency: `calculateBaseline(profile)` returns same value for same inputs (regression — already exists at [ClockEngineTests.swift:14](products/life-clock-ios/Tests/ClockEngineTests.swift))
  - Telemetry: `StubTelemetry` records events in order; assert no raw PSS/UCLA/age value ever appears (PII guard)
  - **Boundary tests for BMI + cardio (load-bearing curves)**, but DROP per-bucket boundary tests for PSS/UCLA — coefficients are explicitly tuning placeholders per the existing `:65-66` comment; pinning placeholder boundaries is churn

**Definition of done for Phase 1b**: tests pass, telemetry events fire to `Logger` with private value qualifier, no UI changes shipped yet. Can ship behind a flag (no flag needed because no UI is wired up).

#### Phase 2: Reactive estimate harness

**Files:**
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingDraft.swift` (new)
- `products/life-clock-ios/Tests/OnboardingDraftTests.swift` (new)

**Tasks:**

- [ ] **`OnboardingDraft` `@Observable` class** holding all in-progress answers (NOT `ObservableObject` — the codebase is uniformly on the Swift macro `@Observable`, see `LifeClockStore.swift:14`, `SubscriptionStore.swift:12`). Mirror `UserProfile` field-for-field but with all-optional, transient. **No persistence whatsoever — not UserDefaults, not Keychain, not file.** A mid-onboarding crash = restart from scratch. Rationale (independently confirmed by data-integrity-guardian + security-sentinel):
  - Storing `parentMotherAgeAtDeath`, `perceivedStressScore`, `lonelinessScore` in UserDefaults leaks to iCloud device backup (UserDefaults follows iCloud Key-Value-Store rules, NOT the SwiftData `cloudKitDatabase: .none` gate). Silent privacy violation.
  - The flow is ≤5 minutes; mid-flow Apple-process-kills are rare; cost of restart is one re-entry.
  - Brainrot doesn't crash-recover either — established convention.
  ```swift
  @Observable
  final class OnboardingDraft {
    var birthDate: Date?
    var biologicalSex: BiologicalSex?
    var heightCm: Double?
    var weightKg: Double?
    var cardioMinsPerWeek: Int?
    var smokingStatus: SmokingStatus?
    var alcoholFrequency: AlcoholFrequency?
    var strengthFrequencyPerWeek: Int?
    var sleepGoalHours: Double?
    var dietQualityBaseline: DietQuality?
    var parentMotherAlive: Bool?
    var parentMotherAgeAtDeath: Int?
    var parentFatherAlive: Bool?
    var parentFatherAgeAtDeath: Int?
    var perceivedStressScore: Int?
    var lonelinessScore: Int?
    var primaryGoal: OnboardingGoal?
    var toneMode: ToneMode?

    // Engine output (live)
    var runningEstimate: LifeClockEstimate? { … }
    var lastDelta: AnswerDelta?  // "+1.4 yrs from regular strength training"
  }
  ```
  Note: `OnboardingDraft` does NOT touch `ToneMode` enum cases — the side-note about adding "Firm/Direct" is tracked in a separate task chip (see brainstorm `Related Side-Notes`).

- [ ] **`runningEstimate`** computed via `ClockEngine.partialEstimate(draft:)` — gracefully handles missing fields by skipping their adjustment branch. When `birthDate` and `biologicalSex` are unset, returns `nil` (no display until baseline known).

- [ ] **`AnswerDelta`** struct holding `years: Double` and `caption: String`. Re-computed on each `runningEstimate` change as the difference from the previous estimate. Caption looks up a per-factor template ("+%.1f yrs from regular strength training") with non-medical wording.

- [ ] **`completeOnboarding(_:)` integration** — `OnboardingDraft.materialize()` returns a fully-populated `UserProfile` ready to pass to `LifeClockStore.completeOnboarding(profile:tone:disclaimerAccepted:)` ([LifeClockStore.swift:371-382](products/life-clock-ios/Sources/App/LifeClockStore.swift)). **Signature stays stable** per research finding (≥18 store-level test sites call it directly).

- [ ] **Tests** — all-fields-set produces same estimate as `ClockEngine.calculateBaseline`; partial inputs produce stable estimates; delta captions match templates; materialize round-trips cleanly through SwiftData.

**Definition of done**: harness compiles, tests pass, no UI changes yet.

#### Phase 3: Visual primitives

**Files:**
- `products/life-clock-ios/Sources/Shared/LifeGridDotView.swift` (new)
- `products/life-clock-ios/Sources/Shared/ClockMascotView.swift` (new)
- `products/life-clock-ios/Sources/Assets.xcassets/ClockMascotPositive.imageset/` (new)
- `products/life-clock-ios/Sources/Assets.xcassets/ClockMascotNegative.imageset/` (new)

(`AnimatedNumberView` was originally planned here. Replaced with the built-in SwiftUI primitive `.contentTransition(.numericText(value:))` (iOS 17+) — saves a component file and matches Apple's recommended pattern. See Phase 5 for usage.)

**Tasks:**

- [ ] **`LifeGridDotView`** — Canvas-based grid of dots representing weeks of life:
  ```swift
  struct LifeGridDotView: View {
    let totalWeeks: Int      // typically 80 yrs * 52 = 4160
    let livedWeeks: Int      // age-derived
    let lostWeeks: Int       // engine penalty visualization
    let mode: GridMode       // .full | .remainingHighlighted | .recoveryHighlighted
  }
  ```
  Performance pattern (per Apple Canvas docs + performance-oracle review):
  - `Canvas(rendersAsynchronously: true) { context, size in … }` — single biggest perf lever for 4000+ primitives; lets the canvas present off the main thread.
  - **Precompute dot center coordinates once** via `@State` keyed on `totalWeeks` so the geometry isn't rebuilt every frame.
  - **Animate via a single `Double` progress parameter (0→1)** wrapped in `TimelineView(.animation)`. Interpolate colors inside the Canvas closure with `Color.lerp`. Avoid per-dot `withAnimation`.
  - For `.recoveryHighlighted` mode reveals where only a subset changes, prefer cross-fading two `Image`-rendered snapshots (rendered once via `ImageRenderer` at view-load) over re-rendering 4160 dots.
  - **Reduce Motion**: query `@Environment(\.accessibilityReduceMotion)`; gate the progress animation on `!reduceMotion` (Canvas content still draws; just skip the sweep). Color-blind safe: encode lived/remaining/lost/recovery via shape *and* color (e.g. filled circle vs ring) — not color alone.
  - **Note:** [ClockHandView.swift:13-14](products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift) explicitly rejects Canvas as "overkill" for a single hand. The dot grid is the opposite case (many primitives, one pass) — Canvas is correct.

- [ ] **`ClockMascotView`** — two static Asset images (positive + negative) crossfaded based on a `running: LifeClockEstimate?`:
  ```swift
  struct ClockMascotView: View {
    let estimate: LifeClockEstimate?
    let baseline: LifeClockEstimate? // for delta polarity
    // crossfades positive/negative art based on whether estimate is above/below baseline
  }
  ```
  Founder will provide the two assets. Until then ship placeholders (the existing app icon clock + a desaturated/sad variant). **Recommend SVG/PDF vector** in the asset catalog (`.preserveVectorRepresentation`) to ship one asset instead of @1x/@2x/@3x × iPhone/iPad and avoid Dynamic Type scaling artifacts.

- [ ] **EngineClock injection alignment.** New views requiring time take it via init param or by reading `store.clock` (which the store already exposes — see [LifeClockStore.swift:70](products/life-clock-ios/Sources/App/LifeClockStore.swift)). **Do NOT introduce `@Environment(\.engineClock)`** — that would be a third pattern not present in the existing codebase. CI grep gate (`Date()` / `Calendar.current` only in `EngineClock.swift`) still applies.

- [ ] **Skip per-component snapshot tests.** Pixel snapshots on visual primitives that will be tweaked every release = guaranteed churn, near-zero defect detection. Verify via SwiftUI Previews + manual review + the integration UITest in Phase 9.

**Definition of done**: components render in SwiftUI Previews on iPhone 12 baseline at 60fps; placeholders for mascot art committed; animation respects Reduce Motion; CI grep gates pass.

#### Phase 3.5: Cold open + app preview screens (depends on Phase 3 primitives)

Moved earlier in the sequence (was originally Phase 8). The original ordering had the coordinator's `OnboardingScreen` enum touched twice — once in Phase 4 (with stub lead-ins) and again later in Phase 8 (filling them in). Building the lead-ins right after the primitives means the Phase 4 coordinator wires up the full enum once.

**Files:**
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/ColdOpenView.swift` (new)
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/AppPreviewsView.swift` (new)
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/WelcomeView.swift` (new)
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/MeetYourClockView.swift` (new)
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/ReactiveSliderView.swift` (new)

**Tasks:**

- [ ] **`ColdOpenView`** — clock mascot alone, no copy, ~2s auto-advance. Skippable on tap (don't trap users in a forced delay).

- [ ] **`AppPreviewsView`** — phone-in-phone preview of 3 actual app screens (`TodayView`, `HistoryView`, a wrap-up). Animates between them. Bottom CTA: "Get started." Use `ImageRenderer`-captured static images, not live SwiftUI subviews — performance + isolation.

- [ ] **`WelcomeView`** — "Welcome to Life Clock" + tagline + Let's go CTA.

- [ ] **`MeetYourClockView`** — introduces `ClockMascotView` mascot. Copy: "This is your clock. The more you show up, the more time it gives back."

- [ ] **`ReactiveSliderView`** — interactive demo BEFORE any questions. User drags between extremes; the mascot crossfades positive ↔ negative AND a sample number animates via `.contentTransition(.numericText(value:))`. Demo only — no data captured. Bottom CTA: "Show me mine."

**Definition of done**: 5 lead-in screens render and animate at 60fps; preview screens use `ImageRenderer` snapshots; reactive slider feels responsive on device.

#### Phase 4: New onboarding flow shell + data-collection screens

**Files:**
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift` (heavy refactor)
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingScreen.swift` (new — enum)
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/*.swift` (new — one file per screen)
- `products/life-clock-ios/UITests/LifeClockUITests.swift` (rewrite — all step IDs change)

**Tasks:**

- [ ] **Refactor `OnboardingView` to use `NavigationStack(path:)` + `.navigationDestination(for: OnboardingScreen.self)`** rather than a hand-rolled switch (which would introduce a third coordinator pattern not present in the codebase). The existing convention is `NavigationStack` per feature root ([TodayView.swift:8](products/life-clock-ios/Sources/Features/Today/TodayView.swift), [HistoryView.swift:22](products/life-clock-ios/Sources/Features/History/HistoryView.swift)). Pattern:
  ```swift
  struct OnboardingView: View {
    @State private var path = NavigationPath()
    @Environment(LifeClockStore.self) private var store
    @State private var draft = OnboardingDraft()

    var body: some View {
      NavigationStack(path: $path) {
        ColdOpenView() // root
          .navigationDestination(for: OnboardingScreen.self) { screen in
            screenView(for: screen)
          }
      }
    }
  }
  ```
  Benefits: real back-stack semantics free, `runningEstimate` recompute on pop is automatic, matches the rest of the codebase. Forward = `path.append(.nextScreen)`; back = path pop. Document the new `Sources/Features/Onboarding/Screens/` subfolder convention in the directory's header (it's the first feature with a per-screen subfolder; precedent for future expansions).

- [ ] **`OnboardingScreen` enum** — one case per screen:
  ```
  coldOpen, appPreviews, welcome, meetYourClock, reactiveSlider,
  visibilityFraming, personalizeIntro, goalPick,
  baselineDOB, baselineSex, bodyComp, smoking, alcohol, strength, cardio,
  sleep, diet, familyMother, familyFather, stress, social, tone,
  priorAttempts, analyzing, archetypeReveal, concreteThisYear,
  lifeGridFull, lifeGridRemaining, bigNumberPenalty,
  engineRevealAndDial, recoveryPreview, healthKitAuth,
  paywallPrimary, entryView
  ```

- [ ] **Each screen view** in `Screens/`:
  - Reads from `OnboardingDraft` (env)
  - Fires `OnboardingTelemetry.screenAppeared` on appear, `screenAdvanced` on tap-continue
  - Uses agency-framed copy (no "doom default", no medical-claim verbs)
  - Has a stable accessibility identifier `onboarding.<screen-case>` for UITest
  - Continue CTA disabled until valid input (matches existing pattern at `OnboardingView.swift:284`)

- [ ] **Data-collection screens**:
  - `goalPick`: 4–5 options (Live longer / More energy / Be there for family / Beat family history / Just curious) — selected goal personalizes `recoveryPreview` cycling words.
  - `bodyComp`: height + weight inputs → derives BMI; "Prefer not to say" path leaves both nil.
  - `cardio`: minutes/week input.
  - `familyMother` / `familyFather`: parent alive Y/N, then age-at-death; "Prefer not to say" / "Don't know" as first-class options that leave fields nil.
  - `stress`: PSS-10 short form (3–5 questions condensed to 1 screen with a 5-point Likert) → numeric score 0–40.
  - `social`: UCLA-3 loneliness scale (3 questions) → numeric score 3–9.
  - `priorAttempts`: 3-option choice ("First time / Tried, didn't stick / Tried, briefly worked") — informs archetype sub-meter weights and recovery copy tone, but no in-flow rating screen (deferred to a separate post-launch plan; see Future Considerations).

- [ ] **3-bar fake-progress `analyzing`**: three sequential progress bars ("Reading your inputs… / Calibrating against population data… / Generating your timeline…") with ~1.5s each. Total 4–5s. Uses `EngineClock` for timing.

- [ ] **`archetypeReveal`**: large heading with archetype name, sub-meter bars (behavioralRisk + recoveryCapacity), 1-paragraph description, `Makes sense` CTA. Per-archetype copy in a static dictionary.

- [ ] **`concreteThisYear`**: pulls a tangible-this-year stat ("Looks like you'll spend ~X days [eating / sleeping / commuting] this year") computed from the user's age and population averages. No threat language.

- [ ] **`lifeGridFull` → `lifeGridRemaining` → `bigNumberPenalty`**: the dot-grid escalator. Reuses `LifeGridDotView`. `bigNumberPenalty` shows the engine's lifestyle-derived penalty (e.g. "~12 yrs at risk from current habits") — framed in agency language ("at risk from", not "lost to", not "rotting").

- [ ] **`recoveryPreview`**: Goal-driven cycling. `RecoveryCopyTable[goal][archetype]` returns a list of 3–5 cycling words. Words match the goal:
  - `.beThereForFamily` → "with your kids", "showing up", "at the dinner table"
  - `.moreEnergy` → "feeling alive", "on the trail", "awake at dawn"
  - `.beatFamilyHistory` → "outliving the odds", "rewriting the story"
  - `.liveLonger` → "living", "loving", "exploring"
  - `.justCurious` → "showing up", "noticing", "being here"
  Cycling animation: 1.5s per word, fades with `.transition(.opacity)`.

- [ ] **HealthKit re-position**: move auth from current step 4 (`OnboardingView.swift:184-211`) to a dedicated `healthKitAuth` screen between `recoveryPreview` and the paywall transition. Copy: "Let your clock learn from your body." Calls existing `LifeClockStore.requestHealthAuthorization()` ([LifeClockStore.swift:346-362](products/life-clock-ios/Sources/App/LifeClockStore.swift)) — no new HKHealthStore instantiation (CI gate).

- [ ] **`Info.plist` audit task**: Apple Guideline [5.1.1(ii)](https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage) rejects mismatched `NSHealthShareUsageDescription`. Verify the existing string covers what the engine reads (resting HR, steps, exercise minutes, sleep — confirm via `LiveHealthKitService.swift`) and matches the new on-screen copy. "Learn from your body" is a broader claim than "steps only" — update the description if the auth-screen copy implies broader use.

- [ ] **HealthKit decline handling**: per Apple, `requestAuthorization` returns `success: true` only when the sheet dismisses, **not** when anything was granted. Don't infer grant state from the bool. Engine already handles missing inputs gracefully. Surface an "Open Settings" affordance (`UIApplication.openSettingsURLString`) in Profile for users who declined and later want to grant — Apple **cannot** re-prompt programmatically.

- [ ] **GDPR Art. 9 consent priming.** Family-longevity (`familyMother` / `familyFather`) and stress / social screens collect special-category data under GDPR (parental mortality, mental-health-adjacent self-report). Add a single priming screen *before* the family-longevity block:
  - Title: "A few sensitive questions"
  - Body: "These help us calibrate. Stored on your device only — never sent off."
  - CTA: "Continue" (advances) / "Skip these" (sets all four parent fields + PSS + UCLA to nil; advances to `tone`)
  - This is the GDPR-required explicit consent moment. Document it as such in the analytics consumer doc.

- [ ] **Under-18 user flow.** Existing `isAdultBirthDate` gate at [OnboardingView.swift:284](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift) hides smoking/alcohol questions for users <18. Preserve this. Additionally: skip the `bigNumberPenalty` and "this is what you have left" framing for under-18s — the mortality framing isn't appropriate. Replace with a softer "Your habits compound from here" screen.

- [ ] **Both-parents-lost-young soft framing.** If both `parentMotherAgeAtDeath < 65` AND `parentFatherAgeAtDeath < 65`, insert a one-screen acknowledgement before the running estimate updates: "That's a lot to carry. Your clock isn't your fate — these inputs are one signal among many." Engine still applies the −2 yrs adjustment, but the UX softens.

- [ ] **"Just curious" goal softening.** If `primaryGoal == .justCurious`, replace `bigNumberPenalty` and the commitment framing with a curiosity-aligned variant ("Here's what the data suggests" rather than "X years at risk"). Recovery preview still cycles per goal table.

- [ ] **Offline-at-paywall.** If `SubscriptionStore.products` is empty when `paywallPrimary` would render, route to `freeFallback` with a one-line note: "Upgrade options unavailable — try again from Profile." Don't block the user from entering the app.

- [ ] **Reinstall / upgrade-install rule.** If `currentProfile != nil` AND `anchorAdjustedAt == nil` (existing user from before this rebuild), **do NOT re-run onboarding** — they've already completed the old 7-step flow. Show a one-time "Update your clock" banner on Today inviting them to a one-time recalibration that runs only the new screens (lifestyle additions + dial). Track via a new `userProfile.onboardingV2CompletedAt: Date?` field (additive, optional, included in Phase 1a).

- [ ] **Rewrite `LifeClockUITests.swift:10-32`** — every step ID changes. Walk the new flow end-to-end. Pin each accessibility ID per the screen enum.

- [ ] **Telemetry**: per-screen `screenAppeared` + `screenAdvanced` events. Choice events on every selection screen with the choice key+value. Build a `funnel.md` doc that lists each event for the analytics consumer.

**Definition of done**: full onboarding walkable end-to-end in simulator (placeholder reveal/dial/paywall acceptable for now); UITests rewritten and passing; per-screen telemetry firing; agency-framed copy reviewed against `CLAUDE_HANDOFF.md:38-46` grep gates.

#### Phase 5: Engine reveal + healthspan dial

**Files:**
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift` (new)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift` (small addition: `applyAnchorAdjustment(years:)`)
- `products/life-clock-ios/Tests/EngineRevealAndDialTests.swift` (new)

**Tasks:**

- [ ] **`EngineRevealAndDialView`** — the screen that fuses the engine output and the one-time dial:
  ```
  ┌─────────────────────────────────────────┐
  │      Your projected healthspan          │
  │                                         │
  │   Text(...).contentTransition(            │
  │     .numericText(value: years))           │
  │              53.2 years                 │
  │     (locked-in date: Mar 14 2079)       │
  │                                         │
  │   ─────●─────────────────  -5      +5   │
  │              ▲                          │
  │      "Adjust if your gut says           │
  │       something the questions missed"   │
  │                                         │
  │   ┌───────────────────────────────────┐ │
  │   │           Confirm                 │ │
  │   └───────────────────────────────────┘ │
  │                                         │
  │      One-time only — locks for life     │
  └─────────────────────────────────────────┘
  ```
- [ ] **Dial mechanics**:
  - Range: ±5 years around `runningEstimate.projectedAgeYears`
  - Initial position: 0 (engine output, no adjustment)
  - Real-time number animation as user drags
  - Real-time projected-end-date recalculation
  - Haptic at center (engine output) and at the bounds
  - On Confirm: `applyAnchorAdjustment(years:)` writes `personalAdjustmentYears` and `anchorAdjustedAt = .now` (via `EngineClock`)
  - Telemetry: `dialAdjusted(years:)` with the final value

- [ ] **Idempotency**: if `anchorAdjustedAt != nil` on this view's appear (edge case: user backs into onboarding somehow, or store-level test path), skip past it. Should never happen in a clean flow but defensive check is cheap.

- [ ] **`applyAnchorAdjustment(years:)` on `LifeClockStore`** — small new method, race-safe:
  ```swift
  @MainActor
  func applyAnchorAdjustment(years: Double) async {
    guard let profile = currentProfile else { return }
    // Set both fields, then save. The engine guards on `anchorAdjustedAt != nil`
    // so partial state (one field set, save failed) cannot double-apply.
    profile.personalAdjustmentYears = years
    profile.anchorAdjustedAt = clock.now
    do {
      try modelContext.save()
      emit(.anchorAdjusted)  // optional intent for SupportMomentPresenter
    } catch {
      // Roll the in-memory writes back to keep memory consistent with disk
      profile.personalAdjustmentYears = nil
      profile.anchorAdjustedAt = nil
      Logger(subsystem: "com.lifeclock.app", category: "Store")
        .error("applyAnchorAdjustment save failed: \(error, privacy: .public)")
      // Surface error to caller via a thrown error or a published state field;
      // do NOT silently fail (avoid the existing `try?` anti-pattern that hides
      // the SwiftData migration landmine).
    }
  }
  ```
  No `try?`. Errors surface; in-memory state matches disk on failure.
  Note: `LifeClockStore.completeOnboarding(profile:tone:disclaimerAccepted:)` signature **stays stable** per research finding. The dial value flows through the `profile` argument (already populated by `OnboardingDraft.materialize()`). Fits the existing pattern of small mutator methods on the store ([LifeClockStore.swift:386-398](products/life-clock-ios/Sources/App/LifeClockStore.swift)).

- [ ] **`ClockEngine.calculateBaseline` honors the adjustment — atomically gated:**
  ```swift
  // at ClockEngine.swift:27, after `projected = baselineYears + lifestyleAdjustment`:
  let dialAdjustment = (profile.anchorAdjustedAt != nil)
      ? (profile.personalAdjustmentYears ?? 0)
      : 0
  projected += dialAdjustment
  ```
  This is the load-bearing race fix. The engine treats the pair `(personalAdjustmentYears, anchorAdjustedAt)` as logically atomic: until both are set, the adjustment is 0. A killed app between the two writes leaves `anchorAdjustedAt = nil` → engine returns the unadjusted estimate → next launch the dial screen reappears (idempotency check passes) → user re-confirms cleanly. No double-counting possible.

- [ ] **Explicit dial confirmation modal**: after the user taps Confirm on the dial, show a small "Lock your clock?" alert: "Once locked, this can't be re-adjusted." with Cancel / Lock. Cancel returns to the dial. Lock fires `applyAnchorAdjustment`. Prevents accidental confirm.

- [ ] **Back-navigation rules around the dial**:
  - Pre-confirm (`anchorAdjustedAt == nil`): back-nav to a question screen recomputes `runningEstimate`; the dial position resets to 0 on re-arrival.
  - Post-confirm (`anchorAdjustedAt != nil`): back-nav from any subsequent screen to the dial is **disabled**. Programmatically: clear the `NavigationPath` on Confirm, push the post-dial screens onto a fresh path. The dial screen never reappears.
  - Implementation: on `applyAnchorAdjustment` success, `path = NavigationPath()` then `path.append(.healthKitAuth)`.

- [ ] **Tests**:
  - Dial bounds: -5 / +5 / 0
  - Persistence: confirm writes `personalAdjustmentYears` and `anchorAdjustedAt` together
  - Idempotency: pre-adjusted profile routes past the screen
  - Engine integration: `calculateBaseline` for a profile with `personalAdjustmentYears = 3.0` returns engine output + 3.0 yrs
  - Reload: a profile saved with `personalAdjustmentYears = 3.0` reads back as 3.0 (SwiftData round-trip)

**Definition of done**: dial works end-to-end; engine respects the adjustment; tests pass; telemetry fires.

#### Phase 6: Single-tier paywall with introductory pricing

**MAJOR PIVOT from original draft.** The original draft proposed a two-stage paywall with an "I'd rather pay full price" inverted-dismissal overlay. **This pattern was the proximate cause of Cal AI's App Store removal in April 2026** under Guidelines 3.1.2(c) (price-prominence deception) and 5.6 (manipulative purchase flow — "second, different subscription purchase flow after the first was declined"). Cal AI was reinstated only after removing it. Brainrot ships a variant in production, but the rejection precedent is now documented and the risk/reward is wrong for a launching app.

Also dropped from the original draft: `CommitmentRitualView` ("wind your clock 5x"), `LoadingPremiumView` (second fake-progress in one flow is dark-pattern smell), `RatingAskView` mid-onboarding (Apple's `requestReview` is rate-limited; burning the quota on pre-purchase users is bad ROI — moves to post-first-week-of-use as a separate plan). `ResearchCredibilityView` becomes a tappable "How is this calculated?" link on `EngineRevealAndDialView`, not a dedicated screen.

What survives: a single, well-built paywall that respects guidelines and converts on the engine reveal's emotional momentum.

**Files:**
- `products/life-clock-ios/Sources/Features/Paywall/PaywallProductsView.swift` (new — extracted shared core)
- `products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift` (new — onboarding wrapper)
- `products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift` (refactor — wrap shared core)
- `products/life-clock-ios/Sources/Services/Products.storekit` (intro offer config)

**Tasks:**

- [ ] **Extract `PaywallProductsView` shared core.** Single source of truth for: product list rendering, annual/monthly toggle, restore button, §3.1.2 fineprint ([PaywallSheet.swift:141-158](products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift)), `isPro`-flip auto-dismiss ([PaywallSheet.swift:54-56](products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift)). Both the existing `PaywallSheet` (re-engagement) and the new `PaywallPrimaryView` (onboarding) become thin wrappers around this core. **Justification**: pre-deepening, two paywall surfaces would have drifted forever (every fineprint edit a 2-PR change). One core, two chromes.

- [ ] **`PaywallPrimaryView`** — single-tier paywall. App Store-safe shape:
  - **Annual / monthly toggle** with **equal-prominence pricing** for the total amount the user will be billed. Per Apple 3.1.2(c) — Cal AI was rejected for showing the per-week price more prominently than the total. Format: "**$59.99 / year** ($4.99/mo equivalent)" for annual; "**$5.99 / month**" for monthly. The total is the larger font.
  - **Visible auto-renewal terms**, never gated behind a toggle interaction (Cal AI's other rejection vector). Display "Subscription renews automatically. Cancel anytime in Settings." in a fixed-position footer.
  - **Introductory offer applied automatically** for new subscribers: first year at $11.99 (then $59.99/yr). Display as "First year $11.99, then $59.99/year." NOT as a dismissible discount overlay. NOT with strikethrough — the strikethrough deception risk (Apple 3.1.1 + FTC) is real if $11.99 is the only price ever offered to a new subscriber.
  - Existing close button + restore button from [PaywallSheet.swift:32-41](products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift) preserved via the shared core.
  - Annual pre-selected per existing pattern at [PaywallSheet.swift:48-52](products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift).
  - Auto-dismiss when `isPro` flips → next screen is `freeFallback` (now misnamed — rename to `entryView` since it serves both free and pro users) or directly to Home.

- [ ] **Introductory pricing config (NOT promotional offer signing).** Per [WWDC25 StoreKit](https://developer.apple.com/videos/play/wwdc2025/241/) and the framework-docs research: introductory offers for new subscribers are auto-applied by StoreKit at purchase time, no `offerID` in the purchase call, no JWS signing infrastructure required. Configure once in App Store Connect → in-app purchase → introductory offer for `com.lifeclock.pro.annual`: pay-as-you-go, $11.99 first year, then standard $59.99/yr. Mirror in `Products.storekit` for sandbox. Eligibility is automatic (StoreKit gates by subscription-group history). **Skip promotional offers entirely** — no private key in the bundle, no signing endpoint to maintain, no key-rotation contingency.

- [ ] **Eligibility check before showing intro price.** At display time, gate the "First year $11.99" line on `Product.SubscriptionInfo.isEligibleForIntroOffer(for: groupID)`. If false (existing/lapsed subscriber), display the standard price only.

- [ ] **Telemetry**:
  - `paywallShown(.primary)` once on appear
  - `paywallDismissed(.primary, reason: .closed)` → entry view
  - `paywallDismissed(.primary, reason: .ineligibleForIntro)` → entry view (informational; user can resubscribe in Profile)
  - `purchased(productID:)` on success (productID public, no PII)

- [ ] **Entry view (renamed from `freeFallback`)**: any dismissal lands on Home. The locked-in clock + dial value are visible (per brainstorm decision: "Keep current split"). For pro users, the existing `PaywallSheet` triggers from Profile and History continue to work as re-engagement (now via the shared `PaywallProductsView` core).

- [ ] **Strikethrough audit**: zero strikethrough pricing anywhere. Strikethrough is only safe if it represents a real prior price the user could have paid. For new subscribers, the only price they could have paid IS the intro — strikethrough is deceptive.

- [ ] **App Store Connect privacy questionnaire update**: declare the new sensitive fields per Phase 1a. This is the same disclosure already noted in 1a but must be live before paywall ships.

**Definition of done for Phase 6**: single paywall renders end-to-end in simulator with sandbox StoreKit; intro pricing displays for eligible (new) and falls back cleanly for ineligible; both purchase and dismiss-to-entry paths tested; `PaywallSheet` re-engagement still works post-refactor.

#### Phase 7: Tests, analytics validation, TestFlight rollout

**Files:**
- `products/life-clock-ios/UITests/OnboardingFunnelTests.swift` (new)
- `products/life-clock-ios/Tests/OnboardingEndToEndTests.swift` (new)
- `docs/products/life-clock/onboarding-funnel.md` (new — analytics consumer doc)
- `docs/products/life-clock/PHASE_STATUS.md` (update)

**Tasks:**

- [ ] **End-to-end onboarding integration test** — drives a `OnboardingDraft` through all answers, completes onboarding, verifies `UserProfile` persisted with all expected fields including `personalAdjustmentYears` and `anchorAdjustedAt`.

- [ ] **XCUITest funnel walkthrough** — completes the entire ~30-screen flow end-to-end, asserts each screen's accessibility ID appears in order, verifies paywall reaches sandbox purchase.

- [ ] **Analytics smoke test** — `StubTelemetry` records all events through the flow; assert the funnel sequence matches `onboarding-funnel.md`.

- [ ] **Per-screen drop-off instrumentation** — wired through `OnboardingTelemetry`. Funnel doc defines:
  - 1 row per screen
  - Event name, expected occurrence, expected duration
  - Drop-off threshold beyond which we flag for compression

- [ ] **TestFlight rollout plan**:
  - Internal testers: full onboarding, all dials, sandbox StoreKit
  - External 100-user cohort: real Apple sandbox + actual purchase flow
  - Gating metrics: completion rate ≥40%, dial-confirm rate ≥80% of completers, paywall-shown rate = 100% of confirms, paywall-conversion ≥3%
  - Compression contingency: if completion < 30%, identify top-3 drop-off screens and prepare a "lite" branch that removes them.

- [ ] **Accessibility audit**: VoiceOver walkthrough of each screen; Dynamic Type at largest size; Reduce Motion gating on every animation; Color-blind safe palette on dot grid.

- [ ] **Update `docs/products/life-clock/PHASE_STATUS.md`** with the new phase + completion criteria.

**Definition of done**: all tests green, analytics doc landed, TestFlight cohort enrolled, launch readiness checklist complete.

## Alternative Approaches Considered

(All explored in the brainstorm — see [docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md](docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md). Summary:)

- **Anchor prompt placement**: rejected (a) persistent banner, (b) modal on first day-of-use, (c) settings-only time-boxed in favor of inline at end of onboarding, folded into reveal screen.
- **Dial semantics**: rejected DOB editor and unbounded dial in favor of bounded ±5-year healthspan dial.
- **Reveal style**: rejected back-loaded big reveal and two-stage reveal in favor of live reactive number with delta captions.
- **Tactics aggressiveness**: rejected Brainrot-lite and elegant reveal in favor of full Brainrot tactics (with copy adapted to agency framing).
- **Free vs Pro split**: rejected tighter free tier, looser free tier, and clock-as-Pro in favor of unchanged current split.

## System-Wide Impact

### Interaction Graph

A user completing onboarding now triggers a chain reaction up to four levels deep:

1. **Final screen tap** → `OnboardingDraft.materialize()` → `LifeClockStore.completeOnboarding(profile:tone:disclaimerAccepted:)` ([LifeClockStore.swift:371-382](products/life-clock-ios/Sources/App/LifeClockStore.swift)) → `modelContext.insert(profile)` → `emit(.onboardingComplete)` ([LifeClockStore.swift:382](products/life-clock-ios/Sources/App/LifeClockStore.swift)).
2. **`emit(.onboardingComplete)`** → `SupportMomentPresenter` evaluates trigger conditions → may schedule a wrap-up moment.
3. **`LifeClockStore.bootstrap()`** is called from `advance()` ([OnboardingView.swift:310](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift) — preserve at the new equivalent site) → reads HealthKit auth state → loads daily snapshots → triggers UI refresh on `TodayView`, `HistoryView`, `ProfileView`.
4. **`isPro` flip** (via `Transaction.updates` listener at [SubscriptionStore.swift:24](products/life-clock-ios/Sources/Services/SubscriptionStore.swift)) → `PaywallPrimaryView` auto-dismisses → `OnboardingScreen` advances past the paywall to either `freeFallback` or directly to Home.

**`anchorAdjustedAt` is read** by `EngineRevealAndDialView`'s idempotency check; written exactly once by `applyAnchorAdjustment(years:)`. **`personalAdjustmentYears` is read** by `ClockEngine.calculateBaseline` on every estimate call (Today screen, History recompute, weekly trend) — so this field changes the headline number throughout the app forever after the dial is locked.

### Error & Failure Propagation

- **SwiftData migration failure** (NSCocoaErrorDomain 134110 per [LifeClockSchema.swift:10-13](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)) — silent no-op; the app would launch with an empty store. **Mitigation**: every new field MUST be optional or defaulted; pre-merge unit test verifies a V1-seeded store opens cleanly with V1.1 schema. (Reference: `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`.)
- **HealthKit permission timeout** — `LiveHealthKitService.requestAuthorization()` ([LiveHealthKitService.swift:58-62](products/life-clock-ios/Sources/Services/LiveHealthKitService.swift)) async-waits; if no response, the user can tap Continue and proceed without HealthKit data. Engine handles missing HealthKit inputs.
- **StoreKit purchase failure** — existing `SubscriptionStore.purchase()` returns `Result<Transaction, Error>`; on error, show a brief alert in the paywall and stay on `PaywallPrimaryView`. Don't auto-advance to free fallback (that would feel like the app gave up).
- **Promo offer signature mismatch** — Apple requires server-side signed promotional offers OR app-side cryptographic signatures using a private key stored in the App Store Connect dashboard. **Mitigation**: use the simpler "introductory pricing" mechanism (configured per-product in App Store Connect, no signature) instead of promotional offers, IF the founding offer can be a one-time intro price for new subscribers. **Decision deferred to Phase 7 implementation** — pick whichever mechanism Apple recommends for our cohort definition.
- **`OnboardingDraft` mid-flow crash** — draft is transient (in-memory ObservableObject). Any crash discards progress. **Mitigation**: serialize draft to UserDefaults on each screen transition; restore on relaunch if `UserProfile` doesn't yet exist. Draft cleanup on `completeOnboarding`.

### State Lifecycle Risks

- **Partial-write to UserProfile**: `completeOnboarding` writes a fully-populated profile in one `modelContext.insert(...)` followed by `try? modelContext.save()`. If the save fails after insert, SwiftData should roll back the insert in the same context — but the documented bug at `docs/solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md` suggests sheet-dismissal can leave dangling references. **Mitigation**: wrap `completeOnboarding` in a do/catch and verify the profile is queryable before transitioning to Home; if not, reset onboarding state.
- **Dial confirmed but profile not yet written**: `applyAnchorAdjustment(years:)` is called AFTER `completeOnboarding` (the profile already exists). Race-free.
- **Reinstall behavior**: per CI gate `cloudKitDatabase: .none`, `personalAdjustmentYears` and `anchorAdjustedAt` do NOT iCloud-sync. Reinstall = onboarding starts fresh with new dial available. This matches the "one-time per install" semantics in the brainstorm.
- **Backgrounding mid-paywall**: StoreKit handles this — Apple's paywall sheet survives backgrounding. Our wrapper `PaywallPrimaryView` should not interrupt an in-flight purchase.

### API Surface Parity

- `LifeClockStore.completeOnboarding(profile:tone:disclaimerAccepted:)` signature **stays stable** (≥18 store-level test sites depend on it). New fields ride in via the `profile` argument.
- `ClockEngine.calculateBaseline(profile:)` signature **stays stable**. Internal logic now reads new optional fields and applies the dial adjustment.
- `LifeClockStore.applyAnchorAdjustment(years:)` is **new** — only called from `EngineRevealAndDialView`. No API parity concerns.
- `OnboardingTelemetry` is **new** — injected via init parameter on `OnboardingCoordinator` (matches the existing service-injection convention; not `@Environment(\.onboardingTelemetry)`). Parity with no other interface (this is the only consumer).

### Integration Test Scenarios

These cross-layer scenarios are NOT caught by unit tests:

1. **Walk full onboarding → verify `TodayView` shows the engine output minus dial adjustment**: simulator boots cleanly, user completes all 30 screens, dials -2.5 years, lands on `TodayView`, headline number reflects -2.5 yrs. Assert via XCUITest accessibility identifier on the headline.
2. **Walk to paywall → tap "I'd rather pay full price" → verify primary paywall returns at full price**: discount overlay fully dismisses without affecting StoreKit state. No spurious `purchased` event fires.
3. **Walk to paywall → cancel → verify free fallback shows correct entitlements**: `isPro == false`, History shows 7-day cap, locked rows trigger existing `PaywallSheet` (not the new `PaywallPrimaryView`). The clock and dial value remain visible.
4. **Migration rehearsal**: build app at `main`, complete onboarding (V1 schema), then check out this branch and re-launch. App must read the V1 profile, surface it as already-onboarded, and migrate cleanly. (This rules out the SwiftData mandatory-attribute landmine.)
5. **HealthKit denial**: user taps Don't Allow on the system permission. Engine still works. `TodayView` shows the dial-adjusted estimate. No HealthKit-derived inputs feed the engine; archetype was computed without them.

## Acceptance Criteria

### Functional Requirements

- [ ] User can complete onboarding from cold open through paywall in ≤5 minutes on a 2024-era iPhone. **Measurement**: XCUITest harness times from `screenAppeared(.coldOpen)` telemetry event to `paywallShown(.primary)`; assert `< 300_000ms` on iPhone 12 simulator.
- [ ] Five new lifestyle factors are collected (BMI, cardio, family longevity, perceived stress, social isolation) with "prefer not to say" paths that leave fields nil.
- [ ] Running estimate animates after each answer with a per-factor delta caption.
- [ ] Engine reveal screen displays the engine's output AND a working ±5 yr dial.
- [ ] Confirming the dial writes both `personalAdjustmentYears` and `anchorAdjustedAt`.
- [ ] After dial confirmation, `ClockEngine.calculateBaseline` returns engine output + dial adjustment for ALL subsequent calls.
- [ ] Dial confirmation screen never reappears post-onboarding; idempotency verified.
- [ ] Single-tier paywall fires after `healthKitAuth`; annual/monthly toggle visible; intro pricing applies for new subscribers (auto-detected via `Product.SubscriptionInfo.isEligibleForIntroOffer`); auto-renewal terms always visible; close → entry view (free); successful purchase → `isPro` flips → auto-dismiss → entry view (Pro).
- [ ] Free users land in the existing app with their clock and dial value visible; existing `PaywallSheet` triggers from Profile and History continue to work.
- [ ] All copy passes the `CLAUDE_HANDOFF.md:38-46` grep gates: zero hits for `diagnose | prescribe | guarantee | predict` in user-facing strings. **Measurement**: CI step runs `rg -n '(diagnose|prescribe|guarantee|predict)' Sources/Features/Onboarding/Screens/` — fails the build on any hit.
- [ ] All time-using screens (animations, fake-progress, mascot crossfades) take an injected `EngineClock` via init param or `store.clock` (NOT a new `@Environment(\.engineClock)`); CI grep gate passes.
- [ ] `HKHealthStore()` instantiation remains only in `LiveHealthKitService.swift`; CI grep gate passes.
- [ ] New `UserProfile` fields are NOT iCloud-synced (per `cloudKitDatabase: .none` gate).
- [ ] **Telemetry value-redaction gate**: unit test runs against `OSLogTelemetry` and asserts no raw integer (PSS/UCLA/age) is emitted at the public log level. Manual verification via `log show --predicate 'subsystem == "com.lifeclock.app"' --info` on a test device.
- [ ] **Strikethrough audit**: zero strikethrough pricing in any paywall surface. CI grep `\.strikethrough\(\)` against `Sources/Features/Paywall/` and `Sources/Features/Onboarding/Screens/Paywall*.swift` returns no hits.
- [ ] **Privacy disclosure**: App Store Connect privacy questionnaire reflects all new sensitive fields before production release (Phase 1a).
- [ ] **Sensitive-data consent screen** appears before the family-longevity / stress / social block; "Skip these" path leaves the four parent fields + PSS + UCLA at nil and advances cleanly.
- [ ] **Back-nav gates**: post-confirm dial cannot be reached from any later screen; XCUITest verifies pushing back from `healthKitAuth` does NOT land on `engineRevealAndDial`.
- [ ] **HealthKit `Info.plist` audit**: `NSHealthShareUsageDescription` accurately matches the on-screen "let your clock learn from your body" framing AND the actual types requested by `LiveHealthKitService`.

### Non-Functional Requirements

- [ ] All animations respect Reduce Motion. **Verified for**: `LifeGridDotView` (skip sweep, hard color swap), `ClockMascotView` (skip crossfade), `.contentTransition(.numericText())` (Apple handles this — verify), dial drag (snap to nearest 0.5 yr instead of continuous interpolation), 3-bar fake-progress (collapse to single 1.5s gate), recovery cycling (pace at 3s/word, NOT 1.5s/word; opacity transitions are not auto-suppressed by Reduce Motion but pacing should still relax).
- [ ] VoiceOver walks the entire flow with sensible labels and announcements.
- [ ] Dynamic Type at the largest setting does not truncate any critical CTA.
- [ ] Color-blind audit on the dot grid: no red/green-only encoding (use shape + color).
- [ ] Performance: 60fps on iPhone 12 baseline through dot grid transitions and dial drag.
- [ ] Onboarding completion rate ≥40% on a 100-user TestFlight cohort. **If <30%, plan a compression branch.**
- [ ] Paywall conversion rate ≥3% on the same cohort.
- [ ] Dial-confirm rate ≥80% of completers (i.e. don't make the dial feel optional).

### Quality Gates

- [ ] Schema migration test passes: V1 store opens cleanly with new schema; new optional fields default correctly.
- [ ] All unit tests in `Tests/ClockEngineTests.swift`, `Tests/OnboardingDraftTests.swift`, `Tests/EngineRevealAndDialTests.swift`, `Tests/OnboardingTelemetryTests.swift` pass.
- [ ] XCUITest `OnboardingFunnelTests` walks the full flow and verifies each screen's accessibility ID and the paywall transition.
- [ ] Code review: at least one Swift reviewer signs off on the engine extension; at least one design reviewer signs off on the copy.
- [ ] Privacy + content review: founder reviews **every screen's primary copy**, not a sample of 5. Build an `Onboarding/Screens/copy.csv` listing screen ID + headline + body + CTA for one-shot review. CI grep on this CSV runs the agency-framing gate.
- [ ] App Store metadata + screenshot updates queued for the new flow.

## Success Metrics

- **Onboarding completion rate**: % of users who reach `paywallPrimary`. Target ≥40%, baseline TBD from current 7-step flow.
- **Dial-confirm rate**: % of completers who tap Confirm on `EngineRevealAndDialView`. Target ≥80%. **Operational definition**: Confirm is the only forward CTA on the dial screen — no skip affordance — so this metric is meaningful.
- **Dial adjustment distribution**: histogram of `personalAdjustmentYears` values. Healthy distribution = unimodal around 0 with thin tails. **Threshold for dial-range re-tuning**: >15% of users at the +5 boundary OR >15% at the -5 boundary suggests range is too narrow.
- **Paywall conversion rate**: % of `paywallShown(.primary)` events that result in `purchased`. Target ≥3%.
- **Per-screen drop-off**: top-3 highest-drop-off screens. Compression candidates if completion is below target.
- **Day-7 retention by archetype**: are some archetypes more sticky? Informs personalization priorities.

## Dependencies & Prerequisites

- **Founder-provided assets**: positive + negative clock mascot art (PNG or SVG, both sized for iPad + iPhone). Placeholders shipped during dev.
- **App Store Connect promotional offer or intro pricing config** for the founding offer (Phase 7).
- **Sandbox StoreKit testing accounts** for paywall flow validation.
- **Side-note task**: `ToneMode` rename + reintroduction of "Firm/Direct" is tracked separately (see brainstorm `Related Side-Notes`). This plan does NOT depend on or modify that work.
- **Worktree**: per `CLAUDE_HANDOFF.md:23-25`, work happens in `/Users/simons/ai-company-os-life-clock`; every Bash command in implementation must `cd` in.

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SwiftData mandatory-attribute migration landmine | High if rules ignored | Total data loss | All new fields optional or defaulted; file-backed V1→V1.1 migration test pre-merge (in-memory containers don't exercise lightweight migration — known false-negative); check `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`; Phase 1a ships standalone for ≥48h TestFlight soak before Phase 1b |
| **App Store rejection for two-stage paywall + inverted dismissal** | **High (recently enforced)** | **High (delayed launch)** | **DROPPED** the pattern entirely after deepening research. Cal AI was pulled April 2026 for the exact pattern (Guidelines 3.1.2(c) + 5.6). Plan now uses single-tier paywall with intro pricing — Apple-blessed mechanism, no JWS signing, no "second purchase flow after decline" |
| **Telemetry PII leak via os_log** | **Medium** | **High (privacy violation)** | **Logger with `privacy: .private`** on every value parameter; sensitive values bucketed before logging; unit test asserts no raw integer ever appears in log sink |
| **PII in UserDefaults / iCloud backup** | **Medium** | **High (silent privacy violation)** | **DROPPED** UserDefaults draft persistence entirely; mid-flow crash = restart. Also closes a Brainrot-mismatch convention vector |
| **`applyAnchorAdjustment` race causing double-applied dial** | **Medium** | **Medium (data corruption)** | Engine reads `personalAdjustmentYears` only when `anchorAdjustedAt != nil` — atomic gate; explicit do/catch on save replaces silent `try?` |
| App Store rejection for mortality framing | Low | High (delayed launch) | Agency framing + scientific sourcing + zero medical-claim verbs (`diagnose / prescribe / guarantee / predict` CI grep gate); pre-submit a 1-page rationale doc explaining the existing WeCroak / Memento Mori app precedent |
| App Store rejection for mismatched HealthKit usage description | Low | Medium | Phase 4 adds explicit `Info.plist` audit task — the new "let your clock learn from your body" copy must match `NSHealthShareUsageDescription` |
| GDPR Art. 9 special-category data without explicit consent | Medium (EU users) | High (legal) | Priming consent screen before family-longevity / stress / social block; "Skip these" path leaves fields nil; future analytics backend MUST gate sensitive event transport on EU consent toggle |
| Onboarding completion rate < 30% (drop-off cliff) | Medium | High | Per-screen telemetry from day one; compression branch ready; A/B option: trim dot-grid escalator to 1 screen instead of 3 |
| LifeGridDotView jank on iPhone 12 (4160 dots) | Low-Medium | Medium | `Canvas(rendersAsynchronously: true)`, precomputed dot geometry, `TimelineView(.animation)` wrapper, `Color.lerp` inside Canvas closure — never per-dot `withAnimation` |
| HealthKit decline forecloses recovery | Low | Low | Surface "Open Settings" affordance (`UIApplication.openSettingsURLString`) in Profile — Apple cannot re-prompt programmatically after decline |
| Reactive estimate animations stutter on older devices | Low | Low | 60fps target on iPhone 12; profile in Instruments; built-in `.contentTransition(.numericText())` is GPU-batched |
| Sheet-dismissal SwiftData crash | Low | High | Reference `docs/solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md`; avoid holding @Model references in dismissed paywall sheet; `PaywallProductsView` shared core minimizes the surface |
| Tone tension surfaces late: "Full Brainrot" copy slips through despite agency rule | Medium | Medium | First-class mention in this plan; review checklist includes agency-grep against forbidden verbs; ship a copy-review pass mid-Phase 4 |
| Existing user (pre-rebuild) gets stuck on old onboarding | Low | Low | Phase 4 upgrade-install rule: `currentProfile != nil` AND `anchorAdjustedAt == nil` → one-time recalibration (lifestyle additions + dial only), tracked via `onboardingV2CompletedAt` |
| Removing memento-mori case stalled (separate task) blocks tone alignment | Low | Low | This plan does NOT depend on the side-note; tone selector renames can happen in parallel without conflict |

## Resource Requirements

- **Engineering**: 1 senior iOS engineer, ~4–6 weeks of focused work. Can compress to ~3 weeks with a designer pair on Phases 3, 4, 7.
- **Design**: 2 mascot art assets (positive + negative); copy review for all 30 screens; dot-grid color palette; archetype copy + sub-meter axes.
- **Testing**: 100-user TestFlight cohort for the conversion + completion KPI targets.
- **Legal/copy**: pre-submission spot-check by the founder against `CLAUDE_HANDOFF.md:57-59` rules.

## Future Considerations

- **Localization**: all copy lives in agency-framed templates; structuring for `String.LocalizationKey` from day one is cheap and pays off when the app expands beyond English.
- **Per-archetype daily flow**: archetypes are surfaced once during onboarding but could drive daily quest selection in `Features/Quests/`. Out of scope for this plan; flag for a future plan.
- **Re-onboarding**: long-dormant users (≥90 days inactive) might benefit from a re-onboarding flow that re-runs the lifestyle questions. Requires the dial to be re-adjustable, which CONFLICTS with the "one-time" semantics. Defer.
- **Engine confidence intervals**: the `partialEstimate` could expose ±X yrs uncertainty bands rather than a single number. Brainrot-lite version of the reveal. Defer to a future post-launch tuning plan.
- **Goal-based personalization across the app**: `primaryGoal` is captured but only used by the recovery animation. Could drive daily copy, archetype-specific quests, and notification cadence. Future plan.

## Documentation Plan

- `docs/products/life-clock/CLAUDE_HANDOFF.md` — note the new copy gate "no doom default" needs ongoing enforcement; add a per-screen review checklist.
- `docs/products/life-clock/MONETIZATION.md` — update the conversion-moment section to reflect the new end-of-onboarding paywall.
- `docs/products/life-clock/CLOCK_MODEL.md` — add the five new lifestyle factors to the rules table with citations.
- `docs/products/life-clock/PHASE_STATUS.md` — add Phase 7 (or whatever phase number is next) for the rebuild.
- `docs/products/life-clock/onboarding-funnel.md` — NEW. Defines every telemetry event, the expected sequence, and drop-off thresholds.
- `docs/solutions/` — once any non-obvious issue is solved during implementation (e.g. promotional-offer signature wrangling, reactive animation jank on iPhone 11), capture as a learning per the `/workflows:compound` pattern.

## Sources & References

### Origin

- **Brainstorm document**: [docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md](docs/brainstorms/2026-05-01-life-clock-reveal-onboarding-anchor-dial-brainstorm.md). Key decisions carried forward:
  1. Bounded ±5 yr healthspan dial folded into engine reveal screen, ONE-TIME ONLY.
  2. Five new lifestyle factors (BMI, cardio, family longevity, stress, social) with sourced coefficients.
  3. Full Brainrot tactics adopted for STRUCTURE; copy adapted to agency framing per `CLAUDE_HANDOFF.md`.
  4. Clock mascot from iOS app icon with positive + negative states; dot grid reacts.
  5. Pace-based archetypes (Marathoner / Sprinter / Sleeper / Outlier).
  6. Goal-driven recovery animation cycling per goal × archetype.
  7. HealthKit auth moves to after reveal+dial.
  8. ~~Two-stage paywall: yearly/monthly anchor + 80%-off overlay with "I'd rather pay full price" dismissal.~~ **Replaced during deepening** with single-tier paywall + intro pricing (Cal AI rejection precedent — see Enhancement Summary §1).
  9. Free vs Pro split unchanged from `MONETIZATION.md`.

### Internal References

- Schema rules: [LifeClockSchema.swift:5-13](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)
- Engine current state: [ClockEngine.swift:19-79](products/life-clock-ios/Sources/Engines/ClockEngine.swift)
- Engine tests: [Tests/ClockEngineTests.swift](products/life-clock-ios/Tests/ClockEngineTests.swift)
- Existing paywall: [PaywallSheet.swift](products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift)
- Subscription store: [SubscriptionStore.swift:21, 24](products/life-clock-ios/Sources/Services/SubscriptionStore.swift)
- Product IDs: [PaywallProductID.swift:5-10](products/life-clock-ios/Sources/Services/PaywallProductID.swift)
- HealthKit auth: [LiveHealthKitService.swift:58-62](products/life-clock-ios/Sources/Services/LiveHealthKitService.swift)
- Existing onboarding: [OnboardingView.swift](products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift)
- UITests: [LifeClockUITests.swift:10-32](products/life-clock-ios/UITests/LifeClockUITests.swift)
- Animation precedent: [ClockHandView.swift:18, 49](products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift)
- Footgun list: [CLAUDE_HANDOFF.md:38-59](docs/products/life-clock/CLAUDE_HANDOFF.md)

### Internal Learnings

- `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md` — load-bearing for Phase 1 schema additions.
- `docs/solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md` — mitigates a known crash class in the multi-stage paywall sheet flow.

### External References

#### Engine science
- CDC FastStats — life expectancy at birth (current baseline anchor in `ClockEngine.populationBaseline`).
- Cohen, S. (1988) — Perceived Stress Scale (PSS-10) reference for `perceivedStressScore`.
- Holt-Lunstad, J. et al. (2010, 2015) — social connection mortality meta-analyses.
- Sebastiani, P. et al. (2012); Atzmon, G. et al. (2010) — parental longevity and offspring mortality.
- Lee, I-M. et al. (2014); Physical Activity Guidelines (2018) — cardio mins/week mortality reduction.
- Global BMI Mortality Collaboration (2016) — BMI mortality U-curve.

#### Apple platform docs
- [Implementing introductory offers in your app — Apple Developer](https://developer.apple.com/documentation/storekit/implementing-introductory-offers-in-your-app)
- [Product.PurchaseOption — Apple Developer](https://developer.apple.com/documentation/storekit/product/purchaseoption)
- [What's new in StoreKit and IAP — WWDC25](https://developer.apple.com/videos/play/wwdc2025/241/)
- [SchemaMigrationPlan — SwiftData](https://developer.apple.com/documentation/swiftdata/schemamigrationplan)
- [MigrationStage — SwiftData](https://developer.apple.com/documentation/swiftdata/migrationstage)
- [ModelConfiguration.CloudKitDatabase.none](https://developer.apple.com/documentation/swiftdata/modelconfiguration/cloudkitdatabase-swift.struct/none)
- [SwiftUI Canvas](https://developer.apple.com/documentation/swiftui/canvas) + [`rendersAsynchronously`](https://developer.apple.com/documentation/swiftui/canvas/rendersasynchronously)
- [`accessibilityReduceMotion`](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion)
- [`ContentTransition.numericText(value:)`](https://developer.apple.com/documentation/swiftui/contenttransition/numerictext(value:))
- [Authorizing access to health data](https://developer.apple.com/documentation/healthkit/authorizing-access-to-health-data)
- [`HKHealthStore.requestAuthorization`](https://developer.apple.com/documentation/healthkit/hkhealthstore/requestauthorization(toshare:read:))
- Apple HIG — onboarding & permission timing patterns.
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — esp. 1.4.1 (medical claims), 3.1.1 (deceptive purchase flows), 3.1.2(c) (subscription pricing prominence), 5.1.1(ii) (purpose strings), 5.6 (Developer Code of Conduct — manipulative purchase flows).
- [App Store Privacy Details](https://developer.apple.com/app-store/app-privacy-details/) — sensitive-data classification.
- [`Logger`](https://developer.apple.com/documentation/os/logging/generating_log_messages_from_your_code) with `privacy: .private` qualifier.

#### App Store enforcement precedents (rejection vectors)
- [Cal AI App Store crackdown — TechCrunch (April 2026)](https://techcrunch.com/2026/04/21/apples-cal-ai-crackdown-signals-its-still-policing-the-app-store/) — pulled for two-stage paywall + price-prominence + "second purchase flow after decline." Critical precedent for our paywall design.
- [WeCroak on the App Store](https://apps.apple.com/us/app/wecroak/id1248149943) — approved precedent for mortality-framed apps; positioned as contemplation/mindfulness not medical intervention.

#### Onboarding & paywall patterns
- [Mobile App Onboarding: 5 Paywall Optimization Strategies — AppAgent](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/)
- [Apple Subscription Offers Guide for Developers 2026 — Adapty](https://adapty.io/blog/apple-subscription-offers-guide/)
- [State of In-App Subscriptions 2026 — Adapty](https://adapty.io/state-of-in-app-subscriptions/)

#### Source pattern
- Brainrot onboarding video provided by founder — pattern reference; see brainstorm for extracted patterns.

### Related Work

- `docs/products/life-clock/MONETIZATION.md` — current free/Pro split + intended paywall timing.
- `docs/products/life-clock/CLOCK_MODEL.md` — engine rules + transparency principles.
- `docs/products/life-clock/PHASE_STATUS.md` — phase tracking (this plan adds the next phase).
- Side-note task chip: "Reintroduce Firm/Direct tone + rename labels" (parallel work, no conflict).
