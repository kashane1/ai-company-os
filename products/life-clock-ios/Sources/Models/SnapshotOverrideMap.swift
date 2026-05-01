import Foundation
import UIKit

/// User-applied corrections to HealthKit-derived values on a single
/// `DailyHealthSnapshot`. Stored on the snapshot as encoded `Data` because
/// SwiftData's representation of Swift dictionaries on `@Model` types has
/// been inconsistent across iOS minor releases.
///
/// Field names are restricted to `Field.allCases` raw values — bounded
/// vocabulary keeps decoding safe across versions even if a future build
/// adds or renames overridable fields.
struct SnapshotOverrideMap: Codable, Equatable {
    enum Field: String, CaseIterable, Codable {
        case stepCount
        case sleepHours
        case exerciseMinutes
        case activeEnergyKcal
    }

    /// Map of field → corrected value. Field is stored as raw string so a
    /// future enum case rename never silently drops user data.
    private var values: [String: Double] = [:]

    var isEmpty: Bool { values.isEmpty }

    func value(for field: Field) -> Double? {
        values[field.rawValue]
    }

    var presentFields: [Field] {
        Field.allCases.filter { values[$0.rawValue] != nil }
    }

    mutating func set(_ value: Double, for field: Field) {
        values[field.rawValue] = value
    }

    mutating func clear(_ field: Field) {
        values.removeValue(forKey: field.rawValue)
    }

    // MARK: - Encoded `Data` round-trip

    /// Decode from a snapshot's `overridesData`. Returns an empty map for
    /// `Data()` (the storage default) so callers don't have to special-case
    /// "never written" rows. Decode failures of NON-empty data return an
    /// empty map AND fire an assertion in DEBUG so we hear about corruption
    /// before it silently destroys overrides on the next write. Production
    /// behavior remains "fail closed to empty" so a bad row doesn't crash
    /// the app — but the assertion + the structural defense in
    /// `OverrideService.applyOverride` (write-through to raw field) means
    /// the user's most recently visible value survives a corrupt round trip.
    static func decode(from data: Data) -> SnapshotOverrideMap {
        guard !data.isEmpty else { return SnapshotOverrideMap() }
        do {
            return try JSONDecoder().decode(SnapshotOverrideMap.self, from: data)
        } catch {
            assertionFailure("SnapshotOverrideMap decode failed: \(error). Bytes: \(data.count)")
            return SnapshotOverrideMap()
        }
    }

    /// Encode for storage. Empty maps encode to `Data()` so writes are
    /// indistinguishable from "never written" — keeps disk usage minimal.
    /// Throws on JSONEncoder failure (vanishingly unlikely for `[String:
    /// Double]` but propagated rather than silently swallowed because a
    /// fall-through to `Data()` here would silently wipe every override on
    /// the snapshot the next time `OverrideService` writes it back).
    func encode() throws -> Data {
        guard !isEmpty else { return Data() }
        return try JSONEncoder().encode(self)
    }
}

extension SnapshotOverrideMap.Field {
    /// Static metadata + raw-field accessors per overridable field.
    ///
    /// DELIBERATELY DATA-ONLY — do not add behavior (rendering pipelines,
    /// validation pipelines, side-effecting closures) to this type. The
    /// whole point is that adding a new overridable field becomes one
    /// `Spec` entry, not edits across 7 switch sites. Behavior belongs
    /// on the consumers (OverrideService, OverrideSheet, DayDetailView).
    struct Spec {
        let displayName: String
        let keyboard: UIKeyboardType
        let bounds: ClosedRange<Double>
        let boundsCopy: String
        /// Format `value` for display (e.g. "8,000 steps", "7.5 h").
        let format: (Double) -> String
        /// Format `value` for the OverrideSheet text field — bare number,
        /// no unit (e.g. "8000", "7.5"). Matches the keyboard type.
        let editorFormat: (Double) -> String
        /// Read the raw HK field for this metric, returning nil when HK
        /// never delivered a value.
        let rawGetter: (DailyHealthSnapshot) -> Double?
        /// Write `value` to the raw HK field for this metric. Used by
        /// OverrideService to write the override through to the field
        /// the engine reads.
        let rawSetter: (DailyHealthSnapshot, Double) -> Void
    }

    var spec: Spec {
        switch self {
        case .stepCount:
            return Spec(
                displayName: "Steps",
                keyboard: .numberPad,
                bounds: 0...100_000,
                boundsCopy: "0–100,000 steps",
                format: { "\(Int($0)) steps" },
                editorFormat: { String(Int($0)) },
                rawGetter: { $0.stepCount.map(Double.init) },
                rawSetter: { $0.stepCount = Int($1) }
            )
        case .sleepHours:
            return Spec(
                displayName: "Sleep",
                keyboard: .decimalPad,
                bounds: 0...24,
                boundsCopy: "0–24 hours",
                format: { String(format: "%.1f h", $0) },
                editorFormat: { String(format: "%.1f", $0) },
                rawGetter: { $0.sleepHours },
                rawSetter: { $0.sleepHours = $1 }
            )
        case .exerciseMinutes:
            return Spec(
                displayName: "Exercise",
                keyboard: .numberPad,
                bounds: 0...1_440,
                boundsCopy: "0–1,440 minutes",
                format: { "\(Int($0)) min" },
                editorFormat: { String(Int($0)) },
                rawGetter: { $0.exerciseMinutes.map(Double.init) },
                rawSetter: { $0.exerciseMinutes = Int($1) }
            )
        case .activeEnergyKcal:
            return Spec(
                displayName: "Active energy",
                keyboard: .numberPad,
                bounds: 0...20_000,
                boundsCopy: "0–20,000 kcal",
                format: { "\(Int($0)) kcal" },
                editorFormat: { String(Int($0)) },
                rawGetter: { $0.activeEnergyKcal },
                rawSetter: { $0.activeEnergyKcal = $1 }
            )
        }
    }
}
