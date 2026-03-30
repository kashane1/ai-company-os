import Foundation

struct SpotRowDetails {
    let waterbodyName: String
    let isPinned: Bool
    let notesPreview: String?
}

struct SpotStatSummary {
    let tripCountText: String
    let catchCountText: String
    let productiveTripCountText: String
}

struct SpotRecentTripSummary: Identifiable {
    let id: UUID
    let dateText: String
    let outcomeText: String
    let isSkunked: Bool
    let conditionSummary: String?
}

enum SpotPresentationLogic {
    static func rowDetails(for spot: Spot) -> SpotRowDetails {
        let notesPreview = TripEditingLogic.normalizedOptionalText(spot.notes)
        return SpotRowDetails(
            waterbodyName: spot.waterbody?.name ?? "Unknown water",
            isPinned: spot.latitude != nil,
            notesPreview: notesPreview
        )
    }

    static func catchesHere(spotID: UUID, catches: [CatchRecord]) -> [CatchRecord] {
        catches.filter { $0.trip?.spot?.id == spotID }
    }

    static func statSummary(for summary: SpotRecallSummary) -> SpotStatSummary {
        SpotStatSummary(
            tripCountText: "\(summary.recentTrips.count)",
            catchCountText: "\(summary.catchCount)",
            productiveTripCountText: "\(summary.successfulTripCount)"
        )
    }

    static func recentTripSummaries(
        trips: [Trip],
        dateFormatter: DateFormatter = AppFormatters.tripDate
    ) -> [SpotRecentTripSummary] {
        trips.map { trip in
            SpotRecentTripSummary(
                id: trip.id,
                dateText: dateFormatter.string(from: trip.startAt),
                outcomeText: trip.outcomeRawValue.capitalized,
                isSkunked: trip.outcomeRawValue == TripOutcome.skunked.rawValue,
                conditionSummary: trip.conditionSnapshot?.displaySummary
            )
        }
    }
}
