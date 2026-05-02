---
title: Life Clock — collapse tab bar to Today + History + Profile
type: refactor
status: in-review (PR #20 open; pre-merge fixes applied 2026-05-02)
date: 2026-05-01
shipped_pr: https://github.com/kashane1/ai-company-os/pull/20
notes:
  - "Phase 3 (Reflection) was initially deferred due to a SwiftData/iOS 26 trap.
    Root-caused on rebase: ModelContext does not retain its ModelContainer on
    iOS 26.4 simulator. Fix in LifeClockStore (hold modelContext.container
    in a stored property) unblocked Phase 3 and 2 pre-existing crashing
    LifeClockStoreTests as a side effect. Phase 3 then landed with all 9
    DailyReflectionStoreTests passing."
  - "2026-05-02 review pass (workflows:review): five P1 + four P2 findings
    addressed pre-merge — see 'Pre-merge review fixes' section below.
    Schema version corrected from no-op (1,1,0)→(1,1,0) to (1,1,0)→(1,2,0);
    DailyReflection.dayKey promoted to @Attribute(.unique); fetchReflection
    full-table scan replaced with predicated fetch; ReflectionPrompts cache
    removed; ReflectionSheet gained .large detent; ReflectionCard combined
    accessibility element + hint; misleading ledger comment corrected."
origin: in-conversation brainstorm (Claude + Codex), 2026-05-01 — captured in this plan's "Strategic frame" and "Sources" sections; no standalone brainstorm file
deepened: 2026-05-01
reviewed: 2026-05-02
---

# Life Clock — collapse tab bar to Today + History + Profile

## Enhancement Summary

**Deepened on:** 2026-05-01
**Sections enhanced:** Phase 1, Phase 2, Phase 3 (substantially rewritten), Phase 4, Risk Analysis, Open Questions, System-Wide Impact, Acceptance Criteria, Sources

### Key improvements from research/review pass

1. **iOS 17 API correctness — `Calendar.Component.dayOfYear` is iOS 18+ only.** The project's deployment target is iOS 17.0. Replaced with `Calendar.ordinality(of: .day, in: .year, for:)` (iOS 8+). Without this fix, Phase 3 would not compile.
2. **SwiftData property-default invariant.** `Sources/Models/LifeClockSchema.swift:11-13` documents a hard rule: every non-optional stored property must have a property-level default, or lightweight migration silently fails on upgraded devices (NSCocoaErrorDomain 134110, writes no-op invisibly). The original `DailyReflection` sketch violated this. Fixed with property-level defaults; required for all new fields.
3. **Store-mediated reads/writes are mandatory, not optional.** Codebase grep proves there is exactly **one** `@Query` site app-wide (`RootView` for profile presence). The original plan incorrectly stated `HistoryView` used `@Query`; it does not — it reads through `LifeClockStore`. `ReflectionCard` must follow the store-mediation pattern (`var todayReflection: DailyReflection?` + `func saveReflection(...)`), not introduce a second `@Query` site.
4. **Timezone race + double-tap race on reflection upsert.** `Calendar.startOfDay(for:)` is timezone-current; a user crossing time zones can see today's reflection disappear, save again, end up with two rows. Switched to `Int dayKey` (yyyyMMdd) which is timezone-stable, matches the `HistoricalImportCoordinator.dayKey` precedent, and removes the upsert race surface. `@Attribute(.unique)` is **not** added in this version.
5. **Reflection ships with `DayDetailView` readback in scope, not as a follow-up.** Per NN/g diary-study research and the Day One precedent: a reflection users can write but never read again is the canonical abandonment driver. Promoted from "Future Considerations" to in-scope.
6. **Today screen tightening.** `momentumCard` (a retrospective summary) is removed from Today entirely — its content belongs in History now that History is shipped. Reduces card count from 8 to 7 and sharpens "Today is forward-facing."
7. **Phase 4 stale-reference sweep is now an explicit grep recipe** with whitelisting, not "review for any references."
8. **Open questions cut from 6 to 1.** The other five are decided in-plan with rationale.

### New considerations discovered

- The `LifeClockStore.ledger: [TimeLedgerEntry]` in-memory mirror has no production read consumer post-refactor (only tests touch it). Plan now decides explicitly to keep it (with a code comment) rather than refactor it as part of this change.
- `Sources/` Xcode project file uses folder references — but verify `LifeClock.xcodeproj/project.pbxproj` does not list deleted files explicitly before Phase 1 build.
- `TARGETED_DEVICE_FAMILY` should be checked if iPad support is intended (per `docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md`).
- `ToneMode.todayInterpretation(...)` must take primitives (`Int`, `String?`), not SwiftData entities — matches the existing `wrapUpPositiveBody(minutes:)` precedent and preserves `ToneMode`'s `Foundation`-only import boundary.

---

## Overview

Reduce the Life Clock iOS tab bar from **5 tabs** (Today, Progress, Plan, History, Profile) to **3 tabs** (Today, History, Profile) by consolidating Progress (`TimeLedgerView`) and Plan (`QuestsView`) content into a denser, reorganized Today screen. Reframe Quest-flavored copy as behavioral-mirror "Plan" language inside Today, and add a small new **Reflection** card that closes the daily loop.

The data models behind the removed tabs (`TimeLedgerEntry`, `Quest`) **stay**. The screens and tab-bar entries go.

This is a UX-density and IA refactor, not a rebuild. Today already shows compact versions of nearly everything that lived on Progress and Plan, so the bulk of the work is **delete + reorder + reword**, with one genuinely new surface (Reflection — persisted, with History readback) and one product-language pass (Quest → Plan / behavioral-mirror).

## Problem Statement

The current 5-tab structure has two redundant destinations:

- **Progress (`TimeLedgerView`)** — a flat list of `TimeLedgerEntry` rows that duplicates the top-3 "What influenced today's progress" card already on Today (`driversCard` at [TodayView.swift:141](products/life-clock-ios/Sources/Features/Today/TodayView.swift)). With the History tab now shipped (PR #18/#19), the deeper "look back at past entries" job belongs in History via `DayDetailView`, not in a Progress tab.
- **Plan (`QuestsView`)** — renders the same `store.todayQuests` list that Today's `questsCard` already shows ([QuestsView.swift](products/life-clock-ios/Sources/Features/Quests/QuestsView.swift) vs. [TodayView.swift:222](products/life-clock-ios/Sources/Features/Today/TodayView.swift)). The only meaningful difference is preamble copy and per-card layout.

Three downstream consequences:

1. **Wasted nav slots.** Two tabs that don't earn their cost forever in the bottom bar.
2. **Diluted product identity.** Life Clock's center of gravity is *daily reflection that nudges behavior change*, not a quest/task app. A dedicated `Plan` tab implicitly positions the app as gamified task-completion, which contradicts the calmer, post-2026-04-30-UX-pass direction documented in [`PHASE_STATUS.md`](docs/products/life-clock/PHASE_STATUS.md) and the gentle/coach tone modes that survived that pass.
3. **Cognitive overhead for a 20-second user.** Five bottom tabs is the iOS visual ceiling and reads as feature-bloat for a product whose core daily session is a glance + one small action.

## Strategic Frame (carried forward from brainstorm)

The IA decision was settled in a Claude + Codex strategic brainstorm on 2026-05-01:

> Life Clock is a **daily reflection and behavior-awareness app**, not a quest/task app. The core loop is: see today's healthspan signal → understand what drove it → reflect on the choices behind it → follow a small plan for the rest of the day.

Key decisions carried forward into this plan:

- **2 tabs in this area + Profile = 3 total.** Today (forward-facing) + History (retrospective) + Profile.
- **Today stays the command center** but disciplined around one job: help the user interpret today and make a better next decision. Density of meaning, not breadth of modules.
- **Quest → Plan, but as a Today section, not a tab.** The bar for promoting Plan to a top-level tab is when users need to choose, manage, compare, schedule, or evaluate multi-day plans. We're not there yet — and likely won't be inside the v1/early-TestFlight window.
- **Plan copy is behavioral-mirror, not task-list.** Section labels like "What to notice", "One decision to improve", "Your challenge today" replace gamified phrases like "Mark complete" and "Potential +N min".
- **Ledger data lives, the Ledger screen dies.** Retrospective view of `TimeLedgerEntry` happens via History → `DayDetailView`. Today shows top-3 drivers (already does). The full chronological list as a screen is unnecessary surface.
- **Add a Reflection prompt** as the "connective tissue between the healthspan score and behavior change" — and ensure saved reflections re-surface in History (NN/g diary-study research is unambiguous: write-only journals are the #1 abandonment driver).

## Proposed Solution

### Target tab bar

```
[ Today ]   [ History ]   [ Profile ]
```

`AppTab` enum reduces from 5 cases to 3 (`today`, `history`, `profile`). `MainTabView` drops the `TimeLedgerView()` and `QuestsView()` entries.

### Target Today screen (sections in order)

1. **Life Clock** — headline delta + projected healthspan card (existing `headline` + `clockCard`). Unchanged behavior.
2. **Why it changed** — top 3 drivers + interpretation line (existing `driversCard`, retitled and supplemented with a one-line plain-language interpretation). The diet context line stays.
3. **Today's Plan** — `store.todayQuests` rendered with reframed copy (existing `questsCard`, recopy + minor restyle). Per-row "Potential +N min" label is **removed entirely** (decided in-plan; resolves former Open Q2).
4. **Reflection** — NEW. Single rotating prompt card. Tap to write a one-line reflection that persists per day. Saved reflection re-surfaces in History → `DayDetailView` (in scope, not a follow-up).
5. **Quick check-ins** — existing `quickLogCard` + toolbar Check-In button.
6. **Diet streak** — existing `dietStreakBanner` (still conditional, ≥2 days).

`momentumCard` is **removed from Today entirely.** Its content ("X of Y planned actions complete," check-in count) is retrospective summary — exactly what History does. Removing it tightens the "Today is forward-facing" framing and reduces card count from 8 to 7.

Old order:
```
headline → supportMoment → momentum → dietStreak → clock → drivers → quickLog → quests
```

New order:
```
headline → clock → supportMoment → drivers (Why it changed) → quests (Today's Plan) → reflection → quickLog → dietStreak
```

### What gets removed

- `Sources/App/AppTab.swift` — drop `.ledger` and `.quests` cases.
- `Sources/Features/TimeLedger/TimeLedgerView.swift` — delete entire file. Folder can also be removed.
- `Sources/Features/Quests/QuestsView.swift` — delete entire file. Folder can also be removed.
- `Sources/App/ToneMode.swift` — delete `ledgerTitle`, `ledgerEmptyState`, `questsTitle`, `questsPreamble` properties **and** the doc-comment paragraph at lines 7-9 explaining the now-removed `ledgerTitle`.
- `MainTabView` in `LifeClockApp.swift` — drop the `TimeLedgerView()` and `QuestsView()` `.tabItem` blocks.
- `momentumCard` in `Sources/Features/Today/TodayView.swift` — delete the view function and its call site (was at line 97-111).

### What gets kept (do not touch)

- `LifeClockStore.ledger: [TimeLedgerEntry]` — still feeds `todayDrivers` and weekly drivers analytics. **Decision (carried forward from architecture review):** keep as-is with an inline code comment noting "exposed for tests + future debug surfaces; production reads go through `todayDrivers`." Refactoring `ledger` to private + updating 4 test assertions is a separate cleanup, not in scope here.
- `Models/TimeLedgerEntry` — data model stays.
- `Models/Quest` and `Sources/Engines/QuestEngine` — Today still renders `store.todayQuests` and calls `store.toggleQuestCompletion`.
- All tests under `products/life-clock-ios/Tests/` that reference `store.ledger` (`LifeClockStoreTests`, `LifeClockE2ETests`) — they exercise the data model, not the deleted screen.

### What gets reworded (Quest → Plan / behavioral-mirror)

- Today's plan card section title stays `"Today's Plan"` (matches the IA section name); add a one-line subhead `"One small thing to notice or do."` styled `.caption` / `.foregroundStyle(.secondary)`.
- Per-row CTA in `questsCard`: rows are tappable toggles with no explicit CTA today, so no change needed there. **Drop the "Potential +N min" right-aligned label entirely.** Reasoning: behavioral mirror, not points board. The minute estimate stays an engine input; users don't need it on every row.
- "What influenced today's progress" headline → **"Why it changed."** Tighter, matches the IA name.
- Add a one-line plain-language interpretation under the drivers list (e.g. "Today is helping your healthspan because sleep and steps both supported you.") — generated from a new `ToneMode` method that takes **primitives**, not entities (see Phase 2).

### What's new: Reflection card (persisted v1, with History readback)

- A single card titled with a tone-mode-specific heading.
- Body text: one rotating prompt. Pool of **15-20 prompts** (was 10; per best-practices research a returning user sees the same prompt every 10 days at 10-prompt pool, which is noticeable; 15-20 makes the loop ~2-3 weeks).
- Deterministic by day-of-year so it doesn't shuffle on every render.
- Tap → opens `ReflectionSheet` (modeled after `OverrideSheet`, **not** `QuickLogSheet`). User writes one line, taps Save.
- Once a reflection exists for today, the card shows a subtle "Saved." state and the response (truncated) instead of the prompt input. Re-tap edits.
- Saved reflection appears in `DayDetailView` for that day (one-line addition; in scope).
- New SwiftData entity `DailyReflection` added to `LifeClockSchemaV1` as a nested type.
- All reads/writes go through `LifeClockStore` methods (no view-direct `@Query`).

**Hard non-goals for v1 Reflection** (per best-practices research):
- No "all reflections" feed view.
- No share button on a reflection.
- No "shuffle prompt" button.
- No required mood/tag/scale fields alongside the text.
- No auto-save / debounce — save on Done button only.

## Technical Approach

### Architecture impact

This refactor is contained almost entirely within the SwiftUI view layer + a small `ToneMode` trim + one additive SwiftData entity (`DailyReflection`) + a `LifeClockSchemaV1.versionIdentifier` patch bump. No service changes. No engine changes.

### Implementation Phases

#### Phase 1: Tab bar collapse (lowest risk, biggest visible win)

**Pre-flight checks:**

```bash
# 1. Confirm Xcode project does not explicitly reference deleted files
grep -n "TimeLedgerView\|QuestsView" \
  products/life-clock-ios/LifeClock.xcodeproj/project.pbxproj
# Expected: zero hits if project uses folder references; if hits exist,
# remove them in Xcode before deleting the source files.

# 2. Confirm no other branch is touching Today / Progress / Plan / Profile
git log main..feat/life-clock-founder-pack -- products/life-clock-ios/Sources/Features/{Today,Quests,TimeLedger,Profile} 2>/dev/null
git log main..feat/life-clock-mvp-skeleton -- products/life-clock-ios/Sources/Features/{Today,Quests,TimeLedger,Profile} 2>/dev/null
git log main..feat/ux-audit-cleanup-pass -- products/life-clock-ios/Sources/Features/{Today,Quests,TimeLedger,Profile} 2>/dev/null
# Expected: empty (branches are stale relative to main).

# 3. If iPad is a target, verify TARGETED_DEVICE_FAMILY (per ios-ipad-compatibility-mode-cramped-layout.md learning)
grep "TARGETED_DEVICE_FAMILY" products/life-clock-ios/LifeClock.xcodeproj/project.pbxproj
# Expected: 1,2 (with quotes) in both Debug and Release configs if iPad supported.
```

**Edits:**

- Edit `Sources/App/AppTab.swift`: delete `.ledger` and `.quests` cases. Drop their `title` and `systemImage` switch arms.
- Edit `Sources/App/LifeClockApp.swift` `MainTabView`: remove the `TimeLedgerView()` and `QuestsView()` `.tabItem { ... }` blocks. Resulting body has only Today, History, Profile.
- Delete files:
  - `Sources/Features/TimeLedger/TimeLedgerView.swift` (and remove the empty `TimeLedger/` folder).
  - `Sources/Features/Quests/QuestsView.swift` (and remove the empty `Quests/` folder).
- Edit `Sources/App/ToneMode.swift`: delete `ledgerTitle`, `ledgerEmptyState`, `questsTitle`, `questsPreamble`. Delete the now-stale doc-comment paragraph at lines 7-9 explaining the inlined `ledgerTitle`.
- Update `products/life-clock-ios/UITests/LifeClockUITests.swift`: change `plan.complete.0` → `today.planAction.0`. Same accessibility surface, different screen.
- Add `LifeClockStore.ledger` inline comment: `// Exposed for tests + future debug surfaces; production reads go through todayDrivers.`

**Post-flight checks:**

```bash
# Confirm no remaining references to removed tab cases
grep -rn "\.ledger\b\|\.quests\b" products/life-clock-ios/Sources/
# Expected: zero hits in production source. Test files that reference store.ledger are fine.

# Confirm no remaining references to deleted view types
grep -rn "TimeLedgerView\|QuestsView" products/life-clock-ios/
# Expected: zero hits anywhere.
```

##### Phase 1 success criteria

- App builds.
- App boots into Today with 3 tabs visible (verify on iPhone simulator AND iPad simulator if iPad is a target).
- Existing `LifeClockStoreTests` and `LifeClockE2ETests` still pass.
- `LifeClockUITests` pass.
- All grep checks above return expected results.

#### Phase 2: Today reorder + IA-aligned recopy

**Edits in `Sources/Features/Today/TodayView.swift`:**

- Reorder the `VStack` to match the target order above.
- **Delete `momentumCard`** (was at line 97-111) and its call site.
- Rename `driversCard`'s headline from `"What influenced today's progress"` to `"Why it changed"` (one-line edit at [TodayView.swift:143](products/life-clock-ios/Sources/Features/Today/TodayView.swift)).
- Add a plain-language interpretation line below the drivers headline. Source: new `ToneMode` methods (signatures match the existing `wrapUpPositiveBody/wrapUpNegativeBody/wrapUpZeroBody` pattern at `ToneMode.swift:134-163`):
  ```swift
  func todayInterpretationPositive(driverTitle: String?) -> String
  func todayInterpretationNegative(driverTitle: String?) -> String
  func todayInterpretationPreData() -> String
  ```
  These take **primitives only** (no `LifeClockEstimate`, no `[TimeLedgerEntry]`) so `ToneMode` keeps its `Foundation`-only import boundary. View derives `(deltaSign, topDriverTitle)` from `store.todayEstimate?.dailyTimeDeltaMinutes` and `store.todayDrivers.first?.title`.
  - Add accessibility identifier `today.drivers.interpretation` on the new line.
- Rework `questsCard`:
  - Drop the "Potential +N min" right-aligned label per row.
  - Add a one-line subhead under the section title: `Text("One small thing to notice or do.").font(.caption).foregroundStyle(.secondary)`.
  - Keep the section title `"Today's Plan"` (case-sensitive — matches IA section name).

**Post-flight checks:**

```bash
# Catch dead gates left behind by reorder (per incomplete-refactor-auto-detection learning)
grep -nE "\.isEmpty|== nil|\.disabled" products/life-clock-ios/Sources/Features/Today/TodayView.swift
# Review each hit — confirm it's intentional or remove.
```

##### Phase 2 success criteria

- New ordering renders correctly on iPhone 12-class device + iPad.
- "Why it changed" interpretation copy reads naturally in both `gentle` and `coach` tone modes.
- All accessibility identifiers remain stable; new `today.drivers.interpretation` exists.
- Snapshot of Today (manual review) matches the target IA.
- All tests pass.

#### Phase 3: Reflection card + sheet + History readback (persisted, store-mediated)

**Step 1: Add `DailyReflection` to `LifeClockSchemaV1`**

In `Sources/Models/LifeClockSchema.swift` — **nest the model inside the schema enum**, do not create a new file:

```swift
enum LifeClockSchemaV1: VersionedSchema {
    static var versionIdentifier: Schema.Version = Schema.Version(1, 1, 0)  // bumped from (1, 0, 0)
    static var models: [any PersistentModel.Type] = [
        UserProfile.self,
        DailyHealthSnapshot.self,
        HabitLog.self,
        LifeClockEstimate.self,
        TimeLedgerEntry.self,
        Quest.self,
        WeeklyReport.self,
        DailyReflection.self,            // ← new
    ]

    // ... existing nested @Model classes ...

    @Model
    final class DailyReflection {
        // dayKey is yyyyMMdd in the calendar at write time. Timezone-stable.
        // Mirrors the HistoricalImportCoordinator.dayKey precedent.
        var dayKey: Int = 0
        var prompt: String = ""
        var response: String = ""

        init(dayKey: Int, prompt: String, response: String) {
            self.dayKey = dayKey
            self.prompt = prompt
            self.response = response
        }
    }
}
```

At the typealias block at the bottom of `LifeClockSchema.swift:266-272`, add:

```swift
typealias DailyReflection = LifeClockSchemaV1.DailyReflection
```

**Why these specific choices** (consolidating data-integrity and pattern-recognition reviews):

- **Property-level defaults on every non-optional field.** Required by the schema-file rule at `LifeClockSchema.swift:11-13` (cite postmortem `docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`). Without these, lightweight migration silently fails on upgraded devices (NSCocoaErrorDomain 134110).
- **`Int dayKey` instead of `Date date`.** A `Date`-based key requires `Calendar.startOfDay(for:)` at write and `==` predicate at read; `startOfDay` is timezone-current, so a user crossing time zones would see today's reflection disappear and could write duplicates. `Int dayKey = year*10000 + month*100 + day` is timezone-stable and matches the existing `HistoricalImportCoordinator.dayKey` pattern (`Sources/Services/HistoricalImportCoordinator.swift:6`).
- **No `@Attribute(.unique)`.** With the upsert path going through a `@MainActor`-isolated store method (Step 2), unique constraint is unnecessary and would crash-on-save in any race that slipped through. Promote to `.unique` in a future V2 only after the store-mediated path has soaked.
- **`versionIdentifier` patch bump to `(1, 1, 0)`.** Patch-bump for additive entity. Even though SwiftData lightweight-migrates without an explicit `MigrationStage`, the bumped identifier is the discoverable record that V1's contents changed. `LifeClockMigrationPlan.stages` stays `[]`.

**Pre-merge gate (TestFlight check):**

```bash
# Mechanical check: has TestFlight shipped between plan write and merge?
gh pr list --state merged --search "testflight in:title" --limit 5
git log --oneline --all | grep -i "testflight" | head
# If a TestFlight build has been cut, escalate Phase 3 to a full V2 migration:
# - create LifeClockSchemaV2 containing all V1 models + DailyReflection
# - add MigrationStage.lightweight(fromVersion: V1.self, toVersion: V2.self)
# - re-point the typealias block at the bottom of LifeClockSchema.swift to LifeClockSchemaV2.*
# - write a V1→V2 snapshot test
# Pure additive entity changes are still V1-safe even post-TF unless an existing entity
# is also being modified in the same release; we are not modifying any existing entity.
```

**Step 2: Add store mediation**

In `Sources/App/LifeClockStore.swift`:

```swift
// Observable property exposed to views
private(set) var todayReflection: DailyReflection?

// In bootstrap() / refreshFromHealthKit() / after saveReflection():
private func reloadTodayReflection() {
    let key = DayKey.from(date: clock.now(), calendar: clock.calendar)
    todayReflection = fetchReflection(dayKey: key)
}

private func fetchReflection(dayKey: Int) -> DailyReflection? {
    var descriptor = FetchDescriptor<DailyReflection>(
        predicate: #Predicate { $0.dayKey == dayKey }
    )
    descriptor.fetchLimit = 1
    return try? modelContext.fetch(descriptor).first
}

@MainActor
func saveReflection(prompt: String, response: String) {
    let key = DayKey.from(date: clock.now(), calendar: clock.calendar)
    if let existing = fetchReflection(dayKey: key) {
        existing.response = response
        existing.prompt = prompt   // re-stamp in case prompt rotated
    } else {
        let new = DailyReflection(dayKey: key, prompt: prompt, response: response)
        modelContext.insert(new)
    }
    do {
        try modelContext.save()
    } catch {
        assertionFailure("DailyReflection save: \(error)")  // DEBUG-loud, RELEASE-silent
    }
    reloadTodayReflection()
}

// For History readback
func reflection(for date: Date) -> DailyReflection? {
    let key = DayKey.from(date: date, calendar: clock.calendar)
    return fetchReflection(dayKey: key)
}
```

Add `Sources/Shared/DayKey.swift`:

```swift
import Foundation

enum DayKey {
    /// Returns yyyyMMdd as Int. Timezone-stable: uses calendar's day/month/year
    /// components in the calendar's current zone at the moment of computation.
    static func from(date: Date, calendar: Calendar) -> Int {
        let comps = calendar.dateComponents([.year, .month, .day], from: date)
        let y = comps.year ?? 1970
        let m = comps.month ?? 1
        let d = comps.day ?? 1
        return y * 10_000 + m * 100 + d
    }
}
```

**Why store-mediated, not view-direct `@Query`** (consolidating architecture and pattern-recognition reviews):

- App-wide `@Query` invariant: there is exactly **one** `@Query` site (`RootView` for profile-presence routing in `LifeClockApp.swift:134`). Every other view reads through `@Environment(LifeClockStore.self)`. Adding a `@Query` to `ReflectionCard` would be the second site and the first inside a content card — diverges from the codebase norm.
- Save path is race-free only inside `@MainActor` store. View code calling `modelContext.insert` directly bypasses the serialization the store gives you (the documented pattern in `setTodayHabits` at `LifeClockStore.swift:557-583`).
- History `DayDetailView` reads through `store` today; if Reflection is store-mediated, the readback line in `DayDetailView` is one call (`store.reflection(for: snapshot.date)`) — no second read path emerges.

**Step 3: Add `ReflectionPrompts.swift`**

In `Sources/Shared/ReflectionPrompts.swift` (`Foundation`-only, no SwiftUI imports — matches `TimeDeltaFormatter.swift`, `LifeClockPalette.swift` pattern):

```swift
import Foundation

enum ReflectionPrompts {
    private static let pool: [String] = [
        "What's one decision today that future-you would thank you for?",
        "Where did you choose the harder, healthier option?",
        "What pulled you off your plan today?",
        "What's one small thing you'd do differently tomorrow?",
        "What did you notice about how your body felt today?",
        "What's one habit that's quietly helping you?",
        "What's getting in the way of the day you wanted?",
        "What surprised you about today?",
        "What would tomorrow look like if today was a fresh start?",
        "What's one moment you want to remember?",
        "What did you learn about yourself today?",
        "What's one thing you can let go of?",
        "What are you grateful for in your body today?",
        "What's one signal your body is sending you?",
        "What would the next steady version of you do right now?",
    ]

    // @MainActor-safe cache: callers are SwiftUI views, all on main.
    @MainActor private static var cachedDayKey: Int = -1
    @MainActor private static var cachedPrompt: String = ""

    /// Deterministic by day-of-year using `Calendar.ordinality(of:in:for:)`.
    /// IMPORTANT: do NOT use `Calendar.Component.dayOfYear` — it's iOS 18+ only;
    /// the project's deployment target is iOS 17.0 (see project.pbxproj
    /// IPHONEOS_DEPLOYMENT_TARGET). `ordinality(of: .day, in: .year, for:)` is
    /// iOS 8+ and computes the same value (1...365 or 1...366).
    @MainActor
    static func prompt(for date: Date, calendar: Calendar = .current) -> String {
        let dayKey = DayKey.from(date: date, calendar: calendar)
        if dayKey != cachedDayKey {
            cachedDayKey = dayKey
            let dayOfYear = calendar.ordinality(of: .day, in: .year, for: date) ?? 1
            cachedPrompt = pool[(dayOfYear - 1) % pool.count]
        }
        return cachedPrompt
    }
}
```

**Step 4: Add `ReflectionCard.swift` and `ReflectionSheet.swift` to `Sources/Features/Today/`**

`ReflectionCard` is a dumb tap-target:

```swift
struct ReflectionCard: View {
    @Environment(LifeClockStore.self) private var store
    let onTap: () -> Void

    var body: some View {
        let prompt = ReflectionPrompts.prompt(
            for: store.clock.now(),
            calendar: store.clock.calendar
        )

        Button(action: onTap) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text(store.toneMode.reflectionHeading)
                    .font(.headline)
                if let saved = store.todayReflection {
                    Text(saved.prompt)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                    Text(saved.response)
                        .font(.callout)
                        .lineLimit(2)
                        .accessibilityIdentifier("today.reflection.savedResponse")
                    Text("Saved.")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                } else {
                    Text(prompt)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("today.reflection.prompt")
                    Text("Reflect")
                        .font(.callout.bold())
                        .accessibilityIdentifier("today.reflection.openSheet")
                }
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
            .accessibilityIdentifier("today.reflection")
        }
        .buttonStyle(.plain)
    }
}
```

`ReflectionSheet` mirrors `OverrideSheet` (`Sources/Features/History/OverrideSheet.swift`), **not** `QuickLogSheet`:

```swift
struct ReflectionSheet: View {
    @Environment(LifeClockStore.self) private var store
    @State private var response: String = ""
    @State private var isSaving: Bool = false   // disables Save button on tap to defang double-tap race
    let prompt: String
    let onDismiss: () -> Void

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                Text(prompt)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                TextEditor(text: $response)
                    .frame(minHeight: 96)
                    .padding(DesignTokens.Spacing.xs)
                    .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.sm))
                    .accessibilityIdentifier("reflection.editor")
            }
            .padding(DesignTokens.Spacing.lg)
            .navigationTitle("Reflection")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { onDismiss() }
                        .accessibilityIdentifier("reflection.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        guard !isSaving else { return }
                        isSaving = true
                        store.saveReflection(prompt: prompt, response: response)
                        onDismiss()
                    }
                    .disabled(isSaving || response.trimmingCharacters(in: .whitespaces).isEmpty)
                    .accessibilityIdentifier("reflection.save")
                }
            }
            .presentationDetents([.medium])
            .presentationDragIndicator(.visible)
            .accessibilityIdentifier("reflection.screen")
            .onAppear {
                if let saved = store.todayReflection {
                    response = saved.response
                }
            }
        }
    }
}
```

**Step 5: Wire into `TodayView`**

`isPresented` binding lives on `TodayView`, matching `quickLogPresented` pattern:

```swift
@State private var reflectionPresented: Bool = false
// ...
ReflectionCard(onTap: { reflectionPresented = true })
// ...
.sheet(isPresented: $reflectionPresented) {
    let prompt = ReflectionPrompts.prompt(
        for: store.clock.now(),
        calendar: store.clock.calendar
    )
    ReflectionSheet(prompt: prompt, onDismiss: { reflectionPresented = false })
}
```

**Step 6: Surface in History `DayDetailView`** (in scope, not follow-up)

In `Sources/Features/History/DayDetailView.swift`, add a small section that reads `store.reflection(for: dayStart)` and renders the prompt + response if present, nothing if absent. Keep accessibility identifier `dayDetail.reflection`.

**Step 7: Add `ToneMode.reflectionHeading`**

In `Sources/App/ToneMode.swift`, add to the "Wrap-up copy" MARK section (near `yesterdayWrapUpHeading` at line 116):

```swift
var reflectionHeading: String {
    switch self {
    case .gentle: return "Notice today"
    case .coach: return "What stood out today"
    }
}
```

##### Phase 3 success criteria

- All non-optional stored properties on `DailyReflection` have property-level defaults. Verify with grep: `grep -nE '^\s*var\s+[a-zA-Z_][a-zA-Z0-9_]*:\s*(String|Bool|Int|Date|Double)\s*$' products/life-clock-ios/Sources/Models/LifeClockSchema.swift` returns zero hits inside the new entity definition.
- `LifeClockSchemaV1.versionIdentifier` is `Schema.Version(1, 1, 0)`.
- `typealias DailyReflection = LifeClockSchemaV1.DailyReflection` is in the typealias block.
- `LifeClockMigrationPlan.stages` is unchanged (still `[]`).
- `grep -rn '@Query' products/life-clock-ios/Sources/` returns exactly **one** hit (the existing `RootView` profile lookup in `LifeClockApp.swift:134`).
- All reflection writes go through `LifeClockStore.saveReflection`.
- Card renders the deterministic daily prompt; same prompt within one calendar day; different prompt next day.
- Save persists across app launches (verified via `LifeClockStoreTests` or `LifeClockE2ETests`).
- Reflection appears in `DayDetailView` for that day.
- Test pin: rapid double-tap on Save button creates exactly one `DailyReflection` row for today (the `isSaving` guard handles UI; the store's fetch-then-mutate inside `@MainActor` handles persistence).
- Test pin: writing two reflections in one day upserts (does not duplicate). Covered by `DailyReflectionStoreTests` (new file).
- Build over a previous-DEBUG install on a physical device produces **no** `CoreData:` error logs at first launch (catches the migration landmine that the simulator masks).
- iOS 17 simulator + iOS 18 simulator both render correctly (validates no `dayOfYear` API leak).

#### Phase 4: Verification, docs, and stale-reference sweep

**Run the full test suite:** `Tests/` + `UITests/`. Fix any drift.

**Run the iOS simulator UX audit:** `skills/adapters/claude/ios-simulator-ux-audit.md` against the new Today screen.

**Stale-reference grep recipe** (each command should produce zero unwhitelisted hits):

```bash
# Tab labels in life-clock docs (case-sensitive; "plan" lower-case excluded
# because it appears legitimately as "docs/plans/")
grep -rn -E '\b(Progress|Plan|Quest|Ledger)\b' docs/products/life-clock/ \
  | grep -v -E '(docs/plans/|FOUNDER_PACK|MVP_VS|MASTER_FOUNDER)'

# Tab references in iOS source — if anything in Sources/ still mentions
# the deleted tabs by name, the cleanup is incomplete
grep -rn -E '(TimeLedgerView|QuestsView|\.ledger\b|\.quests\b)' \
  products/life-clock-ios/Sources/

# AppTab enum cases — confirm the enum is shrunken
grep -n 'case ' products/life-clock-ios/Sources/App/AppTab.swift
# Expected output: only `case today`, `case history`, `case profile`.

# @Query proliferation guard
grep -rn '@Query' products/life-clock-ios/Sources/
# Expected output: exactly one hit in LifeClockApp.swift (RootView profile lookup).
```

Surviving hits must be either: (a) intentional historical references in plan/audit docs (whitelist by filename), (b) tests against the data model that legitimately reference `store.ledger` (these stay).

**Doc updates** (specific line targets):

- [`docs/products/life-clock/PHASE_STATUS.md:16`](docs/products/life-clock/PHASE_STATUS.md) — replace `Onboarding, Today, Progress, Plan, Weekly, and Profile are all present.` with `Onboarding, Today, History, and Profile are all present; Today now consolidates progress drivers and the daily plan, with a Reflection card. History was shipped in PR #18/#19.`
- [`docs/products/life-clock/UX_GAME_LOOP.md:11`](docs/products/life-clock/UX_GAME_LOOP.md) — replace `Review Progress or Weekly for context` with `Review History for context.`
- [`docs/products/life-clock/UX_GAME_LOOP.md:40-77`](docs/products/life-clock/UX_GAME_LOOP.md) — rewrite the "Today screen" section to enumerate the new ordered sections; **delete the standalone `### Progress` (line 44) and `### Plan` (line 55) sections**; add a new `### Reflection` paragraph explaining the prompt + save flow.
- [`docs/products/life-clock/README.md`](docs/products/life-clock/README.md) — only edit if it enumerates tabs; otherwise leave.

This plan stays as the canonical record of the IA decision and rationale.

## Alternative Approaches Considered

### Alt A: Keep Plan as a separate tab; only kill Progress

- Why considered: minimizes surface change, preserves the "Plan is its own thing" mental model.
- Why rejected: doesn't solve the core IA problem — Today still duplicates Plan's content. And the brainstorm was clear that Plan only earns a tab when it gains multi-day plan management, scheduled commitments, or experiments. None of those are in scope for v1 or near-term.

### Alt B: Replace one of the removed tabs with a Reflection tab

- Why considered: gives Reflection more emotional weight as a destination.
- Why rejected: best-practices research surfaced direct external evidence — Day One's Nov 2024 navigation update explicitly moved Daily Prompt OUT of top-level into a "More" tab. A daily reflection ritual is a Today-shaped behavior, not a destination. A Reflection tab would mostly be empty until the user has saved several reflections, and even then competes for attention with Today. Reflection inside Today keeps the connective tissue between score → drivers → reflection visible at the moment of decision.

### Alt C: Bigger product reposition — kill Quest model entirely, replace with reflection-only flow

- Why considered: consistent with "this is not a quest app" positioning.
- Why rejected: Quest model is load-bearing — `QuestEngine` is well-tested, and removing it is a separate, larger refactor with engine + persistence implications. This plan keeps Quest internally and reframes its presentation. If, after this lands, the founder still wants to remove the action-completion mechanic entirely, that's a follow-up plan.

### Alt D: Rename Swift `Quest` types to `Plan`

- Why considered: language consistency end-to-end.
- Why rejected: `Quest`, `QuestEngine`, etc. are internal type names with no user-facing leakage once the UI strings change. A rename would touch ~15+ files for cosmetic gain. Marked as low-priority follow-up; **decided in-plan** (was former Open Q1).

### Alt E: Read-only reflection (no persistence) for Phase 3

- Why considered: simpler implementation, no schema change.
- Why rejected: best-practices research is unambiguous (citing NN/g diary-study guidance) — a passive prompt with no input is decorative and re-introduces the "card that doesn't earn its space" problem the plan is otherwise solving. If schedule pressure forces a smaller scope, ship Phases 1+2 only and defer Phase 3 entirely as its own plan; do not ship a read-only stub.

## System-Wide Impact

### Interaction Graph

What runs when a user opens the app under the new structure:

- `LifeClockApp.body` → `RootView` → `MainTabView` (3 tabs).
- `TabView` selects `.today` by default. `TodayView.body` materializes its `VStack`:
  - `headline` reads `store.todayEstimate` (already populated by `store.bootstrap()` → `refreshFromHealthKit()`).
  - `clockCard` reads `store.profile?.hideClock` and `store.todayEstimate.projectedAgeYears`.
  - `supportMomentCard` reads `store.supportMoment` (populated by `SupportMomentPresenter`).
  - `driversCard` reads `store.todayDrivers` + new `store.toneMode.todayInterpretation*(...)` methods.
  - `questsCard` reads `store.todayQuests`. `toggleQuestCompletion(_:)` mutates `Quest.completedAt`, persists via SwiftData, recomputes via `QuestEngine`.
  - **NEW** `ReflectionCard` reads `store.todayReflection`. Tap → `reflectionPresented = true`. Sheet presents `ReflectionSheet`. Save → `store.saveReflection(prompt:response:)` → fetch-then-mutate-or-insert + `try modelContext.save()` + `reloadTodayReflection()`.
  - `quickLogCard` and toolbar present `QuickLogSheet`.
  - `dietStreakBanner` reads `store.dietStreaks`.
- `momentumCard` is **removed**.

No new orchestration paths. Reflection writes are isolated from engine recomputes — `DailyReflection` is not an engine input.

### Error & Failure Propagation

- Removing `TimeLedgerView` / `QuestsView` cannot leak error state — they were pure read views over already-populated store state.
- Reflection persistence: `store.saveReflection` wraps `try modelContext.save()` with `assertionFailure` in DEBUG (loud) and silent degrade in RELEASE. Matches the `assert` already at `LifeClockContainer.swift:29-32`. Save failure surface: one ephemeral reflection lost, not engine state.

### State Lifecycle Risks

- `store.todayQuests` and `store.toggleQuestCompletion` continue to function identically; only their second consumer (the deleted `QuestsView`) is gone.
- `store.ledger` continues to feed `todayDrivers` derivation; its in-memory mirror has no production read consumer post-refactor (kept with explanatory comment).
- New `DailyReflection`: `dayKey` (Int yyyyMMdd) is timezone-stable. Upsert-by-day is correct because `saveReflection` is `@MainActor` and fetch-then-mutate-or-insert; double-tap defended by `isSaving` flag in `ReflectionSheet`. Prompt rotation is deterministic across renders (static cache).

### API Surface Parity

- Public `LifeClockStore` API gains: `var todayReflection: DailyReflection?`, `func saveReflection(prompt:response:)`, `func reflection(for:) -> DailyReflection?`. No existing API breaks.
- `ToneMode` gains: `func todayInterpretationPositive(driverTitle:) -> String`, `func todayInterpretationNegative(driverTitle:) -> String`, `func todayInterpretationPreData() -> String`, `var reflectionHeading: String`. Loses: `ledgerTitle`, `ledgerEmptyState`, `questsTitle`, `questsPreamble`. All take primitives — no SwiftData entity coupling.
- New `Sources/Shared/DayKey.swift` and `Sources/Shared/ReflectionPrompts.swift` are `Foundation`-only.

### Integration Test Scenarios

These are cross-layer scenarios mocked unit tests would miss:

1. **Tab bar renders 3 tabs after a fresh install.** UITest: app launches into onboarding → completes onboarding → asserts `tabBars.buttons.count == 3` and the labels are Today, History, Profile.
2. **Cold-launch with no persisted Quests still renders Today's Plan section without crashing.** XCTest against `TodayView` snapshot or manual: `store.todayQuests == []` → section renders empty state.
3. **Tone-mode swap updates Today copy live.** Unit/UI: change tone mode in Profile → return to Today → verify "Why it changed" interpretation copy and Reflection prompt heading update without app restart.
4. **Reflection save → History readback.** UITest: open Today → tap reflection → write text → Save → switch to History → drill into today's `DayHistoryRow` → assert response visible at `dayDetail.reflection`.
5. **Day-rollover prompt rotation.** Unit (with injected clock): advance clock past midnight → assert `ReflectionPrompts.prompt(for:)` returns a different prompt; advance back to same day → assert deterministic same prompt.
6. **Device install over previous-DEBUG build.** Manual gate: install previous build, run, then install new build with `DailyReflection` schema add; confirm no `CoreData:` errors in the console at first launch and existing entity reads still succeed.

## Acceptance Criteria

### Functional

- [ ] `AppTab` enum has exactly 3 cases: `.today`, `.history`, `.profile`.
- [ ] `MainTabView` renders exactly 3 tab items.
- [ ] `Sources/Features/TimeLedger/` and `Sources/Features/Quests/` are deleted.
- [ ] `ToneMode.ledgerTitle`, `ledgerEmptyState`, `questsTitle`, `questsPreamble` are removed; doc-comment paragraph at `ToneMode.swift:7-9` is removed; no remaining references in source.
- [ ] Today screen sections render in the new order: Life Clock → support moment (conditional) → Why it changed → Today's Plan → Reflection → Quick check-ins → Diet streak (conditional). `momentumCard` is deleted.
- [ ] Drivers card title reads "Why it changed."
- [ ] Drivers card includes a plain-language interpretation line under the title via `ToneMode.todayInterpretation*` methods (primitives only).
- [ ] Today's Plan section uses non-gamified copy (no "Mark complete," no per-row "Potential +N min").
- [ ] Reflection card renders with a deterministic daily prompt; saves persist across launches; saved reflection re-surfaces in `DayDetailView`.
- [ ] `DailyReflection` lives nested inside `LifeClockSchemaV1`; typealias added; `versionIdentifier` is `Schema.Version(1, 1, 0)`; `LifeClockMigrationPlan.stages` is `[]`.
- [ ] `LifeClockUITests` is updated for any moved accessibility IDs and passes end-to-end.

### Non-functional

- [ ] No measurable change in cold-launch time. (`TabView` constructs all tab root views eagerly; removing two minimal `View` structs is sub-millisecond. Skip Instruments.)
- [ ] iPad layout still readable (`.readableColumn()` already applied; verify in iPad simulator).
- [ ] All accessibility identifiers from `today.*` namespace remain stable for tests; new IDs added: `today.drivers.interpretation`, `today.reflection`, `today.reflection.prompt`, `today.reflection.openSheet`, `today.reflection.savedResponse`, `reflection.screen`, `reflection.editor`, `reflection.cancel`, `reflection.save`, `dayDetail.reflection`.
- [ ] Every non-optional stored property on `DailyReflection` has a property-level default literal. Pre-merge grep: `grep -nE '^\s*var\s+[a-zA-Z_][a-zA-Z0-9_]*:\s*(String|Bool|Int|Date|Double)\s*$' Sources/Models/LifeClockSchema.swift` returns no hits inside the `DailyReflection` block.
- [ ] `grep -rn '@Query' products/life-clock-ios/Sources/` returns exactly one hit (`RootView` in `LifeClockApp.swift:134`).
- [ ] Project compiles for iOS 17 deployment target. No `Calendar.Component.dayOfYear` references — only `Calendar.ordinality(of: .day, in: .year, for:)` is used.

### Quality gates

- [ ] All existing `Tests/` pass.
- [ ] All existing `UITests/` pass.
- [ ] New tests added: `DailyReflectionStoreTests` covering upsert (one per day), prompt determinism, day-rollover, double-save guard.
- [ ] Manual simulator UX audit shows the new Today reads coherently.
- [ ] Doc updates landed at the specific line targets in Phase 4.
- [ ] All Phase 4 grep checks return expected results (or whitelisted exceptions explained inline).
- [ ] Manual device test: install over previous-DEBUG build produces no `CoreData:` errors at first launch.

## Success Metrics

- **Engineering:** zero net-new `MigrationStage` entries; ~150-300 lines deleted; ~150-220 lines added (Reflection card + sheet + store methods + DayKey + prompts + History readback + interpretation copy). Net negative or neutral LOC.
- **Product:** post-merge dogfood session — founder reports Today reads as a coherent daily ritual without needing to swipe to Plan or Progress, and a saved reflection feels like it lands somewhere (visible in History).
- **No regression in:** TestFlight blockers (`PHASE_STATUS.md` blockers list), engine determinism (`ClockEngineTests` pass), wrap-up flow (`WrapUpCoordinatorTests` pass), `@Query` invariant (1 site).

## Dependencies & Prerequisites

- **No coordination with the History branch needed.** History tab was shipped to `main` via PR #18 (commit `cdf3fc4`) and hardened in PR #19 (commit `5b57480`). The original brainstorm framing ("History is on a separate branch") is outdated. Validation: `git log --oneline -20` on main shows both merges are landed.
- **No active feature branch is touching Today, Progress, Plan, or Profile** (verified with the Phase 1 pre-flight `git log main..feat/...` checks).
- **Pre-TestFlight status** confirmed at plan write per [`PHASE_STATUS.md`](docs/products/life-clock/PHASE_STATUS.md) line 5. Re-confirm with the Phase 3 `gh pr list / git log` mechanical check at execution time.
- **iOS 17 deployment target** confirmed at `LifeClock.xcodeproj/project.pbxproj` (`IPHONEOS_DEPLOYMENT_TARGET = 17.0`). Constrains us off `Calendar.Component.dayOfYear` (iOS 18+) and the new iOS 18 `Tab { }` initializer.

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `Calendar.Component.dayOfYear` accidentally introduced (iOS 18+; project targets iOS 17) | Medium | High (compile failure) | Use `Calendar.ordinality(of: .day, in: .year, for:)` only. Comment in `ReflectionPrompts.swift` explains the rationale. CI: `grep -rn 'Component.dayOfYear\|\\.dayOfYear' products/life-clock-ios/Sources/` should return zero hits. |
| `DailyReflection` non-optional fields without property-level defaults brick the store on device upgrade (NSCocoaErrorDomain 134110) | Medium | **Critical** (silent data corruption) | Property-level defaults required on every non-optional field. Cite the postmortem in code comment. Phase 3 success criterion includes the grep gate and the device-upgrade install gate. |
| Timezone change creates phantom "today" reflection rows | Medium | Medium (duplicate UX confusion) | `Int dayKey` (yyyyMMdd) replaces `Date` as the day key. Timezone-stable. Matches `HistoricalImportCoordinator.dayKey` precedent. |
| Double-tap on Save creates two `DailyReflection` rows | Medium | Medium | `isSaving` flag in `ReflectionSheet` disables Save after first tap; `@MainActor` store method serializes writes; fetch-then-mutate inside the same call. Test pin in `DailyReflectionStoreTests`. |
| Second `@Query` site introduced in `ReflectionCard` (diverges from app-wide invariant) | Low (now that store mediation is mandatory) | Medium | Phase 4 `grep -rn '@Query'` gate enforces exactly one hit. Plan explicitly forbids `@Query` in `ReflectionCard`. |
| `LifeClockUITests` references accessibility IDs from deleted views (`plan.complete.0`) and breaks CI | High | Medium | Phase 1 includes the UITest update as part of the same change. Verified locations via grep. |
| Removing `ledger*` / `quests*` ToneMode strings breaks an unseen call site | Low | Low | Grep confirmed only the deleted views referenced them. Re-grep at PR-prep time. |
| Xcode project file references the deleted Swift files explicitly | Medium | Low | Phase 1 pre-flight grep on `project.pbxproj`. |
| Schema change post-TestFlight requires V2 migration | Low (pre-TF as of plan-write) → High (post-TF) | High | Phase 3 mechanical TestFlight check (`gh pr list / git log`) is a hard gate before merge. Note: pure additive entity is V1-safe even post-TF *unless* an existing entity is also being modified — we are not modifying any existing entity, so the V2 escalation is conservative. |
| Reflection feels orphan/decorative without re-surfacing in History | Resolved (in scope) | Medium | `DayDetailView` readback is in Phase 3, not deferred. |
| iPad rendered in iPhone compatibility mode | Low | Medium (cosmetic but ugly) | Phase 1 pre-flight grep on `TARGETED_DEVICE_FAMILY` if iPad is intended. Per `docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md`. |
| Dead gates (`isEmpty`, `== nil`, `.disabled`) left behind by Today reorder | Low | Medium (silent dead code) | Phase 2 post-flight grep. Per `docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md`. |

## Resource Requirements

- **Effort:** ~1.5-2 days of focused iOS work for Phase 1 + Phase 2 + Phase 3 (now including History readback). Phase 1 alone is ~2 hours. Phase 4 (verification + docs) is ~2-3 hours.
- **Skills required:** SwiftUI view composition, SwiftData additive schema work, `@MainActor` discipline, test maintenance.
- **Reviewers:** founder (UX direction + copy), one iOS reviewer for code-shape (especially the schema add and store method).

## Future Considerations

### When a Plan tab becomes worth promoting

Promote Plan to a top-level tab only when one of these is true:

- Multi-day programs / experiments ship (e.g. "7 days of earlier dinner").
- Plan history and outcomes become its own product surface.
- Adaptive coaching paths or coach-generated plan adjustments ship.
- Users need to choose between plans, schedule commitments, or compare plan variants.

### When Reflection might justify its own destination

If reflections become long-form, paired with coach replies, or surfaced in weekly summaries as a primary artifact, Reflection could promote into a top-level tab — or a History sub-section. Do not predict; let usage tell.

### Possible follow-ups (not in this plan)

- Rename `Quest` Swift types to `Plan` (cosmetic; ~15 files).
- Add a "weekly reflection" rollup to the History weekly card.
- Promote `DailyReflection.dayKey` to `@Attribute(.unique)` in V2 once the store-mediated upsert path has soaked.
- Refactor `LifeClockStore.ledger` to private + update test assertions to use `store.recentLedger(limit:)`.
- Extend Reflection prompts with tone-mode-specific copy beyond the heading.

## Documentation Plan

See Phase 4 for line-specific edit targets. Summary:

- `PHASE_STATUS.md:16` — single-line update to reflect the new tab list.
- `UX_GAME_LOOP.md:11, 40-77` — rewrite Today section, delete Progress + Plan standalone sections, add Reflection paragraph.
- `README.md` — only edit if it enumerates tabs.

## Sources & References

### Origin

- **In-conversation brainstorm (Claude + Codex), 2026-05-01.** Key decisions carried forward into this plan:
  1. 2-tab structure (Today + History) plus Profile, replacing 5-tab layout.
  2. Quest content reframed as Plan **inside Today**, with behavioral-mirror copy ("What to notice", "One decision to improve", "Your challenge today") rather than gamified task language.
  3. Add a Reflection prompt as the connective tissue between healthspan score and behavior change.
  4. Bar for promoting Plan to a top-level tab: users need to choose, manage, compare, schedule, or evaluate multi-day plans.

### Internal references

- Tab enum: [Sources/App/AppTab.swift](products/life-clock-ios/Sources/App/AppTab.swift)
- Tab bar wiring: [Sources/App/LifeClockApp.swift:145](products/life-clock-ios/Sources/App/LifeClockApp.swift)
- Container + migration plan wiring: [Sources/App/LifeClockContainer.swift](products/life-clock-ios/Sources/App/LifeClockContainer.swift)
- Schema rules + nested-model + typealias convention: [Sources/Models/LifeClockSchema.swift:5-13, :266-272](products/life-clock-ios/Sources/Models/LifeClockSchema.swift)
- Today view: [Sources/Features/Today/TodayView.swift](products/life-clock-ios/Sources/Features/Today/TodayView.swift)
- Plan view (to delete): [Sources/Features/Quests/QuestsView.swift](products/life-clock-ios/Sources/Features/Quests/QuestsView.swift)
- Progress view (to delete): [Sources/Features/TimeLedger/TimeLedgerView.swift](products/life-clock-ios/Sources/Features/TimeLedger/TimeLedgerView.swift)
- History view (already shipped): [Sources/Features/History/HistoryView.swift](products/life-clock-ios/Sources/Features/History/HistoryView.swift)
- DayDetailView (readback target): [Sources/Features/History/DayDetailView.swift](products/life-clock-ios/Sources/Features/History/DayDetailView.swift)
- Sheet pattern reference: [Sources/Features/History/OverrideSheet.swift](products/life-clock-ios/Sources/Features/History/OverrideSheet.swift)
- Store upsert pattern reference: [Sources/App/LifeClockStore.swift:557-583](products/life-clock-ios/Sources/App/LifeClockStore.swift)
- ToneMode primitive-method pattern: [Sources/App/ToneMode.swift:134-163](products/life-clock-ios/Sources/App/ToneMode.swift)
- DayKey precedent: [Sources/Services/HistoricalImportCoordinator.swift:6](products/life-clock-ios/Sources/Services/HistoricalImportCoordinator.swift)
- UITests: [UITests/LifeClockUITests.swift](products/life-clock-ios/UITests/LifeClockUITests.swift)

### Institutional learnings (`docs/solutions/`)

- [docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md](docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md) — **Critical** application: every `DailyReflection` non-optional stored property must have a property-level default.
- [docs/solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md](docs/solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md) — Conditional application: not currently in scope (no Delete affordance), but mandatory-read if Phase 3 grows a delete-from-sheet flow.
- [docs/solutions/integration-issues/catchbook-navigation-revamp-rollout.md](docs/solutions/integration-issues/catchbook-navigation-revamp-rollout.md) — Sibling product nav refactor; informs the "each phase must build and run before the next" discipline encoded in Phase 1 pre/post-flight checks.
- [docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md](docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md) — `TARGETED_DEVICE_FAMILY` pre-flight check.
- [docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md](docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md) — Phase 2 dead-gate post-flight grep.

### External references

- [Calendar.Component | Apple Developer Documentation](https://developer.apple.com/documentation/foundation/calendar/component) — confirms `dayOfYear` is iOS 18+.
- [Calendar.ordinality(of:in:for:) | Apple Developer Documentation](https://developer.apple.com/documentation/foundation/calendar/ordinality(of:in:for:)) — iOS 8+ replacement.
- [How to create a complex migration using VersionedSchema — Hacking with Swift](https://www.hackingwithswift.com/quick-start/swiftdata/how-to-create-a-complex-migration-using-versionedschema) — SwiftData lightweight vs. explicit migration boundaries.
- [Never use SwiftData without VersionedSchema — Mert Bulan](https://mertbulan.com/programming/never-use-swiftdata-without-versionedschema) — documents the failure modes that bite apps mutating shipped V1 schemas.
- [Day One — A Navigation Update: Introducing the Journals and More Tabs (Nov 2024)](https://dayoneapp.com/releases/major-navigation-update-with-journals-more-tab/) — direct precedent for moving Daily Prompt OUT of top-level.
- [NN/G — 6 Tips for Better Participant Engagement in Diary Studies](https://www.nngroup.com/articles/better-diary-studies/) — research backing the "no over-prompting / readback required" Reflection design.

### Related plans / brainstorms

- [docs/plans/2026-04-27-002-feat-life-clock-ios-mvp-skeleton-plan.md](docs/plans/2026-04-27-002-feat-life-clock-ios-mvp-skeleton-plan.md) — original MVP skeleton that established the 5-tab structure being collapsed here.
- [docs/brainstorms/2026-04-30-history-wrapups-brainstorm.md](docs/brainstorms/2026-04-30-history-wrapups-brainstorm.md) — the brainstorm behind PR #18 that shipped History.
- [docs/brainstorms/2026-05-01-history-deferred-followups-brainstorm.md](docs/brainstorms/2026-05-01-history-deferred-followups-brainstorm.md) — the follow-up cleanup pass on History (PR #19).

### Related PRs

- PR #18 — History tab + Yesterday Wrap-Up sheet + animation (commit `cdf3fc4`).
- PR #19 — History/wrap-up/override hardening (commit `5b57480`).

## Open Questions for the Founder

Most prior open questions were decided in-plan during the deepening pass. The single remaining question:

1. **Reflection prompt heading — gentle/coach copy.** This plan proposes `gentle: "Notice today"`, `coach: "What stood out today"`. Founder review for tone consistency with other ToneMode strings (`yesterdayWrapUpHeading`, `historyLongAbsenceHeading`).

### Decisions made by author (do not require founder action; flag only if they object)

- **Quest type rename → defer** (was Q1). Internal names; ~15 files for cosmetic gain.
- **"Potential +N min" per-row label → drop entirely** (was Q2). Behavioral mirror, not points board.
- **Reflection persistence → persisted v1 with History readback** (was Q3 + Q5). Read-only stub rejected per NN/g research; orphan reflections rejected per same.
- **Reflection prompt source → canned pool of 15-20** (was Q4). LLM coaching out-of-scope.
- **Tab persistence across launches → no, keep `.today` reset on launch** (was Q6). Three tabs, Today is the anchor; no `@SceneStorage`.

## Pre-merge review fixes (2026-05-02)

A `/workflows:review` pass on 2026-05-02 surfaced corrections needed before
merging PR #20. Addressed:

### P1 fixes (correctness)

- **Schema version was a no-op bump.** PR initially kept `versionIdentifier`
  at `(1, 1, 0)` — the same value already shipped by the reveal-onboarding
  migration on 2026-05-01 (commit `25fa6b7`). Bumped to `(1, 2, 0)`. Any
  device that already migrated to V1.1 will lightweight-migrate to V1.2
  with the additive `DailyReflection` entity.
- **`fetchReflection` was an unbounded full-table scan.** Initial
  implementation called `modelContext.fetch(FetchDescriptor<DailyReflection>())`
  and filtered in memory because of an unverified concern that
  `#Predicate` on `Int` keypaths could trap on iOS 26. The codebase has
  zero precedent for `Int`-keyed predicates, but every other entity uses
  `#Predicate` cleanly on `Date` keys with no trap. Replaced with
  `#Predicate { $0.dayKey == key }` + `fetchLimit = 1`. Bounded; matches
  the project pattern (e.g. `LifeClockStore.fetchSnapshot(for:)`).
- **`DailyReflection.dayKey` was not unique.** Plan declared `.unique`
  intentionally deferred to V2 to avoid race-induced save crashes. But
  the entity is brand-new in V1.2 — no legacy rows to collide. Without
  `.unique`, any bug in the upsert path silently produces duplicates.
  Promoted to `@Attribute(.unique) var dayKey`. Dropped the redundant
  `id: UUID` field (UUID was unused for lookup; `dayKey` is the natural
  unique key).
- **Plan was not on the PR branch.** The plan file lived only on `main`;
  PR body link 404'd. Plan now committed to `feat/life-clock-tab-consolidation`.

### P1 fixes (simplicity)

- **`@MainActor` static cache in `ReflectionPrompts` was premature.** The
  cached computation is `Calendar.ordinality(...)` + an array index over
  15 elements — sub-microsecond. The cache propagated `@MainActor`
  isolation to every caller and added a stale-cache hazard if locale or
  calendar changed mid-session. Removed; recompute per call.

### P2 fixes

- **Misleading ledger comment.** Comment claimed the in-memory `ledger`
  array was "kept for tests + future debug surfaces." Inaccurate — the
  array is actively maintained by every write path (`toggleQuestCompletion`,
  `refreshFromHealthKit`, `bootstrap`) as an in-memory mirror of the
  persisted `TimeLedgerEntry` rows. Comment rewritten to reflect that
  the persisted rows are the source of truth and the array is a
  read-side hedge.
- **`ReflectionSheet` only offered `.medium` detent.** Under iPad
  rotation or large keyboard insets, medium can crowd the editor.
  Added `.large` to `presentationDetents`.
- **`ReflectionCard` had four separate VoiceOver elements.** Heading,
  saved prompt, saved response, and "Saved." footer were all read
  individually. Added `.accessibilityElement(children: .combine)` and
  an explicit `.accessibilityHint` so VoiceOver reads one combined
  utterance with a clear action affordance.

### Deferred — needs founder decision before V2

These were surfaced by the review but declared out-of-scope or judged
heavier than a pre-merge fix. They're tracked here so V2 doesn't drop
them on the floor:

- **No delete affordance for a saved reflection.** A user who writes
  something raw at 7am and regrets it at 7pm cannot un-save — `Save`
  is gated on non-empty trimmed input. Plan declared delete out of
  scope citing the `swiftdata-deleting-model-from-child-sheet`
  postmortem. For a reflective journal this is a privacy/dignity
  concern. Cheapest fix: relax the empty-string Save guard and call
  `modelContext.delete(existing)` when response is empty.
- **No draft persistence on app backgrounding.** Plan explicitly
  forbade auto-save / debounce. If a user types three sentences, gets
  a phone call, and SwiftUI tears the sheet down on memory pressure,
  the input is lost. Pattern exists elsewhere in the codebase
  (`OnboardingDraft`).
- **Persisted `prompt` field goes stale on tone change.** `DailyReflection`
  stores the literal prompt string at save time. If a user saves under
  `gentle` and switches to `coach`, the saved row's `prompt` field
  remains in the old voice forever. Currently invisible (prompt pool is
  tone-agnostic). Becomes a regression vector if prompts ever become
  tone-specific. Either drop the `prompt` field (re-derive from
  `dayKey` at read time) or document the invariant.
- **No telemetry on Reflection save/edit.** Other Today primitives emit
  `SupportMomentPresenter.Intent` events; Reflection does not. New
  daily-ritual surface needs measurement to validate the "connective
  tissue" thesis.
- **Test coverage gaps.** Spec-flow review flagged: no UITest for
  Reflection→History readback (plan integration scenario #4 unimplemented);
  no test for the `isSaving` double-tap UI guard (only the store-level
  upsert is tested); no test for tone-mode-swap live update of Today copy.
  Store-level coverage in `DailyReflectionStoreTests` is solid.
- **Three `ToneMode.todayInterpretation*` methods could collapse.** ~47
  LOC for what could be one method. Works as-is; cleanup follow-up.
- **`DayKey.swift` is a 21-LOC helper with three call sites.** Could
  inline as a private store helper. Works as-is; cleanup follow-up.
- **`isSaving` flag in `ReflectionSheet` is belt-and-suspenders given
  the `@MainActor` store path.** Simplicity reviewer flagged for
  removal; spec-flow reviewer wanted a UI-level test. Kept because the
  intent (defang double-tap at the UI layer) is defensible and the
  cost is one `@State`.
- **`DailyReflection.dayKey` claim about the prompt-pool collision
  cycle.** Plan claims a 15-prompt pool gives a "2-3 week loop." With
  `(dayOfYear - 1) % 15`, the same prompt repeats every 15 days, not
  2-3 weeks. Cosmetic; existing test only asserts `pool.count > 10`.
