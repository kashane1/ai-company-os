import Foundation
import SwiftData

/// Atomic write path for HealthKit-derived value corrections. Pro-only;
/// the engine ignores overrides while `!isPro` (engine-level gate handled
/// at the read site by callers passing the override-aware snapshot through
/// `OverrideAwareSnapshot.proAdjusted` or by re-running the daily delta
/// against the effective-value projection).
///
/// Atomicity contract: a failure during write leaves the store unchanged.
/// We mutate only after the (potentially throwing) encode steps succeed,
/// then save in a single `try modelContext.save()` and rollback on throw.
@MainActor
struct OverrideService {
    enum OverrideError: Error, Equatable {
        case invalidValue
        case persistenceFailed
        case snapshotMissing
    }

    let modelContext: ModelContext

    /// Apply or update an override for `field` on the snapshot at `dayStart`.
    ///
    /// - Captures the raw HK value into `originalHealthKitValuesData` if not
    ///   already captured (write-once-per-field — never overwrite when HK
    ///   later returns updated data, so revert always restores the truly
    ///   original value).
    /// - Validates `value` against `field`-specific bounds.
    /// - Saves once; rolls back on save failure.
    func applyOverride(
        field: SnapshotOverrideMap.Field,
        value: Double,
        on dayStart: Date,
        recomputedAt: Date
    ) throws {
        guard isValid(value, for: field) else { throw OverrideError.invalidValue }
        guard let snapshot = fetchSnapshot(for: dayStart) else {
            throw OverrideError.snapshotMissing
        }

        var overrides = snapshot.overrideMap
        var originals = snapshot.originalHealthKitMap

        // Write-once-per-field: capture the raw HK value the first time we
        // override this field, never on subsequent edits.
        if originals.value(for: field) == nil,
           let raw = snapshot.rawValue(for: field) {
            originals.set(raw, for: field)
        }
        overrides.set(value, for: field)

        let encodedOverrides = overrides.encode()
        let encodedOriginals = originals.encode()

        snapshot.overridesData = encodedOverrides
        snapshot.originalHealthKitValuesData = encodedOriginals
        snapshot.lastRecomputedAt = recomputedAt

        do {
            try modelContext.save()
        } catch {
            modelContext.rollback()
            throw OverrideError.persistenceFailed
        }
    }

    /// Remove an override and restore the snapshot's raw field to the
    /// captured original HK value. If no original was captured (defensive
    /// path — should not happen if `applyOverride` was used correctly),
    /// the raw field is left untouched.
    func revertOverride(
        field: SnapshotOverrideMap.Field,
        on dayStart: Date,
        recomputedAt: Date
    ) throws {
        guard let snapshot = fetchSnapshot(for: dayStart) else {
            throw OverrideError.snapshotMissing
        }

        var overrides = snapshot.overrideMap
        var originals = snapshot.originalHealthKitMap

        // Restore the raw HK field from the captured original, then drop
        // the override + the captured original (override-and-original move
        // as a unit so subsequent edits start fresh).
        if let original = originals.value(for: field) {
            assignRawValue(original, for: field, on: snapshot)
        }
        overrides.clear(field)
        originals.clear(field)

        snapshot.overridesData = overrides.encode()
        snapshot.originalHealthKitValuesData = originals.encode()
        snapshot.lastRecomputedAt = recomputedAt

        do {
            try modelContext.save()
        } catch {
            modelContext.rollback()
            throw OverrideError.persistenceFailed
        }
    }

    // MARK: - Validation

    private func isValid(_ value: Double, for field: SnapshotOverrideMap.Field) -> Bool {
        guard value >= 0 else { return false }
        switch field {
        case .stepCount: return value <= 100_000
        case .sleepHours: return value <= 24
        case .exerciseMinutes: return value <= 1_440
        case .activeEnergyKcal: return value <= 20_000
        }
    }

    // MARK: - Internals

    private func fetchSnapshot(for dayStart: Date) -> DailyHealthSnapshot? {
        let descriptor = FetchDescriptor<DailyHealthSnapshot>(
            predicate: #Predicate { $0.date == dayStart }
        )
        return try? modelContext.fetch(descriptor).first
    }

    private func assignRawValue(
        _ value: Double,
        for field: SnapshotOverrideMap.Field,
        on snapshot: DailyHealthSnapshot
    ) {
        switch field {
        case .stepCount: snapshot.stepCount = Int(value)
        case .sleepHours: snapshot.sleepHours = value
        case .exerciseMinutes: snapshot.exerciseMinutes = Int(value)
        case .activeEnergyKcal: snapshot.activeEnergyKcal = value
        }
    }
}
