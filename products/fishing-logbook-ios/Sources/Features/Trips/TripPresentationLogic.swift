import Foundation

struct TripRowSummary {
    let catchCountText: String
    let showsSkunkedStyle: Bool
    let durationText: String?
    let spotTitle: String?
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
