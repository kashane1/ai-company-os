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

struct SpotRecallDetailItem: Identifiable {
    let id: String
    let title: String
    let value: String
    let evidence: String?
}

struct SpotRecentTripSummary: Identifiable {
    let id: UUID
    let dateText: String
    let outcomeText: String
    let isSkunked: Bool
    let conditionSummary: String?
}

enum SpotPresentationLogic {
    static func privateRecallCards(for summary: SpotRecallSummary) -> [DeterministicInsightCard] {
        summary.cards
    }

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
            tripCountText: "\(summary.tripCount)",
            catchCountText: "\(summary.catchCount)",
            productiveTripCountText: "\(summary.successfulTripCount)"
        )
    }

    static func recallDetails(for summary: SpotRecallSummary) -> [SpotRecallDetailItem] {
        var items: [SpotRecallDetailItem] = []

        if let mostEffectiveLure = summary.mostEffectiveLure {
            items.append(
                SpotRecallDetailItem(
                    id: "lure",
                    title: "Most effective lure",
                    value: mostEffectiveLure,
                    evidence: evidenceLabel(
                        supportCount: summary.mostEffectiveLureSupportCount,
                        unit: "catch"
                    )
                )
            )
        }

        if let bestTimeWindow = summary.bestTimeWindow {
            items.append(
                SpotRecallDetailItem(
                    id: "time-window",
                    title: "Best time window",
                    value: bestTimeWindow,
                    evidence: evidenceLabel(
                        supportCount: summary.bestTimeWindowSupportCount,
                        unit: "catch"
                    )
                )
            )
        }

        if let simpleConditionSummary = summary.simpleConditionSummary {
            items.append(
                SpotRecallDetailItem(
                    id: "conditions",
                    title: "Simple condition summary",
                    value: simpleConditionSummary,
                    evidence: evidenceLabel(
                        supportCount: summary.simpleConditionSupportCount,
                        unit: "productive trip"
                    )
                )
            )
        }

        return items
    }

    private static func evidenceLabel(supportCount: Int, unit: String) -> String? {
        guard supportCount > 0 else { return nil }
        let pluralizedUnit: String
        if supportCount == 1 {
            pluralizedUnit = unit
        } else if unit == "catch" {
            pluralizedUnit = "catches"
        } else {
            pluralizedUnit = "\(unit)s"
        }
        return "Based on \(supportCount) \(pluralizedUnit)"
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
