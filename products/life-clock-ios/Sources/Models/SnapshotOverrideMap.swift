import Foundation

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
    /// "never written" rows.
    static func decode(from data: Data) -> SnapshotOverrideMap {
        guard !data.isEmpty else { return SnapshotOverrideMap() }
        return (try? JSONDecoder().decode(SnapshotOverrideMap.self, from: data))
            ?? SnapshotOverrideMap()
    }

    /// Encode for storage. Empty maps encode to `Data()` so writes are
    /// indistinguishable from "never written" — keeps disk usage minimal.
    func encode() -> Data {
        guard !isEmpty else { return Data() }
        return (try? JSONEncoder().encode(self)) ?? Data()
    }
}
