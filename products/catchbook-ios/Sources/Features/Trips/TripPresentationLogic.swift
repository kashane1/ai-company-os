import Foundation

struct TripRowSummary {
    let catchCountText: String
    let showsSkunkedStyle: Bool
    let durationText: String?
    let spotTitle: String?
}

struct TripMemoryRecap {
    let primaryLine: String
    let secondaryLine: String?
}

struct TripDetailRecallItem: Identifiable {
    let id: String
    let title: String
    let value: String
    let evidence: String?
}

struct TripDetailRecallSummary {
    let headline: String
    let supportingText: String?
    let items: [TripDetailRecallItem]
}

struct TripSpotReplaySummary: Identifiable {
    let id: UUID
    let trip: Trip
    let dateText: String
    let catchText: String
    let isSkunked: Bool
}

struct TripStatItem: Identifiable {
    let id: String
    let value: String
    let label: String
    let icon: String
}

enum TripPresentationLogic {
    static func tripRowSummary(
        trip: Trip,
        catchCount: Int,
        durationFormatter: DateComponentsFormatter = AppFormatters.duration
    ) -> TripRowSummary {
        let showsSkunkedStyle = catchCount == 0 && !trip.isActive
        let catchCountText = showsSkunkedStyle ? "Skunked" : "\(catchCount)"
        let durationText = trip.endAt.flatMap { endAt in
            durationFormatter.string(from: endAt.timeIntervalSince(trip.startAt))
        }
        return TripRowSummary(
            catchCountText: catchCountText,
            showsSkunkedStyle: showsSkunkedStyle,
            durationText: durationText,
            spotTitle: trip.spot?.title
        )
    }

    static func tripMemoryRecap(
        trip: Trip,
        catches: [CatchRecord],
        calendar: Calendar = .current
    ) -> TripMemoryRecap {
        let catchCount = catches.count
        let topSpecies = Dictionary(grouping: catches, by: \.speciesDisplayName)
            .max { lhs, rhs in
                if lhs.value.count != rhs.value.count {
                    return lhs.value.count < rhs.value.count
                }
                return lhs.key > rhs.key
            }?
            .key

        let lureCounts = catches.reduce(into: [String: Int]()) { counts, catchRecord in
            let lure = catchRecord.lureOrBait.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !lure.isEmpty else { return }
            counts[lure, default: 0] += 1
        }
        let topLure = lureCounts.max { lhs, rhs in
            if lhs.value != rhs.value {
                return lhs.value < rhs.value
            }
            return lhs.key > rhs.key
        }?.key

        let timeWindowText: String? = {
            let representativeDate = catches.first?.caughtAt ?? trip.endAt ?? trip.startAt
            return timeWindowLabel(for: representativeDate, calendar: calendar)
        }()

        var primaryComponents = [catchCount == 0 ? "Skunked" : "\(catchCount) \(catchCount == 1 ? "catch" : "catches")"]
        if let topSpecies {
            primaryComponents.append("Top species \(topSpecies)")
        }

        var secondaryComponents: [String] = []
        if let topLure {
            secondaryComponents.append("Top lure \(topLure)")
        }
        if let timeWindowText {
            secondaryComponents.append(timeWindowText)
        }

        return TripMemoryRecap(
            primaryLine: primaryComponents.joined(separator: " · "),
            secondaryLine: secondaryComponents.isEmpty ? nil : secondaryComponents.joined(separator: " · ")
        )
    }

    static func tripDetailRecallSummary(
        trip: Trip,
        catches: [CatchRecord],
        calendar: Calendar = .current
    ) -> TripDetailRecallSummary {
        let catchCount = catches.count
        let outcomeValue: String
        if catchCount == 0 {
            outcomeValue = trip.isActive ? "In progress" : "Skunked"
        } else {
            outcomeValue = "Productive"
        }

        var items: [TripDetailRecallItem] = [
            TripDetailRecallItem(
                id: "outcome",
                title: "Catch outcome",
                value: outcomeValue,
                evidence: catchCount == 0 ? nil : "\(catchCount) \(catchCount == 1 ? "catch" : "catches") logged"
            )
        ]

        if let topSpecies = topSpeciesSummary(from: catches) {
            items.append(
                TripDetailRecallItem(
                    id: "species",
                    title: "Top species",
                    value: topSpecies.value,
                    evidence: topSpecies.evidence
                )
            )
        }

        if let topLure = topLureSummary(from: catches) {
            items.append(
                TripDetailRecallItem(
                    id: "lure",
                    title: "Strongest lure signal",
                    value: topLure.value,
                    evidence: topLure.evidence
                )
            )
        }

        if let bestCatch = bestCatchSummary(from: catches) {
            items.append(
                TripDetailRecallItem(
                    id: "best-catch",
                    title: "Best catch",
                    value: bestCatch.value,
                    evidence: bestCatch.evidence
                )
            )
        }

        let timeWindow = strongestTimeWindowSummary(
            trip: trip,
            catches: catches,
            calendar: calendar
        )
        items.append(
            TripDetailRecallItem(
                id: "time-window",
                title: "Time window",
                value: timeWindow.value,
                evidence: timeWindow.evidence
            )
        )

        let headline: String
        let supportingText: String?
        if catchCount == 0 {
            headline = trip.isActive ? "0 catches logged so far" : "Skunked"
            supportingText = trip.isActive ? "This trip is still live and saved privately." : "No catches were logged on this trip."
        } else {
            headline = "\(catchCount) \(catchCount == 1 ? "catch" : "catches") logged"
            if let topSpecies = topSpeciesSummary(from: catches)?.value {
                supportingText = "\(topSpecies) showed up most often in this trip's catch log."
            } else {
                supportingText = nil
            }
        }

        return TripDetailRecallSummary(
            headline: headline,
            supportingText: supportingText,
            items: items
        )
    }

    static func recentSpotTripSummaries(
        currentTrip: Trip,
        allTrips: [Trip],
        catches: [CatchRecord],
        limit: Int = 3,
        dateFormatter: DateFormatter = AppFormatters.tripDate
    ) -> [TripSpotReplaySummary] {
        guard let spotID = currentTrip.spot?.id else { return [] }

        let catchCountsByTripID: [UUID: Int] = Dictionary(catches.compactMap { catchRecord in
            guard let tripID = catchRecord.trip?.id else { return nil }
            return (tripID, 1)
        }, uniquingKeysWith: +)

        return allTrips
            .filter { $0.id != currentTrip.id && $0.spot?.id == spotID }
            .sorted { $0.startAt > $1.startAt }
            .prefix(limit)
            .map { trip in
                let catchCount = catchCountsByTripID[trip.id, default: 0]
                let isSkunked = catchCount == 0 && !trip.isActive
                return TripSpotReplaySummary(
                    id: trip.id,
                    trip: trip,
                    dateText: dateFormatter.string(from: trip.startAt),
                    catchText: isSkunked ? "Skunked" : "\(catchCount) \(catchCount == 1 ? "catch" : "catches")",
                    isSkunked: isSkunked
                )
            }
    }

    static func topStats(
        catchCount: Int,
        durationText: String?,
        targetSpeciesCount: Int
    ) -> [TripStatItem] {
        var stats: [TripStatItem] = [
            TripStatItem(
                id: "catches",
                value: "\(catchCount)",
                label: catchCount == 1 ? "Catch" : "Catches",
                icon: "fish"
            )
        ]
        if let durationText {
            stats.append(TripStatItem(id: "duration", value: durationText, label: "Duration", icon: "timer"))
        }
        if targetSpeciesCount > 0 {
            stats.append(
                TripStatItem(
                    id: "targets",
                    value: "\(targetSpeciesCount)",
                    label: targetSpeciesCount == 1 ? "Target" : "Targets",
                    icon: "scope"
                )
            )
        }
        return stats
    }

    private static func topSpeciesSummary(from catches: [CatchRecord]) -> (value: String, evidence: String)? {
        let counts = Dictionary(grouping: catches, by: \.speciesDisplayName).mapValues(\.count)
        guard let winner = counts.max(by: { lhs, rhs in
            if lhs.value != rhs.value {
                return lhs.value < rhs.value
            }
            return lhs.key > rhs.key
        }) else {
            return nil
        }

        return (
            value: winner.key,
            evidence: supportLabel(count: winner.value, unit: "catch")
        )
    }

    private static func topLureSummary(from catches: [CatchRecord]) -> (value: String, evidence: String)? {
        let eligible = catches.compactMap { catchRecord -> String? in
            let lure = catchRecord.lureOrBait.trimmingCharacters(in: .whitespacesAndNewlines)
            return lure.isEmpty ? nil : lure
        }
        let counts = Dictionary(grouping: eligible, by: { $0 }).mapValues(\.count)
        guard let winner = counts.max(by: { lhs, rhs in
            if lhs.value != rhs.value {
                return lhs.value < rhs.value
            }
            return lhs.key > rhs.key
        }) else {
            return nil
        }

        return (
            value: winner.key,
            evidence: supportLabel(count: winner.value, unit: "catch")
        )
    }

    private static func bestCatchSummary(from catches: [CatchRecord]) -> (value: String, evidence: String?)? {
        let eligible = catches.filter { $0.lengthCm != nil || $0.weightKg != nil }
        guard let bestCatch = eligible.max(by: { lhs, rhs in
            bestCatchScore(for: lhs) < bestCatchScore(for: rhs)
        }) else {
            return nil
        }

        let metrics = [
            bestCatch.lengthCm.map { "\($0.formatted()) cm" },
            bestCatch.weightKg.map { "\($0.formatted()) kg" },
        ]
        .compactMap { $0 }
        .joined(separator: " · ")
        let evidence: String? = metrics.isEmpty ? nil : metrics

        return (
            value: bestCatch.speciesDisplayName,
            evidence: evidence
        )
    }

    private static func strongestTimeWindowSummary(
        trip: Trip,
        catches: [CatchRecord],
        calendar: Calendar
    ) -> (value: String, evidence: String?) {
        guard !catches.isEmpty else {
            return (timeWindowLabel(for: trip.startAt, calendar: calendar), "From trip timing")
        }

        var counts: [String: Int] = [:]
        for catchRecord in catches {
            let label = timeWindowLabel(for: catchRecord.caughtAt, calendar: calendar)
            counts[label, default: 0] += 1
        }

        let winner = counts.max { lhs, rhs in
            if lhs.value != rhs.value {
                return lhs.value < rhs.value
            }
            return lhs.key > rhs.key
        }

        return (
            winner?.key ?? timeWindowLabel(for: trip.startAt, calendar: calendar),
            winner.map { supportLabel(count: $0.value, unit: "catch") }
        )
    }

    private static func bestCatchScore(for catchRecord: CatchRecord) -> Double {
        let lengthScore = catchRecord.lengthCm ?? 0
        let weightScore = (catchRecord.weightKg ?? 0) * 10
        return max(lengthScore, weightScore)
    }

    private static func supportLabel(count: Int, unit: String) -> String {
        let pluralUnit: String
        if count == 1 {
            pluralUnit = unit
        } else if unit == "catch" {
            pluralUnit = "catches"
        } else {
            pluralUnit = "\(unit)s"
        }
        return "\(count) \(pluralUnit)"
    }
}
