---
title: UX audit cleanup — Life Clock iOS + ios-simulator-ux-audit skill graduation
type: refactor
status: active
date: 2026-04-30
deepened: 2026-04-30
---

# UX audit cleanup — Life Clock iOS + ios-simulator-ux-audit skill graduation

## Enhancement Summary

**Deepened on:** 2026-04-30 (same-day pass with focused parallel research agents — SwiftData migration, SwiftUI a11y patterns, xcodegen device-family mechanics, simctl video recording).

### Key improvements

1. **`Quest.slug` must NOT carry `@Attribute(.unique)` in V1.** Adding `.unique` to a property whose existing rows would all default to `""` will fail SwiftData lightweight migration with a uniqueness-violation error. Plan now specifies a two-step path: ship `slug: String = ""` without `.unique`, run an idempotent backfill in `bootstrap()` guarded by a `UserDefaults` flag, then add `.unique` in a later schema version once data is clean. Phase 2.A acceptance updated.
2. **`TARGETED_DEVICE_FAMILY` is already `"1,2"` (universal)** at `project.yml:34` — not missing, as I had assumed. Phase 3.B item 10 is reframed: the bug is that **test targets don't carry the setting**, which lets iPad-destination test runs mask layout regressions (exactly the failure mode in the cited learning). Default Q4 answer flips to "keep universal, add explicit declaration to `LifeClockTests` and `LifeClockUITests` targets."
3. **SwiftUI menu-style `Picker` queries as `app.buttons[id]`, not `app.pickers[id]`.** Phase 2.C XCUITest examples corrected. For deterministic option selection, identify each option inside the Picker's content closure too. For `Slider`, `adjust(toNormalizedSliderPosition:)` is genuinely flaky — pair it with `.accessibilityValue("\(Int(hours)) hours")` for assertion. `Stepper` value cannot be set directly; index `boundBy: 1` for increment, `boundBy: 0` for decrement.
4. **GitHub PR media upload is web-UI-only.** `gh pr edit --body-file` cannot attach video; the only paths to inline `<video>` rendering are (a) web-UI drag-drop into the description editor (yields `https://github.com/user-attachments/assets/<uuid>` URLs that play inline), or (b) release-asset upload (lose inline playback). The LFG step 8 needs a manual-handoff step or a computer-use-driven browser action; documented in the new "Recording + PR attachment recipe" section below.

### New considerations discovered

- **`LifeClockMigrationPlan.stages = []` stub is a footgun if also wired into the container.** SwiftData lightweight inference works automatically when no migration plan is wired *or* when the plan is fully consistent. An empty-stages plan that references multiple `VersionedSchema`s will fail. Verify the container init: either delete the stub or fully wire it.
- **`SUPPORTS_MAC_DESIGNED_FOR_IPHONE`** auto-publishes the iPhone-only build to the Mac App Store as "Designed for iPhone" — explicit `NO` if the product wants to skip Mac availability.
- **`xcrun simctl io recordVideo` requires `kill -INT` for clean shutdown** (SIGTERM/SIGKILL produce unplayable files). The `simctl status_bar override --time "9:41"` etc. is the marketing-quality status-bar normalization pattern.
- **`accessibilityElement(children: .combine)` swallows child identifiers.** Onboarding section parents (`onboarding.baseline`, etc.) must use `.contain`, not `.combine`, or child controls become unreachable.

### Research insights now embedded

- Phase 2.A: SwiftData migration recipe (lightweight inference path, `.unique`-deferred pattern, backfill snippet).
- Phase 2.C: corrected XCUIElement collection mappings (Picker→buttons, Slider→sliders, Stepper→steppers, DatePicker.compact→datePickers+buttons).
- Phase 3.B: TARGETED_DEVICE_FAMILY narrowed to a propagation fix, not a value change.
- New section "LFG step 8 — Recording + PR attachment recipe" appended at the end of the plan.

## Overview

This plan retires the seven review todos (026-032) filed against the 2026-04-30 UX audit diff. The work spans two surfaces:

1. **Life Clock iOS** — refactor `LifeClockStore` to remove a presentation leak, replace fragile string-keyed Quest persistence with a stable slug, add accessibility identifiers across onboarding/QuickLog/Paywall to close agent-native parity gaps, decide and execute on `ToneMode.mementoMori`, and expand the launch-configuration fixtures.
2. **Skill estate** — graduate `ios-simulator-ux-audit` from `stage: draft` to `stage: active` by closing eight spec gaps, relocating the canonical to a product-agnostic path, and adding a contract-freeze fixture.

Two inline fixes from the review are already applied (slim adapter, drop `codex` from `target_runtimes`); they are not re-litigated here.

The plan is sequenced into three phases that minimize merge conflicts and let each subsequent phase verify the previous one. Phase 1 lands the test-enabling infrastructure (launch fixtures + skill graduation). Phase 2 lands the three P1 iOS refactors in conflict-aware order. Phase 3 absorbs the product call on `ToneMode` and sweeps the P3 nits + prevention checks.

### Out of scope (deferred)

- HealthKit live integration (already deferred per todo 024).
- Codex adapter for `ios-simulator-ux-audit` (`target_runtimes: [claude]` until adapter ships).
- Catchbook UITests target (Catchbook does not yet have one — separate work).
- Backfill / migration of pre-rename `"Completed quest:"` ledger entries (verified-empty in P3.B grep before deciding).
- Move from `xcodegen` to native `.xcodeproj`.
- New external dependencies.

## Problem Statement

Codex's UX audit pass shipped substantial product improvements (supportive copy, momentum card, plan-completion persistence, XCUITest target, launch harness) plus a new draft skill that captures the audit procedure for reuse. The multi-agent code review surfaced two classes of follow-up:

**Architectural debt the diff introduced:**
- `LifeClockStore` now constructs `SupportMoment` UI prose inline at six mutation sites — copy lives in mutations, not a presenter.
- Quest completion persists via the tuple `(date, title, category)` — renaming a quest title silently orphans every previously-completed quest with that title. The same logic is reimplemented across four overlapping methods (~70 LOC of redundant upsert code).
- New launch fixtures cover only `onboarding`/`onboarded`; paywall, health-denied, streaks, and fixed-date are unreachable deterministically. Several user-reachable controls (onboarding pickers/slider, QuickLog inputs, Paywall Close/Restore) have no accessibility identifiers — agents cannot complete those flows.

**Existing debt the audit's copy refresh exposed:**
- `ToneMode.mementoMori` was renamed to display "Direct" but several properties now collapse to identical strings across all three tones. The enum dispatch is partly dead code.
- The new `ios-simulator-ux-audit` skill has eight spec gaps that block reuse on a different product (path implies coupling, no preconditions, no `mode` input, output collisions undefined, etc.).

**Cross-cutting risks (per past learnings):**
- Adding any non-optional property to a SwiftData `@Model` without a property-level default bricks lightweight migration (`docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`). The plan adds `Quest.slug` and must respect this.
- `TARGETED_DEVICE_FAMILY` may default to iPhone-only, hiding iPad layout regressions (`docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md`).
- Stale Xcode test bundles hide wrong assertions when running `test-without-building` — Codex's report flagged this and it must be addressed before declaring XCUITest work done.

## Proposed Solution

Three phases, each commit-bounded:

- **Phase 1 — Foundation.** Expand launch fixtures and graduate the skill. Independent of iOS refactors; both can land in parallel.
- **Phase 2 — P1 iOS refactors.** Sequenced quest-slug → presenter extraction → accessibility identifiers. Each step builds on the previous one's settled surface.
- **Phase 3 — Product call + sweep.** ToneMode decision + P3 nits + prevention checks.

Each phase has its own acceptance criteria checklist below. Phase 2 is the largest by LOC and risk; the sequencing inside it is the load-bearing decision in this plan.

## Technical Approach

### Architecture

#### LifeClockStore — surface area after this plan

Today: profile, palette, ledger, quests, health auth, support-moment UI messaging, persistence, four-way upsert. After Phase 2: profile, palette, ledger, quests, health auth, persistence (one upsert), delegating to `SupportMomentPresenter` for all UX prose.

The presenter is a value type; it has no SwiftData dependency; it takes `(intent, deltaContext) -> SupportMoment?`. Tests can exercise it without a `ModelContainer`.

#### Quest persistence — slug-keyed identity

`QuestEngine` emits `Quest.slug: String` (e.g. `"nutrition.water-with-meal.v1"`) with a versioned suffix when intent changes. `LifeClockStore` upserts on `(date, slug)` instead of `(date, title, category)`. The four overlapping methods (`applyPersistedCompletions`, `fetchPersistedQuests`, `persistedQuestRecord`, `fetchPersistedQuest`, `persistedQuestMatches`) collapse to one `upsertQuest(_:)` and one `fetchQuests(on:)`. The fragile string-equality contract on titles is replaced by an explicit identity contract on slugs.

`LifeClockSchema.swift:11-13` documents the schema-wide invariant that every non-optional stored property has a property-level default. Quest currently complies. The new `slug: String = ""` field preserves the rule and is safe under SwiftData lightweight migration.

#### Skill estate — ios-simulator-ux-audit graduation

The skill is currently at `skills/canonical/products/life-clock/ios-simulator-ux-audit.md` — a path that implies product-coupling. Phase 1 relocates to `skills/canonical/ios-simulator-ux-audit/skill.md` (standalone layout, matching `niche-research-brief`, `app-name-discovery`, `content-factory` precedents). Eight spec gaps close in the same edit. A contract-freeze fixture lands at `skills/canonical/ios-simulator-ux-audit/fixtures/happy_path.yaml`, the registry flips to `stage: active, fixture_status: passing`, and a per-skill test at `tests/python/unit/test_ios_simulator_ux_audit_fixtures.py` joins the contract-freeze guard count.

This is a new precedent for the repo — no prior skill has been relocated between layouts. Test coverage of the move is limited to `test_skill_reconciliation.py` (registry-side) and `test_skill_stocktake_skill.py` (drift). Both already pass; the relocation should keep them green.

#### Launch fixtures — orthogonal env vars

Replace the binary `Scenario` enum with composable env-var probes:

- `LIFECLOCK_FORCE_PAYWALL=1`
- `LIFECLOCK_HEALTH_AUTH=denied|authorized|notDetermined`
- `LIFECLOCK_SEED_STREAK=<int>`
- `LIFECLOCK_SEED_QUESTS_COMPLETED=<int>`
- `LIFECLOCK_FIXED_DATE=<ISO8601>`

The existing `LIFECLOCK_UI_TEST_SCENARIO=onboarding|onboarded` stays for backwards-compatible XCUITest authoring. New tests adopt orthogonal probes.

### File-touch list

**New files (5)**
- `products/life-clock-ios/Sources/Shared/SupportMomentPresenter.swift`
- `skills/canonical/ios-simulator-ux-audit/skill.md` (relocated; old file deleted)
- `skills/canonical/ios-simulator-ux-audit/fixtures/happy_path.yaml`
- `tests/python/unit/test_ios_simulator_ux_audit_fixtures.py`
- `products/life-clock-ios/UITests/LifeClockOnboardingFormUITests.swift`

**Modified files (~14)**
- `products/life-clock-ios/Sources/App/LifeClockStore.swift` (P1: phases 2.A and 2.B)
- `products/life-clock-ios/Sources/Engines/QuestEngine.swift` (P1: phase 2.A — emit slug)
- `products/life-clock-ios/Sources/Models/LifeClockSchema.swift` (P1: phase 2.A — add `Quest.slug`)
- `products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift` (phase 1.A — orthogonal env vars)
- `products/life-clock-ios/Sources/Services/MockHealthKitService.swift` (phase 1.A — denied path)
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift` (P1: phase 2.C — ids)
- `products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift` (P1: phase 2.C — ids)
- `products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift` (P1: phase 2.C — Close/Restore ids)
- `products/life-clock-ios/Sources/Features/Today/TodayView.swift` (phase 3.B — driver row + streak chip ids)
- `products/life-clock-ios/Sources/App/ToneMode.swift` (phase 3.A)
- `products/life-clock-ios/UITests/LifeClockUITests.swift` (extend coverage in phase 2.C)
- `products/life-clock-ios/project.yml` (phase 3.B — `TARGETED_DEVICE_FAMILY` decision)
- `skills/registry.yaml` (phase 1.B — flip stage, add comment)
- `.claude/skills/ios-simulator-ux-audit.md` (phase 1.B — `canonical_source` path update)
- `skills/adapters/claude/ios-simulator-ux-audit.md` (phase 1.B — `canonical_source` path update)
- `CLAUDE.md` (phase 1.B if path changes; else no-op)

**Untouched** — `Sources/Shared/SupportMoment.swift`, `Sources/Shared/SupportMomentCard.swift`, `Sources/App/AppTab.swift`, `Sources/App/LifeClockApp.swift`. Phase 3.B may collapse `SupportMoment.Tone` to a `Bool isCelebration` if accepted at triage.

### Implementation Phases

#### Phase 1: Foundation (parallel-safe, unblocks Phase 2)

##### Phase 1.A — Expand `LifeClockLaunchConfiguration` (todo 031)

Add orthogonal env-var probes. Keep `LIFECLOCK_UI_TEST_SCENARIO` for back-compat.

Pseudocode for `Sources/App/LifeClockLaunchConfiguration.swift`:

```swift
struct LifeClockLaunchConfiguration {
    enum HealthAuth: String { case denied, authorized, notDetermined }

    let isUITest: Bool
    let scenario: Scenario
    let forcePaywall: Bool          // LIFECLOCK_FORCE_PAYWALL
    let healthAuth: HealthAuth      // LIFECLOCK_HEALTH_AUTH
    let seedStreak: Int             // LIFECLOCK_SEED_STREAK
    let seedQuestsCompleted: Int    // LIFECLOCK_SEED_QUESTS_COMPLETED
    let fixedDate: Date?            // LIFECLOCK_FIXED_DATE (ISO8601)

    static var current: LifeClockLaunchConfiguration { /* parse ProcessInfo */ }

    func makeHealthService() -> HealthKitServiceProtocol {
        // honor healthAuth: denied path returns mock with authorizationStatus = .denied
    }

    func seedInitialStateIfNeeded(in context: ModelContext) {
        // seed onboarded profile if scenario == .onboarded
        // seed streak entries if seedStreak > 0
        // seed completed quests if seedQuestsCompleted > 0
    }
}
```

Mock health service additions for `Sources/Services/MockHealthKitService.swift`:

```swift
final class MockHealthKitService: HealthKitServiceProtocol {
    init(authorization: HealthAuth = .authorized, ...) { ... }
    var authorizationStatus: HealthKitAuthorizationStatus {
        switch authorization { case .denied: .denied; case .authorized: .authorized; case .notDetermined: .notDetermined }
    }
    // requestAuthorization() honors the configured state
}
```

Acceptance:
- [ ] Five new env vars parsed and exposed as typed properties.
- [ ] `MockHealthKitService` honors `denied`/`notDetermined` states.
- [ ] Existing `onboarding`/`onboarded` scenarios unchanged.
- [ ] Unit test for env-var parsing covers each var, plus malformed inputs (empty, garbage, out-of-range).

##### Phase 1.B — Graduate `ios-simulator-ux-audit` skill (todo 030)

Sequence: relocate canonical → close 8 spec gaps in canonical → update adapter and project-skill pointers → add contract-freeze fixture → add per-skill fixture test → flip stage in registry → run reconciliation tests.

Spec gaps to close in canonical (from todo 030):
1. Add `mode: first-launch | returning-user | both` to `inputs:`.
2. Document preconditions: scheme exists in project, simulator runtime installed, code-sign valid, Xcode CLI tools selected.
3. Define output-collision policy: same-day re-runs append a timestamped H2 to existing file (mirrors adapter trim already shipped).
4. Gate "tests updated for the changed flow" — N/A path documented when no XCUITest target exists; bootstrapping it is the audit's first deliverable in that case.
5. Name the handoff channel: audit doc itself is the handoff (downgraded from aspirational queue/state mechanism). Document that explicitly.
6. Add resume contract: mid-flow interruptions restart from step 1; partial state is not persisted.
7. Reconcile output artifacts: 4 H2 sections in canonical match `outputs:` 4 generic items match adapter template. Drop the playbook's 6-artifact list as aspirational, or fold into canonical and update accordingly.
8. Path relocation: `skills/canonical/products/life-clock/ios-simulator-ux-audit.md` → `skills/canonical/ios-simulator-ux-audit/skill.md`. Update registry `path:`, project skill `canonical_source`, adapter `canonical_source`. CLAUDE.md trigger phrase already references the adapter, not the canonical, so unchanged.

Pseudocode for `skills/canonical/ios-simulator-ux-audit/fixtures/happy_path.yaml`:

```yaml
# Contract-freeze fixture for ios-simulator-ux-audit. Locks the canonical
# body's procedure-section names, required input fields, minimum-checklist
# items, and failure-modes against silent drift.
- name: happy_path
  description: Canonical body still exposes the audit contract.
  input:
    skill_file: canonical/ios-simulator-ux-audit/skill.md
  expected:
    required_section_headings:
      - "## Procedure"
      - "## Minimum Checklist"
      - "## Evidence Standard"
      - "## Output Style"
    required_input_fields:
      - "product path"
      - "Xcode scheme"
      - "target simulator device"
      - "audit mode"
    required_failure_modes:
      - "Simulator won't boot"
      - "Onboarding blocked by permission state"
    required_validation_steps:
      - "app builds for the chosen simulator target"
      - "at least one first-launch and one returning-user flow is exercised"
      - "findings are captured in a dated product doc"
```

Pseudocode for `tests/python/unit/test_ios_simulator_ux_audit_fixtures.py`:

```python
# Mirrors tests/python/unit/test_ios_ui_polish_review_fixtures.py.
import pytest, yaml
from pathlib import Path

FIXTURE = Path("skills/canonical/ios-simulator-ux-audit/fixtures/happy_path.yaml")

def test_canonical_body_satisfies_fixture():
    fixture = yaml.safe_load(FIXTURE.read_text())[0]
    body = (Path("skills") / fixture["input"]["skill_file"]).read_text()
    for heading in fixture["expected"]["required_section_headings"]:
        assert heading in body, f"missing heading: {heading!r}"
    # ... mirror other expected buckets
```

Registry update at `skills/registry.yaml`:

```yaml
- id: ios-simulator-ux-audit
  name: iOS Simulator UX Audit
  path: canonical/ios-simulator-ux-audit/skill.md         # relocated
  owner_agent: ios
  target_runtimes: [claude]
  stage: active                                            # was: draft
  kind: agentic
  # Contract-freeze fixture at
  # skills/canonical/ios-simulator-ux-audit/fixtures/happy_path.yaml
  # locks the procedure section names, required input fields, minimum
  # checklist items, and failure modes. See
  # tests/python/unit/test_ios_simulator_ux_audit_fixtures.py.
  fixture_status: passing                                  # was: missing
  source: internal
  adapters:
    claude: adapters/claude/ios-simulator-ux-audit.md
  project_skill: .claude/skills/ios-simulator-ux-audit.md
```

Acceptance:
- [ ] Canonical relocated; old path no longer exists; all three pointers updated atomically.
- [ ] All 8 spec gaps closed; canonical references the adapter's collision-policy and mode-input language.
- [ ] Contract-freeze fixture present; per-skill fixture test passes.
- [ ] Registry flipped to `stage: active, fixture_status: passing`.
- [ ] `test_skill_reconciliation.py`, `test_skill_stocktake_skill.py`, `test_skill_stocktake_on_live_registry.py` all green.
- [ ] Live drift report (`registry_drift.run()`) shows no NEW drift items (the pre-existing `post-run-validation` orphan is unrelated).
- [ ] CLAUDE.md "available skills" entry drops the `*(draft)*` qualifier.

#### Phase 2: P1 iOS refactors (sequenced, conflict-aware)

##### Phase 2.A — Quest stable slug + persistence collapse (todo 026)

Order matters: schema first, engine second, store third, tests fourth.

Step 1 — schema (`Sources/Models/LifeClockSchema.swift`):

```swift
@Model
final class Quest {
    @Attribute(.unique) var id: UUID = UUID()
    var date: Date = Date(timeIntervalSince1970: 0)
    // NEW — property-level default REQUIRED for lightweight migration.
    // DO NOT add @Attribute(.unique) in this version: existing simulator rows
    // would all default to "" and violate uniqueness. Add .unique in a later
    // schema version once the bootstrap() backfill has shipped on every install.
    var slug: String = ""
    var title: String = ""
    // ... rest unchanged
}
```

**Migration plan stub.** Verify what is currently wired into the `ModelContainer` init. SwiftData performs lightweight inference automatically *if no migration plan is referenced*. The stub at `LifeClockSchema.swift:199-208` (`LifeClockMigrationPlan.stages = []`) is safe only if (a) it is not passed to the container, or (b) it has consistent `schemas` and `stages`. An empty-stages plan that references two `VersionedSchema`s will fail. **First sub-step of Phase 2.A**: read `LifeClockApp.init` / `LifeClockContainer.make` to confirm; if the stub is wired, delete it for V1 (let inference handle the additive change). Document the verification result in the PR body.

**Backfill recipe** (runs once in `bootstrap()`, guarded by `UserDefaults`):

```swift
// In LifeClockStore.bootstrap()
private func backfillQuestSlugsIfNeeded() {
    let key = "didBackfillQuestSlugs_v1"
    guard !UserDefaults.standard.bool(forKey: key) else { return }
    let descriptor = FetchDescriptor<Quest>(predicate: #Predicate { $0.slug.isEmpty })
    guard let needs = try? modelContext.fetch(descriptor), !needs.isEmpty else {
        UserDefaults.standard.set(true, forKey: key)
        return
    }
    for quest in needs {
        quest.slug = QuestSlug.derive(from: quest.title, date: quest.date)
    }
    try? modelContext.save()
    UserDefaults.standard.set(true, forKey: key)
}
```

`QuestSlug.derive(from:date:)` is a small helper (in `Sources/Engines/`) that produces a stable slug from a legacy quest's title — e.g. lowercased, `kebab-cased`, suffixed with the day-bucket. It runs only against rows from before this migration; new rows get their slug from `QuestEngine` directly.

Step 2 — engine (`Sources/Engines/QuestEngine.swift`):

```swift
extension QuestEngine {
    func generateDailyQuests(...) -> [Quest] {
        var quests: [Quest] = []
        if shouldEmitWaterQuest(...) {
            let q = Quest(slug: "nutrition.water-with-meal.v1",
                          date: ..., title: "Add a glass of water with one meal", ...)
            quests.append(q)
        }
        // ... one slug per quest type, versioned suffix when intent meaningfully changes
    }
}
```

Step 3 — store (`Sources/App/LifeClockStore.swift`): collapse the four upsert methods to one.

```swift
private func upsertQuest(_ quest: Quest) {
    let dayStart = clock.calendar.startOfDay(for: quest.date)
    let slug = quest.slug
    let descriptor = FetchDescriptor<Quest>(
        predicate: #Predicate { $0.date == dayStart && $0.slug == slug }
    )
    if let stored = try? modelContext.fetch(descriptor).first {
        stored.title = quest.title  // free-form display; persist for ledger continuity
        stored.completedAt = quest.completedAt
        // ... copy mutable fields
    } else {
        modelContext.insert(quest)
    }
}

private func fetchQuests(on dayStart: Date) -> [Quest] { /* one-line predicate */ }
```

`applyPersistedCompletions`, `fetchPersistedQuests`, `persistedQuestRecord`, `fetchPersistedQuest`, `persistedQuestMatches` are deleted. The `toggleQuestCompletion` and `refreshFromHealthKit` paths call `upsertQuest` / `fetchQuests`.

Step 4 — tests (`Tests/LifeClockStoreTests.swift`): add a "title rename preserves completion" test.

```swift
func testQuestCompletionSurvivesTitleRename() async throws {
    // 1. complete a quest with slug "nutrition.water-with-meal.v1"
    // 2. simulate a copy edit: regenerate quests with same slug, different title
    // 3. assert completedAt persists on the regenerated Quest
}
```

Acceptance:
- [ ] `Quest.slug: String = ""` declared with property-level default.
- [ ] Every `QuestEngine.generateDailyQuests` code path emits a non-empty slug.
- [ ] `LifeClockStore` upsert/fetch is two methods, not five.
- [ ] LOC delta in `LifeClockStore.swift`: at least -50 net.
- [ ] New test passes: rename quest title → completion preserved across `bootstrap()` cold restart.
- [ ] Existing test `testCompletedPlanRestoresAcrossColdRestart` still passes without change.
- [ ] In-place SwiftData migration verified on a simulator with pre-existing Quest rows (delete app first to verify clean install also works).

##### Phase 2.B — Extract `SupportMomentPresenter` (todo 027)

Lands after 2.A so the store mutations are settled. Move all `SupportMoment(title:detail:tone:)` constructors out of `LifeClockStore` into a value-typed presenter.

New file `Sources/Shared/SupportMomentPresenter.swift`:

```swift
struct SupportMomentPresenter {
    enum Intent {
        case onboardingComplete
        case checkInSaved(deltaMinutes: Int, hadPriorCheckIn: Bool, strengthLogged: Bool)
        case questCompleted(rewardMinutes: Int)
        case questUndone
        case reset
    }

    func moment(for intent: Intent) -> SupportMoment? {
        switch intent {
        case .onboardingComplete:
            return SupportMoment(title: "You're set.",
                                 detail: "We'll help you notice which daily choices support your health most.",
                                 tone: .calm)
        case let .checkInSaved(delta, hadPrior, strength):
            // mirror the existing four-branch logic, deterministically
        // ...
        case .reset:
            return nil
        }
    }
}
```

Store changes (`Sources/App/LifeClockStore.swift`):

```swift
final class LifeClockStore {
    private let supportPresenter = SupportMomentPresenter()
    private(set) var supportMoment: SupportMoment?  // private(set) — closes the dual-write smell from todo 032 #4

    private func emit(_ intent: SupportMomentPresenter.Intent) {
        supportMoment = supportPresenter.moment(for: intent)
    }

    func dismissSupportMoment() { supportMoment = nil }

    // mutations now call:
    //   emit(.onboardingComplete)
    //   emit(.checkInSaved(delta: ..., hadPriorCheckIn: ..., strengthLogged: ...))
    //   emit(.questCompleted(rewardMinutes: quest.rewardEstimateMinutes))
    //   emit(.questUndone)
    //   supportMoment = nil  (only inside reset, via emit(.reset) returning nil)
}
```

New tests (`Tests/SupportMomentPresenterTests.swift`):

```swift
final class SupportMomentPresenterTests: XCTestCase {
    func testCheckInSavedDeltaPositive() { /* assert title + detail */ }
    func testCheckInSavedNoDeltaWithStrength() { /* ... */ }
    func testQuestCompletedTone() { /* assert .celebration */ }
    func testQuestUndoneTone() { /* assert .calm */ }
    func testResetReturnsNil() { /* ... */ }
}
```

Acceptance:
- [ ] No raw `SupportMoment(...)` constructor inside `LifeClockStore` mutations.
- [ ] `supportMoment` is `private(set)`; only `dismissSupportMoment()` and `emit(...)` mutate it.
- [ ] All five intents have a unit test covering the title + detail + tone surface.
- [ ] Existing store tests (`testQuestCompletionAddsLedgerEntry`, etc.) updated to assert against `supportPresenter.moment(for:)` output, not literal copy strings.
- [ ] Behavior preserved: an `XCUITest` run shows identical user-visible copy after the refactor.

##### Phase 2.C — Accessibility identifiers + extended XCUITests (todo 028)

Lands after 2.B so the views are stable. Add identifiers to every interactive control on the listed surfaces; extend XCUITests to actually exercise the form-fill paths through the new identifiers.

Identifier additions (dotted scheme, per repo convention). For `Picker` with menu style (the iOS-26 form default), add `.accessibilityValue(...)` so XCUITest can read the current selection — the menu picker exposes as `app.buttons[id]` whose label is the selected option, so an explicit value is the cleanest assertion handle. For `Slider`, pair the identifier with `.accessibilityValue("\(Int(hours)) hours")`. `Stepper` exposes as `app.steppers[id]` containing two child buttons (index 1 = increment, index 0 = decrement) — set the identifier on the Stepper itself.

```swift
// Sources/Features/Onboarding/OnboardingView.swift
Picker("Biological sex (optional)", selection: $biologicalSex) { ... }
    .accessibilityIdentifier("onboarding.biologicalSex")
    .accessibilityValue(biologicalSex)
Picker("Smoking status", ...).accessibilityIdentifier("onboarding.smokingStatus")
    .accessibilityValue(smokingStatus)
Picker("Alcohol frequency", ...).accessibilityIdentifier("onboarding.alcoholFrequency")
    .accessibilityValue(alcoholFrequency)
Picker("Diet quality baseline", ...).accessibilityIdentifier("onboarding.dietQualityBaseline")
    .accessibilityValue(dietQualityBaseline)
Slider(value: $sleepGoalHours, in: 5.0...10.0, step: 0.5)
    .accessibilityIdentifier("onboarding.sleepGoalHours")
    .accessibilityValue(String(format: "%.1f hours", sleepGoalHours))

// Section parents — IMPORTANT: use .contain, not .combine.
// .combine would swallow child identifiers and make the form unreachable.
VStack { /* baseline controls */ }
    .accessibilityElement(children: .contain)
    .accessibilityIdentifier("onboarding.baseline")

// Sources/Features/QuickLog/QuickLogSheet.swift
Picker("Alcohol", ...).accessibilityIdentifier("quickLog.alcoholLevel")
    .accessibilityValue(alcoholLevel.label)
Picker("Diet", ...).accessibilityIdentifier("quickLog.dietQuality")
    .accessibilityValue(dietQuality.label)
Picker("Stress", ...).accessibilityIdentifier("quickLog.stressLevel")
    .accessibilityValue(stressLevel.label)
Stepper("Strength sets: \(strengthSets)", value: $strengthSets, in: 0...10)
    .accessibilityIdentifier("quickLog.strengthSets")
    .accessibilityValue("\(strengthSets)")

// Sources/Features/Paywall/PaywallSheet.swift
Button(action: dismiss) { Image(systemName: "xmark") }
    .accessibilityIdentifier("paywall.close")
    .accessibilityLabel("Close")
Button("Restore", ...).accessibilityIdentifier("paywall.restore")
// Subscribe intentionally NOT identified — agents must not drive purchase
```

New XCUITest file `UITests/LifeClockOnboardingFormUITests.swift`:

```swift
final class LifeClockOnboardingFormUITests: XCTestCase {
    func testOnboardingFormFillEndToEnd() throws {
        let app = launchApp(scenario: "onboarding")
        // value screen → continue
        XCTAssertTrue(app.otherElements["onboarding.value"].waitForExistence(timeout: 5))
        app.buttons["onboarding.continue"].tap()
        // safety → toggle disclaimer → continue
        app.switches["onboarding.disclaimerToggle"].tap()
        app.buttons["onboarding.continue"].tap()
        // baseline form fill — menu pickers expose as buttons; tap to open, tap option:
        let sexPicker = app.buttons["onboarding.biologicalSex"]
        sexPicker.tap()
        app.buttons["Female"].tap()
        let smokingPicker = app.buttons["onboarding.smokingStatus"]
        smokingPicker.tap()
        app.buttons["Never"].tap()
        // ... alcoholFrequency, dietQualityBaseline same pattern
        // Slider — adjust + assert by value:
        let sleepSlider = app.sliders["onboarding.sleepGoalHours"]
        sleepSlider.adjust(toNormalizedSliderPosition: 0.5)  // 7.5h on 5-10h range
        XCTAssertEqual(sleepSlider.value as? String, "7.5 hours")
        app.buttons["onboarding.continue"].tap()
        // tone → coach → continue
        app.buttons["onboarding.tone.coach"].tap()
        app.buttons["onboarding.continue"].tap()
        // health → connect → continue
        app.buttons["onboarding.connectHealth"].tap()
        app.buttons["onboarding.continue"].tap()
        // reveal → finish
        app.buttons["onboarding.finish"].tap()
        // Today reflects seeded baseline
        XCTAssertTrue(app.otherElements["today.momentum"].waitForExistence(timeout: 5))
    }
}
```

Extend `UITests/LifeClockUITests.swift` with:

```swift
func testPaywallDismissibleByAgent() throws {
    // launch with LIFECLOCK_FORCE_PAYWALL=1 (Phase 1.A env var)
    // assert paywall.close present; tap; assert dismissed
}
```

Acceptance:
- [ ] Every Onboarding form control on the baseline screen has an identifier.
- [ ] Every QuickLog form control has an identifier.
- [ ] Paywall Close + Restore have identifiers; Subscribe does NOT.
- [ ] `LifeClockOnboardingFormUITests` runs green on a clean build.
- [ ] `testPaywallDismissibleByAgent` runs green using the Phase 1.A `LIFECLOCK_FORCE_PAYWALL` fixture.
- [ ] **Verification:** clean Xcode test bundle (delete `~/Library/Developer/Xcode/DerivedData/LifeClock-*`), then run the full test scheme to defend against the stale-bundle issue Codex flagged in the original report.

#### Phase 3: Product call + sweep

##### Phase 3.A — `ToneMode` collapse (todo 029)

**Open question — needs product call.** Three options on the table; recommended default is **Option 1: collapse to two tones** (delete `.mementoMori`, keep `.gentle` + `.coach`). Rationale: 4 of 8 properties are already collapsed; the audit explicitly removed mortality framing; case rename to "Direct" suggests the original concept is being abandoned.

Whichever option ships, the migration concern is the same: `UserProfile.toneMode: String` may hold the legacy `"memento_mori"` rawValue. Every tone read site must fall back to a default if the rawValue doesn't decode.

Pseudocode for `Sources/App/ToneMode.swift` (Option 1 — collapse to two tones):

```swift
enum ToneMode: String, CaseIterable, Identifiable {
    case gentle, coach
    var id: String { rawValue }

    static func fromStored(_ raw: String) -> ToneMode {
        // legacy "memento_mori" maps to .coach
        return ToneMode(rawValue: raw) ?? .coach
    }

    // Keep only properties where tones genuinely differ.
    // Inline literals where all tones agreed (ledgerTitle = "Progress").
}
```

Call-site update (`Sources/App/LifeClockStore.swift` and onboarding tone picker):

```swift
// reading:
self.toneMode = ToneMode.fromStored(profile.toneMode)
// writing:
profile.toneMode = self.toneMode.rawValue
```

`OnboardingView.swift` tone picker drops the `.mementoMori` button.

Acceptance:
- [ ] No `ToneMode` property returns identical strings across all cases (or the property is deleted and inlined).
- [ ] `ToneMode.fromStored("memento_mori")` returns the chosen default without crashing or warning.
- [ ] Onboarding tone picker compiles and reflects the surviving cases.
- [ ] `LifeClockStoreTests.testToneModeChangePropagatesToProfile` updated for the surviving cases.
- [ ] If product chooses Option 2 (restore differentiation) instead, the acceptance criteria pivot — flag at PR time.

##### Phase 3.B — P3 sweep + prevention checks (todo 032)

Code nits:
1. `SupportMoment.Tone` enum 1:1 with icon+color → either keep as `enum` (it's small and named) or replace with `Bool isCelebration`. **Recommended: keep enum**, it's more readable than a Bool. Document the decision and close the todo line.
2. `useInMemoryStore` alias inlined into `isUITest` reads.
3. `momentumCard` extracts a shared `card { ... }` view modifier in `Sources/Shared/CardContainer.swift` (or similar). Refactor `clockCard`, `driversCard`, `questsCard`, `checkInCard` to use it. Verify visual fidelity unchanged.
4. `supportMoment` already `private(set)` after Phase 2.B — close the line.
5. `applyPersistedCompletions(inout:)` no longer exists after Phase 2.A — close the line.
6. Per-row driver identifiers added in `TodayView.swift` (`today.driver.<index>` or `today.driver.<driverType>`).
7. Diet streak chip identifier added (`today.dietStreak`).
8. Grep for legacy `"Completed quest:"` ledger entries:
   ```bash
   # Local dev verification only — no users have this data yet
   grep -r "Completed quest:" products/life-clock-ios/
   ```
   Expected result: zero hits in source. Document the result; if a user migration becomes necessary later, file a new todo.

Prevention checks:
9. Audit `Sources/Models/LifeClockSchema.swift` for any non-optional `@Model` properties without property-level defaults. The schema header (`:11-13`) declares the invariant; verify every model still complies after Phase 2.A's `Quest.slug` addition.
10. `TARGETED_DEVICE_FAMILY` propagation. **Correction from initial plan**: `project.yml:34` already declares `TARGETED_DEVICE_FAMILY: "1,2"` (universal) on the app target. The actual bug is that the test targets (`LifeClockTests`, `LifeClockUITests`) do not carry the setting — which is exactly the failure mode in the cited learning (catchbook iPad regression hidden by missing test-target propagation). The fix is to add explicit declarations to the test targets so iPad-destination test runs catch layout regressions:

    ```yaml
    # products/life-clock-ios/project.yml — add to LifeClockTests and LifeClockUITests:
    settings:
      base:
        TARGETED_DEVICE_FAMILY: "1,2"
    ```

    **Q4 default updated**: keep universal, add explicit declarations to test targets. Narrowing to iPhone-only is a separate product call — out of scope for this plan.

Acceptance:
- [ ] Items 1-7 either applied or explicitly closed with rationale in the PR description.
- [ ] Item 8 grep run; result recorded in PR body.
- [ ] Item 9 audit run; any violations fixed (expected: zero, since Phase 2.A was held to the same standard).
- [ ] Item 10 product call resolved; `project.yml` declares `TARGETED_DEVICE_FAMILY` explicitly.

## System-Wide Impact

### Interaction Graph

When a user completes a planned action on Today:

1. `TodayView.questsCard` button tap → `LifeClockStore.toggleQuestCompletion(_:)`
2. Store mutates `quest.completedAt`, calls `upsertQuest(_:)` (post-Phase-2.A — was `persistedQuestRecord`).
3. `upsertQuest` resolves the persisted Quest by slug, copies `completedAt`, inserts a `TimeLedgerEntry`.
4. Store calls `emit(.questCompleted(rewardMinutes:))` (post-Phase-2.B — was inline `SupportMoment(...)`).
5. `SupportMomentPresenter.moment(for:)` returns a `SupportMoment`; store assigns to `supportMoment`.
6. SwiftUI re-renders `TodayView`; `supportMomentCard(_:)` displays.
7. `try? modelContext.save()` persists across relaunch.

Relaunch path:

1. App init → `LifeClockApp.init` → `LifeClockStore(...)` → `bootstrap()`
2. `bootstrap()` reads `UserProfile`, calls `refreshFromHealthKit()`.
3. `refreshFromHealthKit` calls `QuestEngine.generateDailyQuests(...)` → emits new `Quest` instances with stable slugs.
4. Store calls `applyPersistedCompletions(to:for:)` (post-Phase-2.A: integrated into `upsertQuest` — fetches existing quests by `(date, slug)`, copies `completedAt` onto the new instances).
5. Today renders with completion state intact.

### Error & Failure Propagation

**SwiftData migration failure (Phase 2.A risk).** If `Quest.slug: String = ""` is declared without the property-level default, lightweight migration fails with `NSCocoaErrorDomain 134110`; `ModelContainer` init throws; `LifeClockApp.init` calls `fatalError("ModelContainer init failed: \(error)")`. Mitigation: the schema header invariant (`:11-13`) is enforced; CI runs `LifeClockE2ETests` which exercise a freshly-seeded container.

**Stored rawValue decode failure (Phase 3.A risk).** `UserProfile.toneMode = "memento_mori"` after the case is removed. If read via `ToneMode(rawValue: profile.toneMode)`, returns nil; current code at `LifeClockStore.swift:163` falls back to `.coach`, which is safe. Phase 3.A formalizes this as `ToneMode.fromStored(_:)`.

**XCUITest stale bundle (Phase 2.C risk).** `xcodebuild test-without-building` against a stale bundle silently runs old assertions. Mitigation: clean `DerivedData/LifeClock-*` before each Phase 2.C run; CI runs full `xcodebuild test`, never `test-without-building`.

**Skill registry test regression (Phase 1.B risk).** Path relocation could leave a dangling `project_skill` or stale `path:` reference. Mitigation: `test_skill_reconciliation.py`, `test_skill_stocktake_skill.py`, and `registry_drift.run()` all run after the change; any new drift item fails the phase.

### State Lifecycle Risks

**Quest persistence during the `(title) → (slug)` transition (Phase 2.A).** Pre-existing simulator data has `Quest` rows without `slug` (lightweight migration backfills them to `""`). The first post-migration refresh emits new quests with non-empty slugs; existing rows are orphaned forever (no slug match). Mitigation: this is acceptable — there are no production users; pre-launch simulator-only data is disposable. Document as expected. Add a one-line note in the migration plan stub at `LifeClockSchema.swift:199-208` for future reference.

**Ledger entries from old format (todo 032 #8).** Pre-rename `"Completed quest:"` ledger entries persist if any exist; undo logic only matches `"Completed action:"`. Mitigation: grep verifies none exist (Phase 3.B). If found, file a follow-up todo — out of scope here.

**Skill canonical relocation (Phase 1.B).** Git move (`git mv`) preserves history. The old path must be deleted in the same commit as the new path's creation; otherwise `orphan_canonical` drift fires.

### API Surface Parity

**Skill discovery surfaces** that reference the canonical path:
- `skills/registry.yaml` — `path:` field.
- `.claude/skills/ios-simulator-ux-audit.md` — `canonical_source` frontmatter.
- `skills/adapters/claude/ios-simulator-ux-audit.md` — `canonical_source` frontmatter.
- `CLAUDE.md` — trigger phrase points to the *adapter*, not canonical, so unchanged.
- `skills/canonical/ios-simulator-ux-audit/fixtures/happy_path.yaml` — `input.skill_file` field references the canonical relative path.

All four (excluding CLAUDE.md) update atomically in Phase 1.B.

**iOS launch-fixture surfaces** that consume `LifeClockLaunchConfiguration`:
- `LifeClockApp.init` — already passes `launchConfiguration.makeHealthService()` and `launchConfiguration.clock`.
- `LifeClockApp.body` — calls `launchConfiguration.seedInitialStateIfNeeded(in:)`.
- New env vars must thread through these existing call sites; no new entry points needed.

### Integration Test Scenarios

Five cross-layer scenarios that unit tests with mocks would never catch:

1. **Slug stability across copy edits.** Complete a Quest with slug `nutrition.water-with-meal.v1` and title `"Drink water"`. In a second run, `QuestEngine` emits the same slug with title `"Add a glass of water with meals"`. After bootstrap, the regenerated Quest still shows `completedAt` set and the ledger has the original `"Completed action: Drink water"` entry (frozen at completion time).

2. **Cold-restart with paywall fixture.** Launch with `LIFECLOCK_FORCE_PAYWALL=1`. Paywall sheet appears immediately; `paywall.close` button is reachable; tapping it dismisses; Today renders below.

3. **Health-denied path.** Launch with `LIFECLOCK_HEALTH_AUTH=denied`. Onboarding's permission education screen shows the appropriate copy; pressing the button does not crash (the mock returns the configured state); user can proceed via "skip" path.

4. **Onboarding form fill fully agent-driven.** XCUITest taps every form control via accessibility identifier (no label-string fallback). Today reflects the seeded baseline (`sleepGoalHours`, `dietQualityBaseline`, etc.).

5. **Skill graduation reconciles cleanly.** After Phase 1.B, `python -m pytest tests/python/unit/test_skill_reconciliation.py tests/python/unit/test_skill_stocktake_skill.py tests/python/integration/test_skill_stocktake_on_live_registry.py tests/python/unit/test_ios_simulator_ux_audit_fixtures.py` — all green. `registry_drift.run()` reports no NEW drift items (pre-existing `post-run-validation` orphan still appears, unrelated).

## Acceptance Criteria

### Functional Requirements

#### Phase 1
- [ ] `LIFECLOCK_FORCE_PAYWALL`, `LIFECLOCK_HEALTH_AUTH`, `LIFECLOCK_SEED_STREAK`, `LIFECLOCK_SEED_QUESTS_COMPLETED`, `LIFECLOCK_FIXED_DATE` parsed and exposed.
- [ ] `MockHealthKitService` honors `denied`/`notDetermined`.
- [ ] `ios-simulator-ux-audit` canonical relocated; 8 spec gaps closed; contract-freeze fixture passes; `stage: active`.

#### Phase 2
- [ ] `Quest.slug: String = ""` shipped with property-level default.
- [ ] Persistence collapses to single upsert; LOC delta in `LifeClockStore.swift` is at least −50 net.
- [ ] `SupportMomentPresenter` exists; no raw `SupportMoment(...)` constructor in `LifeClockStore` mutations.
- [ ] All onboarding form, QuickLog form, and Paywall Close/Restore have accessibility identifiers.
- [ ] `LifeClockOnboardingFormUITests` and the paywall-dismiss XCUITest are green on a clean build.

#### Phase 3
- [ ] `ToneMode` decision shipped (default: collapse to two tones); legacy rawValue gracefully decodes.
- [ ] All P3 nits resolved or explicitly closed.
- [ ] `TARGETED_DEVICE_FAMILY` declared explicitly in `project.yml`.

### Non-Functional Requirements

- [ ] No new external dependencies.
- [ ] No new permissions or capabilities required.
- [ ] All copy strings in `SupportMomentPresenter` match the existing user-visible copy byte-for-byte.
- [ ] Plan-completion XCUITest still passes after Phase 2 (regression check on the existing test).

### Quality Gates

- [ ] All Python skill tests (4 files) green.
- [ ] All Swift unit tests (`LifeClockTests` target) green.
- [ ] All XCUITests (`LifeClockUITests` target) green on a clean build.
- [ ] Live `registry_drift.run()` reports no new drift items.
- [ ] PR description documents:
  - which `ToneMode` option was chosen and why
  - which `TARGETED_DEVICE_FAMILY` value was chosen and why
  - result of the `"Completed quest:"` grep

## Testing requirements

### Unit tests (new)
- `Tests/SupportMomentPresenterTests.swift` — five intent cases.
- Extend `Tests/LifeClockStoreTests.swift` — `testQuestCompletionSurvivesTitleRename`.
- Extend `Tests/LifeClockStoreTests.swift` — `testToneModeFromStoredLegacyValueFallsBack` (Phase 3.A).

### XCUITests (new + extended)
- New: `UITests/LifeClockOnboardingFormUITests.swift::testOnboardingFormFillEndToEnd`.
- Extend `UITests/LifeClockUITests.swift::testPaywallDismissibleByAgent`.

### Python tests (new)
- `tests/python/unit/test_ios_simulator_ux_audit_fixtures.py` (mirrors `test_ios_ui_polish_review_fixtures.py`).

### Manual verification
- Phase 2.A: install on simulator with pre-existing Quest data; verify no crash; verify completion state persists across relaunch.
- Phase 2.C: clean `DerivedData/LifeClock-*`; run full test scheme.
- Phase 3.B: visually compare Today screen before/after `card { }` extraction.

## Dependencies & Risks

### Dependencies
- Phase 2.C depends on Phase 1.A (uses `LIFECLOCK_FORCE_PAYWALL` for the paywall-dismiss test).
- Phase 2.B depends on Phase 2.A (settles `LifeClockStore` mutation surface before extracting presenter).
- Phase 3.A and 3.B depend on Phase 2 (touch the same files).

### Risks
1. **SwiftData migration on existing simulator data (Phase 2.A).** Mitigation: property-level default; manual verification step in test plan; schema header invariant enforced.
2. **Stale Xcode test bundles hiding wrong assertions (Phase 2.C).** Mitigation: clean DerivedData step explicit in acceptance.
3. **Path relocation breaking skill discovery (Phase 1.B).** Mitigation: atomic commit; reconciliation tests run as gate.
4. **`ToneMode.mementoMori` stored values in user data (Phase 3.A).** Mitigation: `fromStored(_:)` fallback; verify with manual test.
5. **Behavior drift in presenter extraction (Phase 2.B).** Mitigation: byte-for-byte copy match in unit tests; XCUITest re-runs to verify user-visible behavior unchanged.
6. **Scope creep in Phase 3.B `card { }` extraction.** Mitigation: explicit scope — only `clockCard`, `driversCard`, `questsCard`, `checkInCard`, `momentumCard`. Other card-like views are out of scope.

### Open questions (need product/operator decisions)

- **Q1 (Phase 3.A).** Delete `.mementoMori` (Option 1, recommended), restore differentiation (Option 2), or collapse to two tones with a different name (Option 3)?
- **Q2 (Phase 1.B).** Graduate to `stage: active` as part of this plan? Recommended yes — the contract-freeze fixture is the load-bearing addition.
- **Q3 (Phase 1.B).** Relocate canonical to `skills/canonical/ios-simulator-ux-audit/skill.md`? Recommended yes — the skill is generic; the product-coupled path is misleading.
- **Q4 (Phase 3.B).** ~~`TARGETED_DEVICE_FAMILY = "1"` vs `"1,2"`?~~ **Corrected after deepen pass**: app target already declares `"1,2"`. Decision is reduced to "add the setting to the test targets too." Default: yes — propagate to `LifeClockTests` and `LifeClockUITests`. Narrowing to iPhone-only is a separate, future product call.

## Sources & References

### Internal references

#### Source todos (read as primary input)
- [todos/026-pending-p1-life-clock-quest-persistence-fragile-key.md](../../todos/026-pending-p1-life-clock-quest-persistence-fragile-key.md)
- [todos/027-pending-p1-life-clock-store-presentation-leak.md](../../todos/027-pending-p1-life-clock-store-presentation-leak.md)
- [todos/028-pending-p1-life-clock-a11y-id-gaps-block-agent-flows.md](../../todos/028-pending-p1-life-clock-a11y-id-gaps-block-agent-flows.md)
- [todos/029-pending-p2-life-clock-tonemode-collapsed-differentiation.md](../../todos/029-pending-p2-life-clock-tonemode-collapsed-differentiation.md)
- [todos/030-pending-p2-ios-simulator-ux-audit-spec-gaps.md](../../todos/030-pending-p2-ios-simulator-ux-audit-spec-gaps.md)
- [todos/031-pending-p2-life-clock-launch-config-scenario-coverage.md](../../todos/031-pending-p2-life-clock-launch-config-scenario-coverage.md)
- [todos/032-pending-p3-life-clock-review-misc.md](../../todos/032-pending-p3-life-clock-review-misc.md)

#### Source files
- `products/life-clock-ios/Sources/Models/LifeClockSchema.swift:11-13` (schema-wide property-default invariant)
- `products/life-clock-ios/Sources/Models/LifeClockSchema.swift:142-170` (Quest model)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:172,217,229,276,282,288,294,313` (SupportMoment construction sites)
- `products/life-clock-ios/Sources/App/LifeClockStore.swift:353-426` (persisted-quest quartet)
- `products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift:7-10,26` (Scenario enum, fixed clock)
- `products/life-clock-ios/Sources/App/ToneMode.swift` (collapsed differentiation across cases)
- `products/life-clock-ios/Sources/Features/Onboarding/OnboardingView.swift:98-133` (a11y id gaps)
- `products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift:23,35,48,~60` (a11y id gaps)
- `products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift:33,36,80,116` (a11y id gaps)
- `products/life-clock-ios/UITests/LifeClockUITests.swift:73-79` (`launchApp(scenario:)` precedent)
- `products/life-clock-ios/project.yml:65-78` (UI test target)
- `skills/canonical/products/life-clock/ios-simulator-ux-audit.md` (relocate)
- `skills/registry.yaml:130-148` (`ios-simulator-ux-audit` entry)
- `skills/canonical/products/catchbook/fixtures/ios-ui-polish-review/happy_path.yaml` (contract-freeze fixture pattern)
- `tests/python/unit/test_ios_ui_polish_review_fixtures.py` (per-skill fixture test pattern)

### Past learnings to apply
- [docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md](../solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md) — non-negotiable: `Quest.slug` ships with property-level default.
- [docs/solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md](../solutions/integration-issues/swiftdata-deleting-model-from-child-sheet.md) — applies if QuickLog refactor introduces deletion paths (currently does not).
- [docs/solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md](../solutions/integration-issues/ios-ipad-compatibility-mode-cramped-layout.md) — direct fix for Phase 3.B item 10.
- [docs/solutions/test-failures/pre-existing-failures-are-often-test-bugs.md](../solutions/test-failures/pre-existing-failures-are-often-test-bugs.md) — clean-DerivedData step before Phase 2.C verification.
- [docs/solutions/architecture/skill-estate-adapter-mirror-and-batch-todo-resolution.md](../solutions/architecture/skill-estate-adapter-mirror-and-batch-todo-resolution.md) — adapter stays thin; Phase 1.B preserves the recently-trimmed adapter.
- [docs/solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md](../solutions/integration-issues/incomplete-refactor-auto-detection-behind-empty-state-gate.md) — when Phase 2.B extracts the presenter, ensure no old conditional gates short-circuit the new path.
- [docs/solutions/integration-issues/waterbody-optional-refactor.md](../solutions/integration-issues/waterbody-optional-refactor.md) — analog for Phase 3.A's enum-case removal pattern.

### External references
- None required. Codebase has strong patterns; standard SwiftUI / SwiftData / xcodegen / pytest mechanics.

### Related work
- 2026-04-30 multi-agent review (this session) — original source of all seven todos.
- Two inline fixes from the review already shipped (slim adapter, drop `codex` from `target_runtimes`).
- Past plan precedents: [2026-04-29-001-feat-life-clock-palette-picker-plan.md](2026-04-29-001-feat-life-clock-palette-picker-plan.md), [2026-04-27-002-feat-life-clock-ios-mvp-skeleton-plan.md](2026-04-27-002-feat-life-clock-ios-mvp-skeleton-plan.md).

## Appendix: LFG step 8 — recording + PR attachment recipe

This section is implementation guidance for the LFG pipeline's `/feature-video` step. It is not part of the iOS or skill changes scoped above.

### Marketing-quality simulator recording

```bash
#!/usr/bin/env bash
set -euo pipefail
DEVICE="booted"
OUT="$HOME/Desktop/lifeclock-walkthrough.mov"

# Normalize status bar (9:41, full battery, full signal)
xcrun simctl status_bar "$DEVICE" override \
  --time "9:41" --dataNetwork wifi \
  --wifiMode active --wifiBars 3 \
  --cellularMode active --cellularBars 4 \
  --batteryState charged --batteryLevel 100

# Record h264 (web-compatible) with notch mask
xcrun simctl io "$DEVICE" recordVideo --codec=h264 --mask=black --force "$OUT" &
REC_PID=$!
echo "Demo Today momentum + plan completion + paywall dismissal. Press Enter to stop."
read -r
kill -INT "$REC_PID"           # SIGINT only — SIGTERM/SIGKILL produce unplayable files
wait "$REC_PID" 2>/dev/null || true
xcrun simctl status_bar "$DEVICE" clear
```

### Size-managed conversion (>10 MB triggers GIF fallback)

```bash
SIZE=$(stat -f%z "$OUT")
if [ "$SIZE" -gt 10485760 ]; then
  PAL="/tmp/palette.png"
  ffmpeg -y -i "$OUT" -vf "fps=15,scale=480:-1:flags=lanczos,palettegen" "$PAL"
  ffmpeg -y -i "$OUT" -i "$PAL" \
    -lavfi "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse" \
    "${OUT%.mov}.gif"
fi
```

### PR attachment — known limit

`gh pr edit --body-file` does **not** upload media. The only paths to inline `<video>` rendering in a PR description are:

1. **Web-UI drag-drop.** Open the PR in a browser, drag the `.mov`/`.gif` into the description editor, copy the resulting `https://github.com/user-attachments/assets/<uuid>` URL, paste into a body file, then `gh pr edit <PR> --body-file pr-body.md`. This is the canonical approach.
2. **Release asset.** `gh release upload` gives a stable URL but loses inline playback.
3. **Computer-use automation.** Drive a browser to perform step 1 programmatically.

For the LFG pipeline, document the manual web-UI step in the PR body or use computer-use to automate it. Step 8's `/feature-video` slash command needs to know about this limit — without it, the pipeline's "video in PR" promise fails silently with a text-only PR description.
