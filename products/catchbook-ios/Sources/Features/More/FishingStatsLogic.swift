import Foundation

/// Pure computation behind the Fishing Stats screen. Every helper is
/// deterministic and takes its inputs as plain arrays so it can be unit
/// tested without touching SwiftData or SwiftUI.
///
/// The view layer binds SwiftData queries, passes them through `build(...)`,
/// and renders the resulting `FishingStats` struct.
enum FishingStatsLogic {
    // MARK: - Top-level builder

    static func build(
        trips: [Trip],
        catches: [CatchRecord],
        personalBests: [PersonalBest],
        now: Date = .now,
        calendar: Calendar = .current
    ) -> FishingStats {
        let completedTrips = trips.filter { !$0.isActive }

        return FishingStats(
            headline: headline(
                trips: completedTrips,
                catches: catches,
                personalBests: personalBests
            ),
            activity: activity(
                trips: completedTrips,
                catches: catches,
                calendar: calendar
            ),
            species: topSpecies(catches: catches, limit: 5),
            lures: topLures(catches: catches, limit: 5),
            spots: topSpots(catches: catches, limit: 5),
            disposition: dispositionBreakdown(catches: catches),
            timeOfDay: timeOfDayBreakdown(catches: catches, calendar: calendar),
            monthly: monthlyBreakdown(
                trips: completedTrips,
                catches: catches,
                now: now,
                calendar: calendar
            )
        )
    }

    // MARK: - Headline

    static func headline(
        trips: [Trip],
        catches: [CatchRecord],
        personalBests: [PersonalBest]
    ) -> FishingStatsHeadline {
        let totalTrips = trips.count
        let totalCatches = catches.count
        let skunkedTrips = trips.filter { $0.outcome == .skunked }.count
        let catchesPerTrip: Double = totalTrips == 0 ? 0 : Double(totalCatches) / Double(totalTrips)
        let totalHours: Double = trips.reduce(0) { sum, trip in
            sum + max(0, trip.durationInterval ?? 0)
        } / 3_600
        let skunkRate: Double = totalTrips == 0 ? 0 : Double(skunkedTrips) / Double(totalTrips)

        return FishingStatsHeadline(
            totalTrips: totalTrips,
            totalCatches: totalCatches,
            catchesPerTrip: catchesPerTrip,
            totalHoursFished: totalHours,
            skunkedTrips: skunkedTrips,
            skunkRate: skunkRate,
            personalBestCount: personalBests.count
        )
    }

    // MARK: - Activity

    static func activity(
        trips: [Trip],
        catches: [CatchRecord],
        calendar: Calendar
    ) -> FishingStatsActivity {
        let biggestFishByWeight = catches
            .compactMap { record -> (CatchRecord, Double)? in
                guard let weight = record.weightKg, weight > 0 else { return nil }
                return (record, weight)
            }
            .max(by: { $0.1 < $1.1 })?.0

        let longestFish = catches
            .compactMap { record -> (CatchRecord, Double)? in
                guard let length = record.lengthCm, length > 0 else { return nil }
                return (record, length)
            }
            .max(by: { $0.1 < $1.1 })?.0

        let firstTripAt = trips.map(\.startAt).min()
        let lastTripAt = trips.map(\.startAt).max()

        let distinctSpecies = Set(
            catches.map { $0.species.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() }
                .filter { !$0.isEmpty }
        ).count

        return FishingStatsActivity(
            biggestByWeight: biggestFishByWeight.map {
                FishingStatsHighlight(
                    species: $0.speciesDisplayName,
                    value: $0.weightKg ?? 0,
                    unit: "kg",
                    caughtAt: $0.caughtAt
                )
            },
            longestByLength: longestFish.map {
                FishingStatsHighlight(
                    species: $0.speciesDisplayName,
                    value: $0.lengthCm ?? 0,
                    unit: "cm",
                    caughtAt: $0.caughtAt
                )
            },
            firstTripAt: firstTripAt,
            lastTripAt: lastTripAt,
            distinctSpecies: distinctSpecies
        )
    }

    // MARK: - Top species / lures / spots

    static func topSpecies(catches: [CatchRecord], limit: Int) -> [FishingStatsEntry] {
        buckets(
            from: catches,
            key: { normalized($0.species) },
            displayName: { _, key in key.prefix(1).uppercased() + key.dropFirst() },
            limit: limit
        )
    }

    static func topLures(catches: [CatchRecord], limit: Int) -> [FishingStatsEntry] {
        buckets(
            from: catches,
            key: { normalized($0.lureOrBait) },
            displayName: { _, key in key.prefix(1).uppercased() + key.dropFirst() },
            limit: limit
        )
    }

    static func topSpots(catches: [CatchRecord], limit: Int) -> [FishingStatsEntry] {
        var counts: [String: (count: Int, display: String)] = [:]
        for record in catches {
            guard let spot = record.trip?.spot else { continue }
            let trimmed = spot.title.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { continue }
            let key = trimmed.lowercased()
            let current = counts[key, default: (0, trimmed)]
            counts[key] = (current.count + 1, current.display)
        }
        return counts.values
            .sorted(by: sortEntries)
            .prefix(limit)
            .map { FishingStatsEntry(label: $0.display, count: $0.count) }
    }

    // MARK: - Disposition

    static func dispositionBreakdown(catches: [CatchRecord]) -> FishingStatsDisposition {
        var released = 0
        var kept = 0
        var unknown = 0
        for record in catches {
            switch record.disposition {
            case .released: released += 1
            case .kept: kept += 1
            case .notRecorded: unknown += 1
            }
        }
        return FishingStatsDisposition(released: released, kept: kept, unknown: unknown)
    }

    // MARK: - Time of day

    static func timeOfDayBreakdown(catches: [CatchRecord], calendar: Calendar) -> [FishingStatsEntry] {
        // Use the same label buckets `timeWindowLabel` produces so the
        // text matches the rest of the app.
        let buckets = ["6-9 AM", "9 AM-Noon", "Noon-3 PM", "3-7 PM", "Evening"]
        var counts: [String: Int] = [:]
        for record in catches {
            let label = timeWindowLabel(for: record.caughtAt, calendar: calendar)
            counts[label, default: 0] += 1
        }
        // Preserve canonical order (morning → evening) rather than sorting
        // by count — chronological order is more useful for a bar chart.
        return buckets.compactMap { label in
            let count = counts[label, default: 0]
            guard count > 0 else { return nil }
            return FishingStatsEntry(label: label, count: count)
        }
    }

    // MARK: - Monthly breakdown

    static func monthlyBreakdown(
        trips: [Trip],
        catches: [CatchRecord],
        now: Date,
        calendar: Calendar
    ) -> [FishingStatsMonthEntry] {
        // 12-month rolling window ending with the current month.
        guard let firstMonthStart = calendar.date(
            byAdding: .month,
            value: -11,
            to: startOfMonth(for: now, calendar: calendar)
        ) else {
            return []
        }

        var months: [(start: Date, label: String)] = []
        for i in 0..<12 {
            guard let start = calendar.date(byAdding: .month, value: i, to: firstMonthStart) else {
                continue
            }
            months.append((start: start, label: monthLabel(for: start, calendar: calendar)))
        }

        var tripCounts = [Date: Int](minimumCapacity: 12)
        for trip in trips {
            let bucket = startOfMonth(for: trip.startAt, calendar: calendar)
            if bucket >= firstMonthStart {
                tripCounts[bucket, default: 0] += 1
            }
        }
        var catchCounts = [Date: Int](minimumCapacity: 12)
        for record in catches {
            let bucket = startOfMonth(for: record.caughtAt, calendar: calendar)
            if bucket >= firstMonthStart {
                catchCounts[bucket, default: 0] += 1
            }
        }

        return months.map { month in
            FishingStatsMonthEntry(
                monthStart: month.start,
                label: month.label,
                tripCount: tripCounts[month.start, default: 0],
                catchCount: catchCounts[month.start, default: 0]
            )
        }
    }

    // MARK: - Helpers

    private static func normalized(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }

    /// Ordering helper that the various top-N builders share: sort by
    /// count descending, then alphabetically so the output is stable for
    /// unit tests and predictable for users.
    private static func sortEntries(
        _ lhs: (count: Int, display: String),
        _ rhs: (count: Int, display: String)
    ) -> Bool {
        if lhs.count != rhs.count {
            return lhs.count > rhs.count
        }
        return lhs.display.localizedCaseInsensitiveCompare(rhs.display) == .orderedAscending
    }

    private static func buckets(
        from catches: [CatchRecord],
        key: (CatchRecord) -> String,
        displayName: (CatchRecord, String) -> String,
        limit: Int
    ) -> [FishingStatsEntry] {
        var counts: [String: (count: Int, display: String)] = [:]
        for record in catches {
            let k = key(record)
            guard !k.isEmpty else { continue }
            let current = counts[k, default: (0, displayName(record, k))]
            counts[k] = (current.count + 1, current.display)
        }
        return counts.values
            .sorted(by: sortEntries)
            .prefix(limit)
            .map { FishingStatsEntry(label: $0.display, count: $0.count) }
    }

    private static func startOfMonth(for date: Date, calendar: Calendar) -> Date {
        let components = calendar.dateComponents([.year, .month], from: date)
        return calendar.date(from: components) ?? date
    }

    private static func monthLabel(for date: Date, calendar: Calendar) -> String {
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.dateFormat = "MMM"
        return formatter.string(from: date)
    }
}

// MARK: - Value types

struct FishingStats: Equatable {
    let headline: FishingStatsHeadline
    let activity: FishingStatsActivity
    let species: [FishingStatsEntry]
    let lures: [FishingStatsEntry]
    let spots: [FishingStatsEntry]
    let disposition: FishingStatsDisposition
    let timeOfDay: [FishingStatsEntry]
    let monthly: [FishingStatsMonthEntry]

    var hasAnyData: Bool {
        headline.totalTrips > 0 || headline.totalCatches > 0
    }
}

struct FishingStatsHeadline: Equatable {
    let totalTrips: Int
    let totalCatches: Int
    let catchesPerTrip: Double
    let totalHoursFished: Double
    let skunkedTrips: Int
    let skunkRate: Double
    let personalBestCount: Int
}

struct FishingStatsActivity: Equatable {
    let biggestByWeight: FishingStatsHighlight?
    let longestByLength: FishingStatsHighlight?
    let firstTripAt: Date?
    let lastTripAt: Date?
    let distinctSpecies: Int
}

struct FishingStatsHighlight: Equatable {
    let species: String
    let value: Double
    let unit: String
    let caughtAt: Date
}

struct FishingStatsEntry: Equatable, Identifiable {
    var id: String { label }
    let label: String
    let count: Int
}

struct FishingStatsDisposition: Equatable {
    let released: Int
    let kept: Int
    let unknown: Int

    var total: Int { released + kept + unknown }
}

struct FishingStatsMonthEntry: Equatable, Identifiable {
    var id: Date { monthStart }
    let monthStart: Date
    let label: String
    let tripCount: Int
    let catchCount: Int
}
