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
}
