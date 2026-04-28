---
title: Life Clock — SwiftData Persistence
type: feat
status: active
date: 2026-04-28
origin: docs/products/life-clock/MVP_VS_FOUNDER_PACK_AUDIT_2026-04-28.md
---

# Life Clock — SwiftData Persistence

## Overview

Re-introduce `@Model` on the seven core types, wrap in `LifeClockSchemaV1: VersionedSchema`, wire a `ModelContainer` (CloudKit explicitly disabled), and route mutations through `ModelContext`. Cold-start persists across launches: `UserProfile`, `HabitLog`, `Quest` completion, `TimeLedgerEntry`. `DailyHealthSnapshot` and `LifeClockEstimate` remain recomputed on each refresh from HealthKit (they're cheap and HealthKit is the source of truth).

This unblocks: cold-start state survival, "return tomorrow" loop closure, prior-week comparisons in Weekly Report, real "Delete data" button, real baseline editing.

## Scope

**In:**
- `LifeClockSchemaV1: VersionedSchema` + `LifeClockMigrationPlan: SchemaMigrationPlan` (empty stages — V1 only).
- All 7 model types annotated `@Model`. Property-level defaults preserved (past learning).
- `ModelContainer` constructed in `LifeClockApp.init` with `cloudKitDatabase: .none`.
- `LifeClockStore` accepts a `ModelContext` and mediates all persistence.
- `RootView` branches on a `@Query` for `UserProfile` — onboard if empty, restore if present.
- `Profile → Delete data` becomes real (deletes all model rows + resets onboarding).
- Tests use `ModelConfiguration(isStoredInMemoryOnly: true)` for isolation.

**Out (deferred):**
- `DailyHealthSnapshot` persistence — HealthKit is the source of truth; recompute on refresh is fine for v1. Persisting becomes a perf optimization later.
- Background refresh / `HKObserverQuery` — separate plan.
- Cross-device sync. Forbidden by HealthKit policy; reinforced by `cloudKitDatabase: .none`.
- Schema V2 migration. Empty stages for now; framework is in place.

## Technical approach

### Schema

```
Sources/Models/LifeClockSchema.swift  (rewritten)
├── enum LifeClockSchemaV1: VersionedSchema
│   ├── @Model UserProfile
│   ├── @Model HabitLog
│   ├── @Model Quest
│   ├── @Model TimeLedgerEntry
│   ├── @Model LifeClockEstimate (persisted but recomputed on refresh)
│   ├── @Model WeeklyReport (persisted but recomputed)
│   └── @Model DailyHealthSnapshot (kept @Model for future cache; not actively persisted in v1)
└── enum LifeClockMigrationPlan: SchemaMigrationPlan { stages = [] }
```

Property-level defaults preserved on every non-optional field per the prior learning (`docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`).

`@Attribute(.unique)` on `id: UUID` for types with one. `HabitLog.date`, `DailyHealthSnapshot.date`, `LifeClockEstimate.date`, `WeeklyReport.weekStart` get `@Attribute(.unique)` so we can upsert by day.

### Container construction

```swift
struct LifeClockContainer {
    static func make(inMemory: Bool = false) throws -> ModelContainer {
        let schema = Schema(versionedSchema: LifeClockSchemaV1.self)
        let config = ModelConfiguration(
            "LifeClock",
            schema: schema,
            isStoredInMemoryOnly: inMemory,
            allowsSave: true,
            cloudKitDatabase: .none   // HealthKit-derived data must not iCloud-sync
        )
        return try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
    }
}
```

### App wiring

```swift
@main @MainActor
struct LifeClockApp: App {
    let container: ModelContainer
    @State private var store: LifeClockStore

    init() {
        do {
            container = try LifeClockContainer.make()
        } catch {
            fatalError("ModelContainer init failed: \(error)")
        }
        let context = container.mainContext
        _store = State(wrappedValue: LifeClockStore(
            healthService: HealthKitConfiguration.service(),
            modelContext: context
        ))
    }

    var body: some Scene {
        WindowGroup { RootView() }
            .modelContainer(container)
            .environment(store)
            .task { await store.bootstrap() }
    }
}
```

### Store changes

`LifeClockStore` gains a `ModelContext`. Mutations route through the context:

- `completeOnboarding(profile:tone:)` → `context.insert(profile)` then `try? context.save()`.
- `setTodayHabits(_:)` → upsert on `HabitLog.date == today`, then save.
- `toggleQuestCompletion(_:)` → mutate then save.
- `resetForOnboarding()` → fetch all rows, delete each, save.
- `bootstrap()` → if `profile` exists in context, restore from it; else seed sample then call `refreshFromHealthKit()`.

### RootView change

`@Query` for `UserProfile` decides the gate, replacing `store.hasCompletedOnboarding`:

```swift
struct RootView: View {
    @Query private var profiles: [UserProfile]
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        if profiles.isEmpty {
            OnboardingView()
        } else {
            MainTabView()
        }
    }
}
```

The `hasCompletedOnboarding` field on the store stays for now as a transient UI flag, but the *truth* is now persisted.

### Profile → Delete data

```swift
func deleteAllData() async {
    do {
        try context.delete(model: UserProfile.self)
        try context.delete(model: HabitLog.self)
        try context.delete(model: Quest.self)
        try context.delete(model: TimeLedgerEntry.self)
        try context.delete(model: LifeClockEstimate.self)
        try context.delete(model: WeeklyReport.self)
        try context.save()
        // Also clear in-memory store
        resetForOnboarding()
    } catch { ... }
}
```

## Acceptance criteria

- [ ] All 7 types are `@Model` again, inside `LifeClockSchemaV1`.
- [ ] All non-optional stored properties keep their property-level defaults.
- [ ] `ModelContainer` constructed with `cloudKitDatabase: .none`.
- [ ] `LifeClockApp.init` builds the container once, fatal-errors on failure.
- [ ] `LifeClockStore` accepts a `ModelContext` and saves on every mutation.
- [ ] `RootView` branches on `@Query<UserProfile>` count — onboard if empty.
- [ ] Cold start after onboarding skips onboarding and restores `UserProfile`.
- [ ] `Delete data` button actually wipes the store and returns the user to onboarding.
- [ ] Tests use `LifeClockContainer.make(inMemory: true)`.
- [ ] CI grep gates remain clean.

## Risks

- **Migration trap on edits:** with `VersionedSchema` shipped, any future edit to a `@Model` field needs a `MigrationStage`. Empty `stages` is fine for V1; V2 must add one.
- **`ModelContext` is not `Sendable`:** the store stays `@MainActor`, no off-actor work. HealthKit live service writes nothing, so no contention.
- **Schema differs from prior commit:** tests that built `UserProfile()` directly still work (initializers retained), but any test reading `let p = UserProfile()` outside a context now creates a transient unmanaged instance — fine, deliberate.
- **Cold-start race:** `@Query` returns empty during first render tick. The seed-or-restore decision happens after the next render. Acceptable flicker; OnboardingView is the safe default.
