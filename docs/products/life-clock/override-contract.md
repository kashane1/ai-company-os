# Override Contract Spec — Life Clock

> **Status:** Canonical product policy. The override surface (`OverrideService` + `OverrideSheet` + `DailyHealthSnapshot.overridesData` / `originalHealthKitValuesData`) is the Pro correction-power feature — Pro Annual unlock #3 in [`MONETIZATION.md`](MONETIZATION.md). This spec defines the data-shape contract + the atomicity guarantee + the entitlement-grace behavior.
>
> Implementation: [`Sources/Services/OverrideService.swift`](../../../products/life-clock-ios/Sources/Services/OverrideService.swift) + `Sources/Features/History/OverrideSheet.swift` + `LifeClockSchema.swift` (`DailyHealthSnapshot.overridesData` / `originalHealthKitValuesData`).

## One-line rule

**Apply an override = atomic write that captures the original HealthKit value once, validates the new value, persists in a single SwiftData save, and rolls back cleanly on failure. Pro-gated for new writes; existing overrides survive downgrade.**

## Data shape (binding — match `SnapshotOverrideMap`)

`DailyHealthSnapshot` carries two related fields:

- **`overridesData`** — encoded `SnapshotOverrideMap` (field → user-corrected value).
- **`originalHealthKitValuesData`** — encoded `SnapshotOverrideMap` (field → raw HK value at first override).

`SnapshotOverrideMap.Field` enumerates the override-able fields (currently a subset of `DailyHealthSnapshot`'s numeric quantities). The two maps are independently encoded so the original-value capture can survive subsequent HK refreshes without contamination.

## Write-once-per-field invariant

The first time the user overrides a field, `OverrideService` captures the current HK value into `originalHealthKitValuesData`. **Subsequent overrides of the same field do NOT update the original capture** — even if HealthKit later returns a different value for that day.

Why: if the user reverts an override, the engine restores the *true original* HK value the user saw when they decided to override — not a refreshed-since value. Refreshed values mid-grace would silently change the user's "I'm correcting what HK saw" mental model.

## Atomicity contract (binding)

`OverrideService.applyOverride(field:value:on:recomputedAt:)`:

1. Validate `value` against `field`-specific bounds. Reject `.invalidValue` if out of range.
2. Locate the snapshot for `dayStart`. Reject `.snapshotMissing` if absent.
3. Decode current `overridesData` + `originalHealthKitValuesData`.
4. If this field is not yet captured in `originalHealthKitValuesData`, capture the raw value.
5. Set / update the user-corrected value in `overridesData`.
6. Re-encode both maps.
7. Single `try modelContext.save()` — rolls back the entire transaction on throw.
8. Update `lastRecomputedAt` on the snapshot.

If steps 1–6 succeed but step 7 throws, the snapshot is left unchanged (SwiftData save semantics). If any step throws before save, no mutation has happened. The user sees an error, not a partially-applied state.

## Pro-entitlement gate (binding)

`OverrideService.applyOverride` is **not** the gate. The gate lives one layer up:

- `LifeClockStore.applyOverride(...)` + `LifeClockStore.revertOverride(...)` check `subscriptions.isPro` first. If not Pro, throw `.notEntitled` and **do not delegate to the service**. The snapshot is never touched in the not-entitled path.
- `EntitlementGatedWritesTests` pins `.notEntitled` on both `applyOverride` and `revertOverride` (and a third write — `selectPlanQuest`). This is a regression guard.

### Grace period — existing overrides survive demote

When a user downgrades from Pro to Free (refund, expiry, post-cancel grace ends), existing overrides remain in `overridesData` and continue to affect the engine's effective-value computation. **What's blocked is new writes / new reverts.** This is a deliberate trust decision:

- Erasing prior overrides on demote would discard *user-authored corrections* — a data-loss anti-pattern.
- The Free user can still see the corrected value; they just can't edit further.
- If the user re-upgrades, override-write capability resumes without data migration.

This contract is documented in [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md) § Post-expiry demoted + § Refunded.

## Read-side: `OverrideAwareSnapshot`

The engine reads the effective-value projection through an override-aware adapter rather than touching `overridesData` directly. The adapter:

- Returns the user-corrected value when one is set.
- Returns the raw HK value otherwise.
- Exposes `.isOverridden(field:)` for UI use (the "Adjusted" chip in History day-detail).

`ClockEngine.calculateDailyDelta` consumes the adapter, not the raw snapshot — overrides are transparent to the engine math.

## Anti-patterns (binding refusals)

- **Do not mutate the snapshot outside `OverrideService`.** `LifeClockStore` delegates; no other call site writes to `overridesData` or `originalHealthKitValuesData`.
- **Do not capture HK value on every write.** Write-once-per-field. Re-capturing breaks revert semantics.
- **Do not skip the validation step.** Bounds vary per field; an out-of-bounds value would feed garbage into the engine.
- **Do not erase overrides on demote.** Grace + trust. See above.
- **Do not surface the override UI on Today** — corrections are a retrospective surface and belong in History day-detail. Today is the daily-loop surface.
- **Do not implement a "revert all overrides" affordance.** Per-field revert only. Bulk revert is a footgun.

## Cross-references

- Implementation: [`Sources/Services/OverrideService.swift`](../../../products/life-clock-ios/Sources/Services/OverrideService.swift)
- Read-side adapter: `Sources/Models/OverrideAwareSnapshot.swift`
- UI: `Sources/Features/History/OverrideSheet.swift` + `DayDetailView.swift`
- Tests: `Tests/EntitlementGatedWritesTests.swift` (gate), `Tests/OverrideServiceTests.swift` (atomicity + write-once)
- Pro entitlement gate copy: [`ToneMode.swift`](../../../products/life-clock-ios/Sources/App/ToneMode.swift) (the `.notEntitled` downgrade notice line)
- Free/Pro rule: [`MONETIZATION.md`](MONETIZATION.md) § Free vs Pro Rule (correction power)
- Lifecycle states: [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md)
- Schema: [`Sources/Models/LifeClockSchema.swift`](../../../products/life-clock-ios/Sources/Models/LifeClockSchema.swift) (`DailyHealthSnapshot.overridesData`, `originalHealthKitValuesData`)

## Validation

The override surface is on-spec when ALL of the following hold:

1. `EntitlementGatedWritesTests` pins `.notEntitled` on `applyOverride` and `revertOverride`.
2. `applyOverride` is atomic (single save, rollback on throw).
3. Write-once-per-field: `originalHealthKitValuesData` updates only on first override of each field.
4. Existing overrides survive Pro → Free demote; new writes / reverts are blocked.
5. The engine reads through `OverrideAwareSnapshot`, never directly from `overridesData`.
6. The "Adjusted" chip surfaces on History day-detail rows where `isOverridden` is true.
