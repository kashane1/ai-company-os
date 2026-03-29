import Foundation

struct SpotRecallSummary {
    let recentTrips: [Trip]
    let catchCount: Int
    let successfulTripCount: Int
    let bestTimeWindow: String?
    let mostEffectiveLure: String?
    let similarConditionsCount: Int
    let similarConditionsLabel: String?

    var cards: [DeterministicInsightCard] {
        var cards: [DeterministicInsightCard] = []

        if let mostRecentTrip = recentTrips.first {
            cards.append(
                DeterministicInsightCard(
                    kind: .lastTrips,
                    title: "Last trips here",
                    body: "You have \(recentTrips.count) recent trips here. The latest was on \(AppFormatters.tripDate.string(from: mostRecentTrip.startAt)).",
                    supportingSampleCount: recentTrips.count,
                    systemImage: "clock.arrow.circlepath"
                )
            )
        }

        if let bestTimeWindow {
            cards.append(
                DeterministicInsightCard(
                    kind: .bestTimeWindow,
                    title: "Best time window historically",
                    body: "Your strongest catch window here has been \(bestTimeWindow).",
                    supportingSampleCount: catchCount,
                    systemImage: "clock"
                )
            )
        }

        if let mostEffectiveLure {
            cards.append(
                DeterministicInsightCard(
                    kind: .mostEffectiveLure,
                    title: "Most effective lure",
                    body: "\(mostEffectiveLure) has produced best in your private history here.",
                    supportingSampleCount: catchCount,
                    systemImage: "bolt.horizontal"
                )
            )
        }

        if let similarConditionsLabel, similarConditionsCount > 0 {
            cards.append(
                DeterministicInsightCard(
                    kind: .similarConditions,
                    title: "Similar conditions",
                    body: "\(similarConditionsCount) productive trips here lined up with \(similarConditionsLabel).",
                    supportingSampleCount: similarConditionsCount,
                    systemImage: "sparkles.rectangle.stack"
                )
            )
        }

        return cards
    }

    static func build(for spot: Spot, trips: [Trip], catches: [CatchRecord]) -> SpotRecallSummary {
        let spotTrips = trips.filter { $0.spot?.id == spot.id }
            .sorted { $0.startAt > $1.startAt }
        let tripIDs = Set(spotTrips.map(\.id))
        let spotCatches = catches.filter { catchRecord in
            guard let tripID = catchRecord.trip?.id else { return false }
            return tripIDs.contains(tripID)
        }

        var timeWindowCounts: [String: Int] = [:]
        for catchRecord in spotCatches {
            let label = timeWindowLabel(for: catchRecord.caughtAt)
            timeWindowCounts[label, default: 0] += 1
        }

        var lureCounts: [String: Int] = [:]
        for catchRecord in spotCatches {
            let lure = catchRecord.lureOrBait.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !lure.isEmpty else { continue }
            lureCounts[lure, default: 0] += 1
        }

        let successfulTripIDs = Set(spotCatches.compactMap { $0.trip?.id })
        let bestTimeWindow = timeWindowCounts.max(by: { $0.value < $1.value })?.key

        var similarityCounts: [String: Int] = [:]
        for trip in spotTrips where successfulTripIDs.contains(trip.id) {
            let signature = trip.conditionSnapshot?.similarityDescription ?? timeWindowLabel(for: trip.startAt)
            similarityCounts[signature, default: 0] += 1
        }

        let mostCommonSimilarity = similarityCounts.max(by: { $0.value < $1.value })

        return SpotRecallSummary(
            recentTrips: Array(spotTrips.prefix(3)),
            catchCount: spotCatches.count,
            successfulTripCount: successfulTripIDs.count,
            bestTimeWindow: bestTimeWindow,
            mostEffectiveLure: lureCounts.max(by: { $0.value < $1.value })?.key,
            similarConditionsCount: mostCommonSimilarity?.value ?? 0,
            similarConditionsLabel: mostCommonSimilarity?.key
        )
    }
}
