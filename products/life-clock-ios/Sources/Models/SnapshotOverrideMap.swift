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
