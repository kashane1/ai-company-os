import Foundation

/// View-side accessors for `DailyHealthSnapshot` overrides. Centralizes the
/// "live HK value vs override" projection so view code never has to remember
/// to consult both.
extension DailyHealthSnapshot {
    var overrideMap: SnapshotOverrideMap {
        SnapshotOverrideMap.decode(from: overridesData)
    }

    var originalHealthKitMap: SnapshotOverrideMap {
        SnapshotOverrideMap.decode(from: originalHealthKitValuesData)
    }

    /// True iff at least one field has been overridden.
    var hasOverrides: Bool {
        !overrideMap.isEmpty
    }

    /// Raw HK value for a field (ignores overrides). Returns nil when HK
    /// never delivered a value. Delegated to the field's `Spec.rawGetter`
    /// — keeps "where do I read each field" in one place.
    func rawValue(for field: SnapshotOverrideMap.Field) -> Double? {
        field.spec.rawGetter(self)
    }

    /// Effective value for a field — override if present, else raw HK value.
    /// View code should always read through this rather than touching
    /// `stepCount` etc. directly when an override may apply.
    func effectiveValue(for field: SnapshotOverrideMap.Field) -> Double? {
        if let override = overrideMap.value(for: field) {
            return override
        }
        return rawValue(for: field)
    }

    /// True iff this specific field is currently overridden. Drives the
    /// "Adjusted" affordance in `DayDetailView`.
    func isOverridden(_ field: SnapshotOverrideMap.Field) -> Bool {
        overrideMap.value(for: field) != nil
    }

    /// Original HK value captured at the moment the override was first
    /// written. Used by Revert to restore. nil when no override exists.
    func originalHealthKitValue(for field: SnapshotOverrideMap.Field) -> Double? {
        originalHealthKitMap.value(for: field)
    }
}
