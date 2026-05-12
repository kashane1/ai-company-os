---
title: Future tab + History summary section
type: feat
status: active
date: 2026-05-11
origin: docs/brainstorms/2026-05-11-life-clock-future-tab-and-history-summary-brainstorm.md
revision: v2 (post-review trim)
prior_plan: ../../.claude/worktrees/priceless-mccarthy-2f81bd/docs/plans/2026-05-11-feat-future-tab-history-summary-plan.md
---

# Future tab + History summary section

## Revision summary (v2 — post-review trim)

This plan was reviewed by `architecture-strategist`, `code-simplicity-reviewer`, `spec-flow-analyzer`, `agent-native-reviewer`, and `learnings-researcher` on 2026-05-11. The v1 plan was structurally sound but sized for a million-user app; v2 trims it for the beta cohort while addressing every P1 correctness/safety finding.

### What v2 cuts (P2 simplicity)

1. **`BaselineHistoryEntry` @Model dropped.** Nothing reads it in v1; deferred with the re-baseline ritual.
2. **Re-baseline ritual deferred to v1.1.** No two-step sheet, no 90-day cooldown, no `Reset trajectory baseline` Profile action in v1. Auto-backfill is the escape hatch; if it feels wrong to the operator, delete-and-reinstall is the v1.0 path.
3. **`WeeklyNarrativeSnapshot` @Model dropped.** Pro long-form narrative computed in-memory on tab open; "Reflection from Sunday, May 10" is derived from `clock.now()` snapped to last Sunday.
4. **Today trajectory peek deferred to v1.1.** Future tab is one tap away; discoverability earns the affordance only after beta data demands it.
5. **Phase 4 + Phase 5 merged.** Both Pro-only, both touch `Narrative.swift`. A Pro tab with sliders but no weekly narrative is a worse first impression than waiting one phase. New "Phase 4: Pro depth."
6. **Phase 6 dissolved.** Polish, telemetry, and cross-screen audit fold into per-phase final-check sessions.
7. **`BaselineCaptureService` inlined.** Single 4-line addition to existing `applyAnchorAdjustment` — not a service.
8. **`BaselineAggregates` / `SliderOverrides` inlined as dictionaries.** One call site each.
9. **Reinstall-recovery sheet dropped.** Heuristic-driven; will trigger for legitimate new users with old Apple Watches. Add back if real beta evidence demands it.
10. **HealthKit-revoked-mid-flight banner dropped.** Existing "HK denied" empty state covers the next-launch case.
11. **Onboarding-incomplete CTA replaced with tab gate.** `AppTab.future` not inserted until `onboardingCompletedAt != nil`. No CTA copy needed.
12. **Cap/floor explainer kept; copy authoring simplified.** Same neutral foreground; clamp-with-tooltip pattern, no per-tone variants of "outside the data we trust."
13. **Phase 0 coefficients doc: 12-citation peer-reviewed rigor → one-page modelling note.** Each coefficient gets one rationale sentence + `// TODO: refine after beta` flag. Citations preserved as comments in code, not a research paper.
14. **Test grid: ~144 goldens → ~30.** Test components (slider thumb in 1 tone × Free/Pro = 2 goldens) + row stacks (3 tones light/dark = 6 goldens) instead of combinatorial layouts. Narrative tests become slot-token assertions, not paragraph-level snapshots.

### What v2 fixes (P1 correctness)

1. **Ship order made consistent.** Inverted order (Phase 2 first) is now the only order stated; Overview and Implementation sections agree.
2. **Phase 2 Future tab visibility gated.** `AppTab.future` insertion is conditional on `LifeClockLaunchConfiguration.futureTabUnlocked` flag (DEBUG-true, RELEASE-false). Flag flips to release-true only when Phase 4 ships. TestFlight users in Phases 2–3 do not see a half-built tab.
3. **`bootstrapV170Baseline` has explicit failure mode.** Sanity-checks `engineYears.isFinite && (engineYears + adjustmentYears) > profile.currentAge`. On failure, leaves `baselineHealthspanYears = nil` so the next cold launch retries (matches `bootstrapQuestPoolEngineFlag` resilience).
4. **Mid-onboarding upgrade case handled.** Bootstrap runs on every cold launch (it's idempotent and cheap); additionally wired into `applyAnchorAdjustment` so dial-completion immediately heals an upgraded-mid-onboarding user.
5. **`CumulativeSummaryCache` concurrency + invalidation contract specified.** Writes are `@MainActor`-only. `refreshFromHealthKit` invalidates inside its save block. Cache has a `contentVersion: Int` field bumped on any `HabitLog` or `DailyHealthSnapshot` delete; stale-detection is `lastIncludedDate < yesterday OR contentVersion != currentContentHash`.
6. **Day 0 boundary state added.** `dayState` machine now has `day0` substate (`days == 0`) with no slider anchors, no chart, baseline-only render. Separates true zero-data from `coldLaunch1to3`.
7. **History summary cache window bounded.** First-walk caps at `max(onboardingCompletedAt, now - 3.years)` with a "since {Year}" affordance in copy when truncation applies.
8. **Floor + cap explainer copy added to Phase 0 deliverable.** Single neutral string per case (not per-tone), surfaced inline next to the projection.
9. **Trajectory cache + scrub-coalesce flag moved onto `LifeClockStore`.** No orchestration leakage into Views.

### What v2 keeps from v1 deepening

The architectural decisions from the v1 deepening pass remain correct: in-place schema bump (no `MigrationStage.lightweight`), property-level defaults on every non-optional new field, `*Engine` static-pure convention, codebase-unprefixed child views, `PaywallSheet` extension instead of a new sibling sheet, pool-vs-template split for short-vs-long copy slots, `personalAdjustmentYears` precedent followed for the new baseline field, deferred shared `Lighting` enum extraction.

---

## Overview

Life Clock ships two complementary depth-of-insight features that elevate the app from "what's broken" polish into "Pro earns its price" territory. Both originate from the 2026-05-11 brainstorm.

1. **Future tab** — a new fourth top-level tab between History and Profile. Forward-looking projection surface. Centerpiece: the user's projected healthspan in years, anchored against a frozen onboarding baseline, with a 6-dimension what-if slider (Pro) that redraws a trajectory chart in real time.
2. **History summary section** — a new section near the top of the existing History tab. Backward-looking cumulative ledger. Hero number of net time delta since install + one-line data-referencing narrative + top-3 contributors panel.

Shared product principle: **free shows what was; Pro shows what could be.** History summary is fully free. Future tab's slider and long-form narrative are Pro depth.

**Ship order (single source of truth):** Phase 0 (research) → Phase 2 (Future tab shell + V1.7.0 migration, tab hidden from RELEASE) → Phase 1 (History summary) → Phase 3 (Trajectory chart) → Phase 4 (Pro depth — slider + long-form narrative + telemetry + polish, tab unhidden on ship). Five phases total.

## Problem statement

Per operator feedback on 2026-05-11: *"a lot of these seem to be sort of minor even remedial tasks. I want the app to feel more premium more smooth and I want the pro features to really bring value."* The 2026-05-10 polish-backlog produced 14 valid prompts but none elevated the app.

Vision Open Question #5 ("Should a Pro user see different drivers / different quests?") has been open since the doc was initialized — Pro is currently the *unlock surface*, not an aspirational tier. This plan closes Q5 by giving Pro a dedicated forward-looking simulator surface with materially deeper value than free.

## Proposed solution

Two-feature delivery sequenced as: Future tab shell + V1.7.0 migration ships first (highest blast radius, maximize TestFlight soak; tab visible only in DEBUG until Phase 4 lands), then History summary (smaller, schema-free), then trajectory chart, then Pro depth. All work respects existing Decided constraints in `vision.md:86-131` — trajectory not prophecy, confidence shipped, currency is time, three tone modes, lighting convention, one notification class, HealthKit data sacred, local-first, iPhone-first.

The plan defers Apple Foundation Models (on-device LLM) to a future flavor-layer decision. Per existing codebase philosophy (5/8 quest-pool affinity plan precedent), the team's pattern is **pre-authored deterministic copy with templated data slots** — no LLM at runtime. Templated composition handles every narrative slot in v1.

## Technical approach

### Architecture — new surfaces

```
products/life-clock-ios/Sources/
├── App/
│   ├── AppTab.swift                    [edit — add case future]
│   ├── LifeClockApp.swift              [edit — conditional FutureView insertion]
│   ├── LifeClockLaunchConfiguration.swift  [edit — fixture knobs, futureTabUnlocked flag]
│   └── LifeClockStore.swift            [edit — atomic baseline write; bootstrapV170Baseline;
│                                              cumulativeDeltaSinceInstall(); trajectoryCache;
│                                              pendingRefreshRequest; @MainActor cache invalidation]
├── Features/
│   ├── Future/                                 [new — 4 files]
│   │   ├── FutureView.swift                    [root; absorbs HeadlineStack + ColdLaunchStates]
│   │   ├── TrajectoryChart.swift               [SwiftUI Charts]
│   │   ├── WhatIfSlider.swift                  [6-dim Pro-gated]
│   │   └── Narrative.swift                     [Free + Pro narrative views]
│   ├── History/
│   │   ├── HistoryView.swift                   [edit — insert install summary]
│   │   └── InstallSummarySection.swift         [new]
│   └── Paywall/
│       └── PaywallSheet.swift                  [edit — optional scrollTo: anchor]
├── Engines/
│   ├── HealthspanEngine.swift          [new — pure static; coefficients inline]
│   └── NarrativeEngine.swift           [new — pure static; in-memory composition]
├── Shared/
│   ├── TrajectoryPoint.swift           [new — Identifiable, Equatable]
│   ├── ToneMode.swift                  [edit — surface-prefixed slots]
│   └── ReflectionPrompts.swift         [edit — pool-of-narratives for short slots]
└── Models/
    └── LifeClockSchema.swift           [edit — bump to 1.7.0 in-place; add 2 fields + 1 @Model]
```

**Net new persistence:** `UserProfile.baselineHealthspanYears: Double?` + `UserProfile.baselineCapturedAt: Date?` + `CumulativeSummaryCache` (single-row). That's it. No `BaselineHistoryEntry`. No `WeeklyNarrativeSnapshot`. No `ProjectionSnapshot`.

### Data flow

```
ONBOARDING (one-time, immutable)
  EngineRevealAndDialView.onAppear
    → ClockEngine.calculateBaseline(profile:).projectedAgeYears   (engineYears)
    → user dials adjustment                                        (dialYears)
    → LifeClockStore.applyAnchorAdjustment(years:)
      → write personalAdjustmentYears + anchorAdjustedAt
      → if profile.baselineHealthspanYears == nil:
          let candidate = engineYears + dialYears
          if candidate.isFinite && candidate > profile.currentAge:
              write baselineHealthspanYears = candidate
              write baselineCapturedAt = clock.now()
          else:
              log warning, leave nil (next launch retries via bootstrap)

EVERY COLD LAUNCH                                                  [NEW — idempotent]
  LifeClockStore.bootstrapV170Baseline
    → if onboardingCompletedAt != nil
       && anchorAdjustedAt != nil
       && personalAdjustmentYears != nil
       && baselineHealthspanYears == nil:
        do {
            let engineYears = ClockEngine.calculateBaseline(profile).projectedAgeYears
            let candidate = engineYears + personalAdjustmentYears
            guard candidate.isFinite && candidate > profile.currentAge else { return }
            baselineHealthspanYears = candidate
            baselineCapturedAt = anchorAdjustedAt  // truthful original capture time
        }
    (cheap O(1) — runs every launch until baseline set; idempotent thereafter)

DAILY / ON-DEMAND (no persistent projection cache)
  refreshFromHealthKit (@MainActor)
    → persist DailyHealthSnapshot for today
    → invalidate CumulativeSummaryCache inside same save block
    → invalidate trajectoryCache (in-memory)
  HealthspanEngine.currentProjection(snapshots:, habits:, baseline:, clock:)
    → recentSnapshots(limit:14), recentHabitLogs(daysBack:14) — batched
    → compute 6-dim rolling averages
    → apply per-dimension coefficients with caps
    → return projected healthspan years + 30-point trajectory
    → NO PERSISTENCE — in-memory only; recompute on tab open or store-invalidation

FUTURE TAB RENDER (live)
  FutureView
    → UserProfile.baselineHealthspanYears (immutable, frozen)
    → LifeClockStore.trajectoryCache — @MainActor in-memory cache
    → state machine: dayState ∈ { day0, coldLaunch1to3, warmingUp4to13, full14plus }
    → if Pro + scrubbing: HealthspanEngine.projectWith(overrides:) — pure function, no fetch

HISTORY SUMMARY RENDER (live)
  InstallSummarySection
    → LifeClockStore.cumulativeDeltaSinceInstall() — @MainActor cache hit
    → cache: CumulativeSummaryCache @Model (single row), contentVersion-tagged
    → first call: batched single fetch from max(onboardingCompletedAt, now - 3.years) → yesterday
    → cache hit: O(1) <5ms
    → day rollover: walk only missing days, increment contentVersion
    → contentVersion mismatch (retroactive HabitLog/DailyHealthSnapshot delete): full recompute
```

## Phases

### Phase 0 — Healthspan modelling note + tone pools authored

**Duration:** 1 session.
**Deliverables:** Two docs.

1. **`docs/products/life-clock/healthspan-coefficients.md`** — one page. Per-dimension coefficient with one-sentence rationale each + `// TODO: refine after beta` flag. Document:
   - 6 dimensions (sleep, dietQuality, steps, exerciseMinutes, extras, nicotine)
   - Cap at +14y from baseline, floor at `max(currentAge + 1, demographicFloor)`
   - Smoking non-linearity rule (when slider > 0, projection caps regardless of other levers)
   - Citations live as inline `// Source: Li 2018 Circulation` comments in `HealthspanEngine.swift`, not in this doc.

2. **`docs/products/life-clock/future-tab-tone-pools-spec.md`** — three-tone copy pool spec for every new narrative slot:
   - Headline subtext: "Updated daily from your last 14 days." × 3 tones
   - Day 0 line: "Your projection arrives tomorrow." × 3 tones (new)
   - Day 1–3 cold-launch line: "Your projection will sharpen as you log days." × 3 tones
   - Day 4–13 transparency line: pre-authored variants for N=4..13 per tone (the *one* templated short slot; 30 strings total — pool-with-discrete-N, not template-with-slot)
   - Free narrative line: strongest-lever variants per dimension × 3 tones (rules-based, slot-filled)
   - Pro long-form narrative templates: paragraph-level slots per data state × 3 tones
   - History summary hero copy: positive net / negative net / day-1 zero-state / day-7 reveal × 3 tones
   - Top-3 contributors panel labels × 3 tones
   - History summary "no signal yet" state (≥7 days but <3 snapshots with data) × 3 tones (new)
   - Cap reached: single neutral string (no per-tone variants — clamp-and-explain pattern)
   - Floor reached: single neutral string

Both docs land before any code. They drive Phase 3 (chart cap/floor copy) and Phase 4 (slider math + narrative composition).

### Phase 1 — History summary section

**Duration:** 2–3 sessions.
**Deliverable:** `feat(life-clock): history summary section with cumulative since-install ledger`

Schema-free; ships safely after Phase 2's migration but doesn't depend on it. Fully free.

**Edit boundaries:**
- `Features/History/HistoryView.swift:28` — insert `InstallSummarySection` as first child of `LazyVStack`
- `Features/History/InstallSummarySection.swift` — new
- `App/LifeClockStore.swift` — add `@MainActor func cumulativeDeltaSinceInstall() -> CumulativeSummary` with cache
- `Models/LifeClockSchema.swift` — add `CumulativeSummaryCache` `@Model` (single-row; `lastIncludedDate: Date = .distantPast`, `contentVersion: Int = 0`, `totalDeltaMinutes: Int = 0`, `topContributors: Data = Data()` JSON-encoded triple)
- `App/LifeClockLaunchConfiguration.swift` — add `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=0|3|7|30` (seeds `profile.onboardingCompletedAt` relative to clock.now())
- `Shared/ToneMode.swift` — add `historySummaryHero`, `historySummaryNarrative`, `historyTopContributorsHeading`, `historySummaryNoSignal`
- `Tests/LifeClockStoreTests.swift` — extend

**Performance gates (binding):**
- First call walks `DailyHealthSnapshot` from `max(profile.onboardingCompletedAt, now - 3.years)` to yesterday. One batched `FetchDescriptor` with a date-range predicate for `HabitLog`. Group into a `[Date: HabitLog]` dict keyed by `startOfDay`.
- **Verify whether `DailyHealthSnapshot` already persists `deltaMinutes`.** If yes, skip engine re-evaluation — just `sum(\.deltaMinutes)`. Check `Models/LifeClockSchema.swift` before implementing.
- Cache result: O(1) hit on second call same day.
- Day rollover: walk only missing days; bump `contentVersion`.
- **Cache invalidation:** any `HabitLog` or `DailyHealthSnapshot` delete bumps `contentVersion`; cache reader compares against current content hash and recomputes on mismatch. `refreshFromHealthKit` invalidates inside its save block.
- **All cache writes `@MainActor`-only.** HK refresh runs on `@MainActor` per existing pattern.

**Behavior:**
- Hero number: `+14d 6h banked since Mar 2` or `−3d 8h since Mar 2` — honest net, same neutral foreground for ±
- "Since {Year}" affordance when 3-year window truncated: `+14d 6h banked since 2023`
- One-line narrative: rules-based, references strongest contributor
- Top-3 contributors panel: cumulative since install (or window start), hidden until ≥7 days of data
- Day 0: `Your ledger starts today. Check back tomorrow.`
- Day 1–6: hero + narrative, contributors hidden
- Day 7+: full section
- Day 7+ with <3 snapshots that have data: "no signal yet" state (HK denied entire week)
- All copy tone-conditional. Excludes today per existing `recentSnapshots(includingToday: false)` convention.

**Acceptance criteria:**
- [ ] History tab renders install summary as the first section above existing rows
- [ ] Hero number computes correctly via `store.cumulativeDeltaSinceInstall()`
- [ ] Day 0 / 1–6 / 7+ states render correctly per `LIFECLOCK_SEED_DAYS_SINCE_INSTALL` fixtures
- [ ] Hero positive and negative use the same foreground; tone copy carries valence
- [ ] All three tones render in light + dark
- [ ] XXL accessibility text does not truncate (`ViewThatFits`)
- [ ] Unit tests cover: zero-snapshots, negative-net, 3-year truncation, retroactive delete (contentVersion bump), HK refresh invalidation race
- [ ] UITest covers day-0, day-7-cutover, no-signal state
- [ ] 3-year truncation surfaces the "since {Year}" copy
- [ ] 8 goldens total: 3 tones × light/dark = 6 + 2 edge states (no-signal, day-0)

### Phase 2 — Future tab shell + V1.7.0 migration + day-state machine (TAB HIDDEN IN RELEASE)

**Duration:** 3–4 sessions.
**Deliverable:** `feat(life-clock): future tab shell + immutable baseline + day-state machine (release-gated)`

Highest-blast-radius change. Ships first to maximize TestFlight soak. **Tab insertion in `MainTabView` is gated by `LifeClockLaunchConfiguration.futureTabUnlocked` — true in DEBUG, false in RELEASE until Phase 4 lands.** TestFlight users in Phases 2–3 see no fourth tab.

**Edit boundaries:**
- `App/AppTab.swift:4-24` — add `case future` with `chart.line.uptrend.xyaxis` SF Symbol
- `App/LifeClockApp.swift:171-175` — insert `FutureView()` conditionally: `if LifeClockLaunchConfiguration.shared.futureTabUnlocked { FutureView() }`
- `App/LifeClockLaunchConfiguration.swift` — add:
  - `futureTabUnlocked: Bool` (DEBUG default true; RELEASE default false; flips RELEASE-true in Phase 4)
  - `LIFECLOCK_JUMP_TO` recognized values: `futureDay0`, `futureColdLaunch`, `futureWarmingUp`, `futureFull`, `futureCapReached`, `futureFloorReached`, `paywallWhatIfSection`
  - `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=N` (shared with Phase 1)
  - `LIFECLOCK_SEED_SLIDER_OVERRIDES` (JSON dict of `dim:value` for deterministic projection seeding)
  - `LIFECLOCK_TELEMETRY_CAPTURE_PATH` (writes emitted events to a JSON file for UITest assertions; opt-in)
- `Models/LifeClockSchema.swift` — bump `versionIdentifier` to `Schema.Version(1, 7, 0)` IN PLACE (no `MigrationStage` split, per `:528-537` convention). Add `baselineHealthspanYears: Double? = nil` + `baselineCapturedAt: Date? = nil` to `UserProfile`. Add `CumulativeSummaryCache` `@Model` (consumed by Phase 1 — schema lands here so the migration carries it). **Every non-optional stored property on new entities MUST have a property-level default** per `swiftdata-mandatory-attribute-migration-landmine.md:162-170`.
- `App/LifeClockStore.swift` — atomic baseline write inside `applyAnchorAdjustment(years:)` with sanity check + `if baselineHealthspanYears == nil` guard; add `bootstrapV170Baseline()` called from container open *and* called from `applyAnchorAdjustment` (idempotent and cheap); add `trajectoryCache: TrajectoryPoint[]?` + `isProjectionValid: Bool` + `pendingRefreshRequest: Bool` (all `@MainActor`-bound). On `refreshFromHealthKit` save: invalidate both `CumulativeSummaryCache.contentVersion` and `trajectoryCache`.
- `Features/Future/FutureView.swift` — new root. Absorbs `HeadlineStack` and `ColdLaunchStates` as private types in the same file.

**Headline stack:**
1. Big number: current projection in `years, months` format (uses `DateComponentsFormatter`)
2. Baseline footnote line: `you started at 84 years` — formatted via same formatter
3. Signed delta: `+3 years, 2 months earned since you started` or `−2 years since you started` — honest, same neutral foreground for ±

**Subtext + info chip:**
- Single line: `Updated daily from your last 14 days` (or Day 4–13 transparency variant when `dayState == warmingUp4to13`)
- Tappable info chip opens `FutureMethodologyTooltip` view

**Day-state machine:**
- `dayState` derived from `clock.now()` − `profile.onboardingCompletedAt`:
  - `days == 0` → `day0` (baseline-only render; "your projection arrives tomorrow" copy; no chart; no slider; no anchors)
  - `1 ≤ days ≤ 3` → `coldLaunch1to3` (baseline-only, calm narrative, no chart, no slider)
  - `3 < days < 14` → `warmingUp4to13` (chart + slider active, N-aware transparency line)
  - `≥ 14` → `full14plus` (full Future tab)
- **Onboarding-incomplete:** `AppTab.future` not rendered at all when `onboardingCompletedAt == nil`. No CTA needed; the tab simply doesn't exist for that user.
- **HealthKit denied (full and after-onboarding):** if `healthDataState == .denied`, render baseline + `Connect Apple Health for a live projection` + Settings deep-link. Slider hidden.
- **HealthKit not-determined (post-baseline):** identical CTA to `.denied` but copy reads `Allow Apple Health` (re-prompt routes via existing onboarding HK prompt). Distinct from `.denied` only in copy.
- **HealthKit authorized zero-data per dimension:** if any dimension has <3 days of samples, treat as cold-launch for that dimension specifically; use onboarding-declared values as resting positions.

**Re-baseline ritual: DEFERRED to v1.1.** No `Reset trajectory baseline` Profile action in v1. Documented in `Future considerations`.

**Acceptance criteria:**
- [ ] `AppTab.future` exists; rendered in `MainTabView` only when `onboardingCompletedAt != nil` AND `futureTabUnlocked == true`
- [ ] DEBUG default `futureTabUnlocked = true`; RELEASE default `false` until Phase 4 ship
- [ ] `LIFECLOCK_INITIAL_TAB=future` works in DEBUG
- [ ] `LIFECLOCK_JUMP_TO=futureDay0|futureColdLaunch|futureWarmingUp|futureFull` fixtures land on the matching day-state
- [ ] V1.6.0 → V1.7.0 lightweight migration succeeds against a real V1.6.0 store snapshot (drop a production-shape copy into the test bundle; open with V1.7 container; assert read/write)
- [ ] Baseline written exactly once in `applyAnchorAdjustment(years:)`; subsequent calls do not overwrite
- [ ] Baseline sanity check rejects NaN / ≤ currentAge values; leaves field nil; bootstrap retries on next launch
- [ ] `bootstrapV170Baseline` runs on every cold launch (idempotent); also runs at end of `applyAnchorAdjustment` to heal upgraded-mid-onboarding users
- [ ] `bootstrapV170Baseline` failure path: malformed profile leaves `baselineHealthspanYears == nil`, doesn't crash
- [ ] HealthKit denied state renders the CTA, not a disabled slider
- [ ] HealthKit not-determined post-baseline renders an allow-prompt CTA
- [ ] Tab does not appear at all when `onboardingCompletedAt == nil`
- [ ] Headline stack uses `ViewThatFits`; handles XXL accessibility text
- [ ] 6 goldens: 3 tones × light/dark on the `full14plus` shell (no chart yet)

### Phase 3 — Trajectory chart

**Duration:** 2–3 sessions.
**Deliverable:** `feat(life-clock): future tab trajectory chart with reference baseline`

Tab stays release-hidden during this phase.

**Edit boundaries:**
- `Features/Future/TrajectoryChart.swift` — new
- `Engines/HealthspanEngine.swift` — new, pure static methods. Coefficients live as `private let` constants at file top with citation comments. API:
  ```swift
  enum HealthspanEngine {
      static func currentProjection(snapshots: [DailyHealthSnapshot], habits: [HabitLog], baseline: Double, clock: EngineClock = .live) -> Projection
      static func weeklyTrajectory(snapshots: [DailyHealthSnapshot], habits: [HabitLog], baseline: Double, weeksBack: Int, weeksForward: Int, clock: EngineClock = .live) -> [TrajectoryPoint]
      static func projectWith(baseAggregates: [Dimension: Double], overrides: [Dimension: Double], baseline: Double) -> Projection
  }
  ```
  All methods static / pure. `[Dimension: Double]` dictionaries inline — no separate `BaselineAggregates` / `SliderOverrides` struct types. `EngineClock` injection follows the `ClockEngine` precedent.
- `Shared/TrajectoryPoint.swift` — new `Identifiable, Equatable` struct

**Chart spec (uses `import Charts`, iOS 17+):** see prior plan §Phase 3 for the `Chart { AreaMark; LineMark; RuleMark }` shape. `interpolationMethod(.monotone)` (honest, no overshooting). `.animation(.smooth(duration: 0.18), value: points)`. `.accessibilityChartDescriptor(self)` for VoiceOver scrubbing.

**Lighting convention:** wrap `Chart` in container with `.shadow(color: .black.opacity(0.22), radius: refSize * 0.55, x: refSize * 0.35, y: refSize * 0.85)`. World-fixed. Defer shared `Lighting` enum extraction.

**Sparse-data rendering:** line segment opacity scales with density in its 14-day window (full opacity at ≥10 days, fades to ~0.4 at ≤3 days).

**Cap and floor:**
- Cap at 105 years. Above this, freeze and surface single neutral string `Projection capped at 105 years.` (no per-tone variants — clamp-and-explain pattern).
- Floor at `max(profile.currentAge + 1, demographicFloor)`. Below this, freeze and surface single neutral string `Projection at minimum.`.
- **Y-domain compression near cap:** when projection within 2y of cap, surface `Near projection ceiling — chart compressed.` annotation; clamp Y-domain to `[projection - 5, cap]` rather than full floor-to-cap. Prevents age-80-with-all-max visually flat chart.

**Acceptance criteria:**
- [ ] Chart renders in `full14plus` with trajectory line and dashed baseline `RuleMark`
- [ ] Chart hidden in `day0` and `coldLaunch1to3`; visible with confidence-faded line in `warmingUp4to13`
- [ ] Cap/floor applied; UI surfaces neutral copy
- [ ] Near-cap chart-compression mode triggers within 2y of cap
- [ ] Sparse-data confidence opacity applied
- [ ] Lighting convention shadow applied to chart container
- [ ] `AXChartDescriptor` allows VoiceOver scrubbing
- [ ] `LIFECLOCK_JUMP_TO=futureCapReached|futureFloorReached` fixtures land on the matching state
- [ ] Unit tests for `HealthspanEngine.weeklyTrajectory`: cold-launch (Day 2), warming-up (Day 8), full (Day 30), sparse, capped, floored, near-cap-compression
- [ ] 4 chart-state goldens: cold-launch, warming, full, near-cap-compressed (single tone, light only — chart visuals don't vary by tone)
- [ ] No frame drops on iPhone 17 during 60-second simulated scroll

### Phase 4 — Pro depth (slider + long-form narrative + telemetry + polish; tab unhide)

**Duration:** 4–5 sessions.
**Deliverable:** `feat(life-clock): pro depth — what-if slider, weekly narrative, telemetry, tab release-unhide`

This is the ship-the-feature phase. Flip `futureTabUnlocked` to RELEASE-true.

**Edit boundaries:**
- `Features/Future/WhatIfSlider.swift` — new
- `Features/Future/Narrative.swift` — new; contains both `FreeNarrativeLine` and `LongFormNarrative` views
- `Features/Paywall/PaywallSheet.swift` — add optional `scrollTo: PaywallSection?` parameter (`.whatIfSimulator`, `.restorePurchases`, etc.). Default `nil` preserves existing behavior.
- `App/LifeClockStore.swift` — add `averageHabits(daysBack:) -> [Dimension: Double]` helper; wire telemetry emit calls
- `Engines/NarrativeEngine.swift` — new, deterministic template-fill for Pro long-form. **In-memory only; recomputed on tab open.** Pure static.
- `App/LifeClockLaunchConfiguration.swift` — flip `futureTabUnlocked` RELEASE-default to `true`. Confirm telemetry capture fixture works.
- `Shared/ToneMode.swift` — extend with long-form narrative paragraph templates
- `Tests/NarrativeEngineTests.swift` — new

**Slider dimensions (6, per brainstorm):**

| Dim | UI label | Personal anchor source | Range / step |
|---|---|---|---|
| sleep | Sleep | `recentSnapshots(limit:14).avg(\.sleepHours)` | 0–10 h, step 0.5 |
| dietQuality | Whole food | habit logs / 14 × 7 | 0–7 days/wk, step 0.5 |
| steps | Steps | `recentSnapshots(limit:14).avg(\.stepCount)` | 0–20000 /day, step 500 |
| exerciseMinutes | Exercise | `recentSnapshots(limit:14).sum(\.exerciseMinutes) / 2` | 0–600 min/wk, step 15 |
| extras | Extras | habit logs / 14 × 7 | 0–14+, step 1 |
| nicotine | Nicotine | habit logs / 14 × 7 | 0–7 days/wk, step 0.5 |

**Personal-current as anchor:** every slider's resting position is the user's actual current 14-day rolling value. Scrubbing is *relative to* personal current.

**Pro gating:**
- Free users see all six slider rows rendered with values, thumbs dim (opacity 0.35) locked. Lock chip per row.
- Tap on locked slider track → presents `PaywallSheet(scrollTo: .whatIfSimulator)`.
- Pro users see active sliders.
- `LIFECLOCK_SIMULATOR_PRO_DISABLED=1` reproduces Free state.
- `LIFECLOCK_JUMP_TO=paywallWhatIfSection` lands directly on the pre-scrolled paywall.

**Slider scrub interaction (performance gates, all bound to `LifeClockStore`):**
- **Memoize 14-day baseline aggregates on scrub-start.** First `onChange` captures `[Dimension: Double]` on `LifeClockStore.scrubBaselineAggregates`. Reuse for subsequent ticks. **Hold for 250ms post touch-end before discarding** (debounced clear) — rapid re-grabs reuse cached aggregates.
- **Disable redraw animation while scrubbing.** `.animation(nil, value: points)` while `isScrubbing == true`; restore `.smooth(duration: 0.18)` on touch-end.
- **Coalesce queued daily-refresh ticks.** `LifeClockStore.pendingRefreshRequest: Bool` flag (counter, not bool — supports multi-touch). Refresh ticks increment while scrubbing; on touch-end with `pendingRefreshRequest > 0`, run exactly one refresh + crossfade.
- **Gesture priority:** wrap slider in `.highPriorityGesture(DragGesture(minimumDistance: 0))` so parent ScrollView doesn't steal slider drags.
- Snap-back on touch-end: slider returns to personal-current. No `Pin scenario` affordance in v1.

**Smoking dominance rule:** when slider > 0 days/week, projection caps regardless of other levers. Documented inline in `HealthspanEngine.swift` coefficient constants.

**Free narrative line:**
- One line below chart, rendered for all users.
- Rules-based composition: identifies strongest lever from current 14-day data, fills tone-conditional template.
- Pools per dimension × 3 tones live in `ToneMode.swift` + `ReflectionPrompts.swift` per Phase 0 spec.

**Pro long-form narrative (was Phase 5; merged here):**
- 3–4 paragraphs: this-week movement, dominant driver, drag, action for next week.
- Each paragraph is a `Template` struct with named slots: `delta`, `dimensionValue`, `count`, `dimensionName`, `comparisonPrior`.
- Slot values format via `DateComponentsFormatter` / `NumberFormatter` for i18n safety.
- 3 tones × 4 paragraphs × ~6 variants per slot = ~72 authored strings (Phase 0 deliverable).
- **In-memory only. No `WeeklyNarrativeSnapshot` @Model.** `NarrativeEngine.compose(forWeekEnding: clock.now().snappedToLastSunday)` runs every tab open. Cheap (sub-50ms over 14 days of in-memory snapshots).
- **Subhead:** `Reflection from Sunday, May 10` — derived from `clock.now().snappedToLastSunday`, not from a persisted timestamp.
- **Pro cancellation handling:** render-layer Pro check. On cancellation, view re-renders, narrative section vanishes. No cache to clear. (If user re-subscribes mid-week, narrative reappears immediately — no waiting for next Sunday.)
- **5:59 AM Sunday transition:** there is no scheduled "tick" anymore. The "this week's narrative" is derived from `clock.now().snappedToLastSunday`. At 5:59 AM Sunday May 17, snapping yields May 10 (last week). At 6:00 AM, snapping yields May 17 (this week). No race possible.

**Telemetry (was Phase 6; merged here):**
- Reuse existing observability (subscription-conversion channel). Pass only event names + dimension enum cases — never values.
- Events emitted: `future_tab_viewed`, `future_slider_scrubbed` (dimension only), `future_pro_paywall_presented`, `history_summary_viewed`.
- **Privacy stance documented:** dimension-enum events ARE behavioral telemetry; the boundary is values-not-categories. Operator-acknowledged scope.
- **Telemetry capture for tests:** `LIFECLOCK_TELEMETRY_CAPTURE_PATH=/tmp/...json` writes emitted events to a JSON file; UITests assert against the file.

**Tab unhide:** flip `futureTabUnlocked` RELEASE-default to `true` in this PR. TestFlight users now see the full Future tab.

**Cross-screen time-unit convention (was Phase 6 §):**
- Today: minutes/hours
- History summary: days+hours
- Future tab: years+months
- Onboarding reveal: years (grandfathered — one-time ritual, outside rolling-app surfaces)
- Append to `vision.md` Decided constraints; operator-only edit, PR proposes the language.
- **Acceptance criterion: audit existing screens for compliance.** Document any pre-existing violations as known-exceptions or fix them in this PR.

**Acceptance criteria:**
- [ ] All 6 slider rows render with personal-current anchors
- [ ] Free users see locked sliders; tap presents `PaywallSheet(scrollTo: .whatIfSimulator)`
- [ ] Pro users scrub a slider; chart redraws within 100ms
- [ ] Scrubbing during a daily refresh: refresh queued, single crossfade on touch-end
- [ ] Snap-back on touch-end (Pro)
- [ ] Gesture priority: parent ScrollView does not steal slider drags
- [ ] Re-grab within 250ms reuses cached aggregates
- [ ] Multi-touch two-finger scrub: pending-refresh counter correctly handles partial release
- [ ] Smoking >0 caps projection per coefficients
- [ ] All-max ≤ cap; all-min ≥ floor
- [ ] `LIFECLOCK_SIMULATOR_PRO_DISABLED=1` → tap slider → PaywallSheet appears
- [ ] `LIFECLOCK_JUMP_TO=paywallWhatIfSection` lands on pre-scrolled paywall directly
- [ ] `LIFECLOCK_SEED_SLIDER_OVERRIDES={"sleep":10,"steps":20000,...}` produces deterministic projection without gestural scrubbing
- [ ] Free narrative line composes correctly across all 6 strongest-lever cases × 3 tones
- [ ] `NarrativeEngine.compose(forWeekEnding:)` produces 3–4 paragraph narrative for all 3 tones
- [ ] Each paragraph references concrete numbers; composition tests verify no zero-slot output
- [ ] All slot values format via `DateComponentsFormatter` / `NumberFormatter`
- [ ] Subhead displays `Reflection from <weekday>, <date>` derived from `clock.now().snappedToLastSunday`
- [ ] Pro cancellation mid-week: narrative section vanishes on re-render
- [ ] Pro re-subscription mid-week: narrative section reappears immediately
- [ ] Sunday 5:59 AM → 6:00 AM clock transition: narrative seamlessly transitions from "last week's" to "this week's" with no scheduled tick
- [ ] Tone-distinctness: paragraph-level diff between gentle/coach/firmDirect ≥ 30% by token diff
- [ ] No mortality lexicon in any tone
- [ ] Telemetry events emit correctly; `LIFECLOCK_TELEMETRY_CAPTURE_PATH` integration verifies emission
- [ ] HealthKit values do NOT appear in any captured telemetry payload
- [ ] Time-unit convention audit: no pre-existing screens violate; any exceptions documented
- [ ] `futureTabUnlocked` flips RELEASE-true in this PR; TestFlight builds show the tab
- [ ] **~16 goldens total:** 2 slider component (Free locked / Pro active) + 6 row stack (3 tones × light/dark) + 6 narrative shapes (3 tones × positive/negative week, light only) + 2 paywall (default / `.whatIfSimulator` scroll)
- [ ] VoiceOver: slider has `accessibilityRepresentation { Slider(value:in:step:) }` with discrete steps

## Alternative approaches considered

### LLM-driven narrative (Apple Foundation Models)

Considered: `import FoundationModels` + `@Generable` for free narrative line and Pro long-form. iOS 26+ A17 Pro+, on-device, zero-cost, ~1–1.5s latency, guided generation guarantees schema conformance.

**Rejected for v1** because: codebase philosophy is "no LLM at runtime, pre-authored deterministic" (5/8 quest-pool affinity plan precedent). Foundation Models cannot do arithmetic safely; narrative must reference concrete numbers. Safest path is template-fill numbers, let the model only reword — which doubles the testing surface for little additional quality. Pre-A17 Pro fallback would require deterministic path anyway.

**Flagged for future:** flavor-layer that takes deterministic template output and asks Foundation Models to lightly reword. Behind feature flag, A/B tested. Separate brainstorm + plan.

### Custom Path-based trajectory chart (no SwiftUI Charts)

**Rejected** because: SwiftUI Charts is iOS 17+ stable, animates cleanly, ships with `AXChartDescriptor` accessibility for free. Marginal aesthetic gain doesn't justify implementation cost. Lighting convention applied via wrapping container preserves visual coherence.

### History summary as a Pro feature

**Rejected** because: brainstorm decision was explicit — `free shows what was; Pro shows what could be`. User's lived history is theirs; Pro earns prediction.

### Re-baseline ritual in v1

**Deferred to v1.1** (this revision). Auto-backfill is "good enough" for upgraded users; if the operator wants a baseline reset, delete-and-reinstall is the v1.0 escape hatch. Adding the ritual to v1 buys a 5-bullet behavioral spec for an action ~zero beta users will take in week 1.

### Refactor shared `Lighting.swift` enum first

**Deferred** because: trajectory chart shadow makes the third call site (`LifeClockMascotView.hand`, `.bezel`, new chart container) — that's the DRY trigger for a follow-up extraction, not blocking work.

## System-wide impact

### Interaction graph

```
ONBOARDING completion
  → EngineRevealAndDialView.onComplete
    → LifeClockStore.applyAnchorAdjustment(years:)
      → existing: personalAdjustmentYears, anchorAdjustedAt
      → NEW: baselineHealthspanYears (if sanity-check passes), baselineCapturedAt
      → NEW: bootstrapV170Baseline() (heals upgraded-mid-onboarding case)

EVERY COLD LAUNCH
  → LifeClockContainer init
    → NEW: bootstrapV170Baseline (idempotent; runs until baseline is set)

DAILY APP FOREGROUND
  → ScenePhase active
    → existing: store.refreshFromHealthKit (@MainActor)
      → existing: persist DailyHealthSnapshot
      → NEW: invalidate CumulativeSummaryCache.contentVersion (same save block)
      → NEW: invalidate trajectoryCache (in-memory)

FUTURE TAB OPEN
  → FutureView.onAppear
    → if trajectoryCache invalid: HealthspanEngine.currentProjection(...) → cache
    → render
  → Pro tab also opens: NarrativeEngine.compose(forWeekEnding: clock.now().snappedToLastSunday)
    → in-memory only; recomputed every open

FUTURE TAB SLIDER SCRUB
  → WhatIfSlider.onScrub(dimension:, value:)
    → first event: LifeClockStore.scrubBaselineAggregates = currentAggregates
    → HealthspanEngine.projectWith(baseAggregates:, overrides:, baseline:)
    → chart redraws via @State binding (animation disabled during scrub)
    → refresh tick queued via LifeClockStore.pendingRefreshRequest++
  → touch-end:
    → 250ms debounced clear of scrubBaselineAggregates
    → if pendingRefreshRequest > 0: single refresh + crossfade

HISTORY TAB OPEN
  → existing: HistoryView render
    → NEW: InstallSummarySection at top
      → store.cumulativeDeltaSinceInstall() — cache hit or window walk
```

### Error & failure propagation

| Error class | Lowest layer | Propagation path | Handled at |
|---|---|---|---|
| `SwiftDataError` migration failure | `LifeClockContainer.init` | crash via fatalError per existing pattern | App relaunch + migration retry |
| `HealthKitAuthError.denied` / `.notDetermined` | `HealthKitConfiguration` | returned status used in `healthDataState` | `FutureView` renders CTA-mode |
| `BaselineSanityError` (logical, not thrown) | `applyAnchorAdjustment` / `bootstrapV170Baseline` | candidate value rejected, field left nil | retried on next cold launch via bootstrap |
| `ProjectionError.insufficientData` (NEW) | `HealthspanEngine` | thrown when <3 days of any dim's data | `FutureView` falls back per-dim to onboarding-declared |
| `ProjectionError.capExceeded` / `.floorExceeded` (NEW) | `HealthspanEngine` | clamped silently; UI surfaces cap/floor copy | `TrajectoryChart` renders neutral string |
| `EntitlementProviding.NotEntitled` | `OverrideService` (existing) | reused for slider tap path | `PaywallSheet(scrollTo:)` presented |
| `NarrativeError.emptyTemplate` (NEW) | `NarrativeEngine` | thrown in tests; in prod, fallback to neutral string | `LongFormNarrative` shows fallback |
| `CumulativeCacheError.contentMismatch` (NEW, logical) | `LifeClockStore.cumulativeDeltaSinceInstall` | content hash != cached → full recompute | transparent to caller |

No silent failure swallowing. Every error class has either a UI affordance, a retry path, or a test contract.

### State lifecycle risks

| Step | Risk | Mitigation |
|---|---|---|
| Baseline atomic write | Partial write if app crashes mid-call | SwiftData @Model writes transactional within modelContext; sanity-check rejects bad values pre-commit |
| Trajectory cache | Stale projection if HK refresh succeeds without clearing | `refreshFromHealthKit` invalidates inside same save block; in-memory cache lifetime tied to store |
| Pro cancellation | Free user briefly sees Pro narrative | Render-layer Pro check evaluates per render pass; no cache to leak |
| CumulativeSummaryCache | Stale after retroactive HabitLog delete | `contentVersion` content-hash mismatch triggers full recompute |
| `bootstrapV170Baseline` | Poison baseline from corrupt profile | Sanity check `(engineYears + adjustmentYears).isFinite && > currentAge` |
| Day 0 / Day -1 timezone edge | User crosses midnight during onboarding | `dayState` computed from `clock.now()` (testable); 24h granularity tolerates timezone drift |
| Scrub multi-touch | Coalesce flag race | `pendingRefreshRequest` is a counter; flush only when all scrubs released |

### API surface parity

| New API | Equivalent existing API | Parity required |
|---|---|---|
| `store.cumulativeDeltaSinceInstall()` | `store.recentSnapshots(limit:)` | Both exclude today by default |
| `HealthspanEngine.weeklyTrajectory(...)` | `ClockEngine.calculateWeeklyTrend(...)` | Both honor `EngineClock` injection |
| `HealthspanEngine.projectWith(overrides:)` | new — no parity needed | Pure function over dictionaries |
| `store.averageHabits(daysBack:)` | `store.recentSnapshots(limit:)` | Both filtered for excluded today |
| `NarrativeEngine.compose(forWeekEnding:)` | new — pure function | No state on engine |

### Integration test scenarios

1. **V1.6.0 → V1.7.0 migration against real user data.** Drop production-shape store snapshot into test bundle. Open with V1.7 container. Assert: V1.6 fields survive, new optional fields nil, `CumulativeSummaryCache` table exists empty.
2. **bootstrapV170Baseline on every cold launch.** Seed `onboardingCompletedAt = Date.distantPast`, `anchorAdjustedAt = Date.distantPast`, `personalAdjustmentYears = 5`, `baselineHealthspanYears = nil`. Cold-launch once → bootstrap fires, baseline set. Cold-launch again → bootstrap no-ops.
3. **bootstrapV170Baseline failure handling.** Seed corrupt profile (currentAge=999). Bootstrap runs, sanity-check fails, baseline stays nil. Repair profile (currentAge=40), cold-launch, baseline now set.
4. **Slider scrub vs daily refresh race.** UITest scrubs sleep slider while `LIFECLOCK_FIXED_DATE` advances by 24h mid-scrub. Assert: chart does not redraw twice; refresh queued; touch-end triggers single crossfade.
5. **Pro cancellation + re-subscription mid-week.** Setup Pro user, open Future tab (narrative visible). Simulate cancellation. Re-open tab — narrative gone. Re-subscribe. Re-open tab — narrative back, same week.
6. **Three-tone all-axes-max snapshot.** `LIFECLOCK_JUMP_TO=futureCapReached` × 3 tones. Assert: projection = 105y; cap copy visible; near-cap chart compression engaged.
7. **CumulativeSummaryCache invalidation race.** Open History tab, observe cumulative. Delete a HabitLog from Day 50. Re-open. Assert: contentVersion mismatch triggers full recompute; new totals reflect deletion.
8. **Onboarding-incomplete tab invisibility.** Force-launch with `onboardingCompletedAt == nil`. Assert: Future tab does not exist in tab bar; no crash.

## Acceptance criteria

### Functional requirements

- [ ] Future tab renders as the fourth top-level tab between History and Profile **only when onboarding complete AND `futureTabUnlocked == true`**
- [ ] Baseline captured exactly once during onboarding (sanity-checked); never silently changed
- [ ] `bootstrapV170Baseline` heals upgraded users; idempotent
- [ ] Day 0 / Day 1–3 / Day 4–13 / Day 14+ states render correctly
- [ ] HealthKit denied / not-determined / authorized-but-empty all handled per spec
- [ ] Trajectory chart renders cleanly in all day-states; cap at 105y; floor at currentAge+1; near-cap compression mode
- [ ] Six-dimension what-if slider — Pro-gated, personal-current anchored, redraws chart in real time
- [ ] Free narrative line composes correctly across all 6 strongest-lever cases × 3 tones
- [ ] Pro long-form weekly narrative recomputed in-memory each tab open; subhead derives from `clock.now().snappedToLastSunday`
- [ ] History summary section: hero number, narrative, top-3 contributors (≥7 days), no-signal state (≥7 days & <3 with-data); 3-year window with "since {Year}" affordance; fully free

### Non-functional requirements

- [ ] No frame drops on iPhone 17 during slider scrub at 120Hz
- [ ] Migration V1.6.0 → V1.7.0 succeeds against production store snapshot
- [ ] No mortality lexicon in any narrative tone
- [ ] All copy passes tone-distinctness check (≥30% token diff between tones at paragraph level)
- [ ] All new persistence respects local-first; no cloud sync
- [ ] Lighting convention applied to trajectory chart
- [ ] All new copy uses `DateComponentsFormatter` / `NumberFormatter` for i18n safety
- [ ] HealthKit values never appear in telemetry payloads (verified via capture fixture)

### Quality gates

- [ ] All new code has unit tests (`HealthspanEngine`, `NarrativeEngine`, store accessors)
- [ ] All new surfaces have UITests + computer-use checkpoint
- [ ] ~30 goldens total: 8 (Phase 1) + 6 (Phase 2 shell) + 4 (Phase 3 chart) + 16 (Phase 4 Pro depth + paywall + narrative + slider)
- [ ] No regressions in existing `LifeClockUITests`, `ProTouchpointsRecon`, `OnboardingRhythmRecon`

## Success metrics

- **Pro conversion uplift.** Target: after Phase 4 ships, rolling 14-day Pro-conversion rate ≥ 1.5× pre-ship baseline.
- **Future tab engagement.** Target: ≥40% of `dayState == full14plus` users view Future tab ≥ 3 times in following 7 days.
- **Slider engagement (Pro).** Target: ≥60% of Pro users who view Future tab scrub at least one slider in following 7 days.
- **History summary engagement (Free).** Target: ≥70% of Free users see install summary section.
- **No regression in retention.** Target: 7-day retention ≥ pre-ship baseline.

## Dependencies & prerequisites

- iOS 17+ deployment target
- SwiftData V1.6.0 stable in production
- `EntitlementProviding` protocol stable
- `LifeClockLaunchConfiguration` fixture-knob system stable
- Existing `ToneMode` + `ReflectionPrompts` pool system

**No external dependencies.** No new third-party packages.

## Risk analysis & mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Healthspan coefficient debate | High | Low | One-page modelling note documents choices; cap at +14y; "refine after beta" flag |
| SwiftData migration failure on real devices | Medium | High | Integration test #1 against production snapshot; lightweight migration documented safe path |
| Lighting convention drift on first chart use | Medium | Low | Phase 3 inline with constants citing `LifeClockMascotView.swift:271-272`; follow-up extraction tracked |
| Pro user retention drop from chart confusion | Low | High | Final-check + computer-use checkpoint catches UX confusion; cap/floor copy reduces surprise |
| Tone-distinctness collapse | Medium | Medium | Phase 0 spec; Phase 4 tests enforce ≥30% token diff |
| SwiftUI Charts performance issue (first use in repo) | Low | Medium | Framework-docs research found no known iPhone 17 issues; perf test in Phase 3 |
| `bootstrapV170Baseline` poison baseline | Low | Medium | Sanity check rejects NaN / ≤ currentAge; retry on next launch |
| CumulativeSummaryCache stale after retroactive delete | Medium | Medium | `contentVersion` content-hash mismatch triggers recompute |
| Greenfield: no prior solutions docs for Charts / Pro gating / scheduling | High | Medium | Front-load Charts perf test (Phase 3); paywall routing edge cases (Phase 4 integration tests) |

## Resource requirements

- **Engineering:** 1 engineer (operator), iterative simulator-driven polish sessions
- **Total estimated effort:** ~12 sessions across 5 phases (vs ~17 in v1 plan — ~30% reduction from cuts)

## Future considerations (v1.1+)

- **Re-baseline ritual.** Profile → `Reset trajectory baseline`. Two-step confirmation, 90-day cooldown, `BaselineHistoryEntry` @Model preserving old baselines. Re-introduced when operator validates need from beta.
- **Today trajectory peek.** `Your trajectory: 87y 2m →` affordance below Today bar. Add after beta data shows tab-discoverability gap.
- **Reinstall-recovery sheet.** Heuristic-driven recovery flow when HK shows >30 days history but `onboardingCompletedAt == today`. Add if real beta evidence demands.
- **HealthKit revoked-mid-flight banner.** One-time banner + chart annotation at discontinuity. Add if reports surface.
- **`BaselineHistoryEntry` @Model.** Tracks re-baseline history; paired with the ritual above.
- **Apple Foundation Models flavor layer.** Lightly reword deterministic template output. Behind feature flag, A/B tested.
- **Watch / iPad / web extensions.** Out of scope for v1 (Decided constraint: iPhone-first).
- **Telemetry-driven coefficient tuning.** Anonymous slider-engagement telemetry feeds back into Phase 0 doc refinement.
- **Shared `Lighting.swift` extraction.** Trigger DRY refactor after this PR lands (third call site materialized).

## Documentation plan

- [x] `docs/products/life-clock/healthspan-coefficients.md` — Phase 0 one-page modelling note
- [x] `docs/products/life-clock/future-tab-tone-pools-spec.md` — Phase 0 tone pool authoring
- [ ] `docs/products/life-clock/vision.md` — append: resolution of Q5; new Decided constraints (immutable baseline; cross-screen time-unit convention with onboarding-grandfathered)
- [ ] `docs/products/life-clock/polish-2026-MM-DD-<phase>-future-*.md` — one session log per phase
- [ ] `docs/solutions/healthspan-projector-modeling-decisions.md` — institutional learning capture post-Phase 4

## Sources & references

### Origin

- **Brainstorm:** [docs/brainstorms/2026-05-11-life-clock-future-tab-and-history-summary-brainstorm.md](../brainstorms/2026-05-11-life-clock-future-tab-and-history-summary-brainstorm.md)
- **Prior plan (v1, pre-review):** [worktrees/priceless-mccarthy-2f81bd/docs/plans/2026-05-11-feat-future-tab-history-summary-plan.md](../../.claude/worktrees/priceless-mccarthy-2f81bd/docs/plans/2026-05-11-feat-future-tab-history-summary-plan.md)

### Internal references

- Tab structure: [products/life-clock-ios/Sources/App/AppTab.swift:4-24](../../products/life-clock-ios/Sources/App/AppTab.swift)
- Tab wiring: [products/life-clock-ios/Sources/App/LifeClockApp.swift:162-180](../../products/life-clock-ios/Sources/App/LifeClockApp.swift)
- Onboarding baseline seam: [products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift:34-56](../../products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift)
- Atomic write entry: [products/life-clock-ios/Sources/App/LifeClockStore.swift:926-933](../../products/life-clock-ios/Sources/App/LifeClockStore.swift)
- Schema versioning: [products/life-clock-ios/Sources/Models/LifeClockSchema.swift](../../products/life-clock-ios/Sources/Models/LifeClockSchema.swift) (esp. :60-67, :472-508, :528-537)
- HistoryView seam: [products/life-clock-ios/Sources/Features/History/HistoryView.swift:28](../../products/life-clock-ios/Sources/Features/History/HistoryView.swift)
- Lighting convention reference: [products/life-clock-ios/Sources/Shared/LifeClockMascotView.swift:271-272,325](../../products/life-clock-ios/Sources/Shared/LifeClockMascotView.swift)
- Today-exclusion convention: [docs/products/life-clock/polish-2026-05-10-history-excludes-today.md](../products/life-clock/polish-2026-05-10-history-excludes-today.md)
- Tone-pools symmetric drama rule: [docs/products/life-clock/polish-2026-05-10-vision-bad-day-gentle-coach-pools.md](../products/life-clock/polish-2026-05-10-vision-bad-day-gentle-coach-pools.md)
- SwiftData migration landmine: [docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md](../solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md)
- SwiftData child-sheet delete: [docs/solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md](../solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md)

### External references (healthspan coefficients — kept as inline citations in code)

- Li et al., Circulation 2018 — ceiling +14y at age 50
- Paluch et al., Lancet Public Health 2022 — HR 0.47 at 8-10k steps/day
- Jha et al., NEJM 2013 — smoking +10y at quit-by-40
- Moore et al., PLOS Med 2012 — +3.4y at 150-300 min/wk MVPA
- Cai et al., GeroScience 2025 — sleep U-curve
- GBD 2020, Lancet 2022 — no safe alcohol level

### External references (iOS frameworks)

- [Swift Charts | Apple Developer Documentation](https://developer.apple.com/documentation/Charts)
- [Model your schema with SwiftData — WWDC23 10195](https://developer.apple.com/videos/play/wwdc2023/10195/)
