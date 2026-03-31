import Foundation

struct SpotRecallSummary {
    struct SeasonalityInsight {
        let title: String
        let body: String
        let supportingSampleCount: Int
    }

    let recentTrips: [Trip]
    let catchCount: Int
    let successfulTripCount: Int
    let bestTimeWindow: String?
    let mostEffectiveLure: String?
    let seasonalityInsight: SeasonalityInsight?
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

        if let seasonalityInsight {
            cards.append(
                DeterministicInsightCard(
                    kind: .seasonality,
                    title: seasonalityInsight.title,
                    body: seasonalityInsight.body,
                    supportingSampleCount: seasonalityInsight.supportingSampleCount,
                    systemImage: "calendar"
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
        let productiveTrips = spotTrips.filter { successfulTripIDs.contains($0.id) }
        let bestTimeWindow = timeWindowCounts.max(by: { $0.value < $1.value })?.key

        var similarityCounts: [String: Int] = [:]
        for trip in spotTrips where successfulTripIDs.contains(trip.id) {
            let signature = trip.conditionSnapshot?.similarityDescription ?? timeWindowLabel(for: trip.startAt)
            similarityCounts[signature, default: 0] += 1
        }

        let mostCommonSimilarity = similarityCounts.max(by: { $0.value < $1.value })
        let seasonalityInsight = strongestSeasonalityInsight(for: productiveTrips)

        return SpotRecallSummary(
            recentTrips: Array(spotTrips.prefix(3)),
            catchCount: spotCatches.count,
            successfulTripCount: successfulTripIDs.count,
            bestTimeWindow: bestTimeWindow,
            mostEffectiveLure: lureCounts.max(by: { $0.value < $1.value })?.key,
            seasonalityInsight: seasonalityInsight,
            similarConditionsCount: mostCommonSimilarity?.value ?? 0,
            similarConditionsLabel: mostCommonSimilarity?.key
        )
    }

    private static func strongestSeasonalityInsight(
        for productiveTrips: [Trip],
        calendar: Calendar = .current
    ) -> SeasonalityInsight? {
        guard productiveTrips.count >= 3 else { return nil }

        let productiveTripCount = productiveTrips.count

        let monthCounts = Dictionary(grouping: productiveTrips) { trip in
            calendar.component(.month, from: trip.startAt)
        }.mapValues(\.count)

        if let strongestMonth = strongestBucket(in: monthCounts) {
            let monthLabel = calendar.monthSymbols[strongestMonth.key - 1]
            return SeasonalityInsight(
                title: "\(monthLabel) has been strongest here",
                body: "\(monthLabel) accounts for \(strongestMonth.value) of your \(productiveTripCount) productive trips at this spot.",
                supportingSampleCount: strongestMonth.value
            )
        }

        let seasonCounts = Dictionary(grouping: productiveTrips) { trip in
            season(for: trip.startAt, calendar: calendar)
        }.mapValues(\.count)

        guard let strongestSeason = strongestBucket(in: seasonCounts) else { return nil }

        return SeasonalityInsight(
            title: "\(strongestSeason.key.label) has been strongest here",
            body: "\(strongestSeason.key.label) accounts for \(strongestSeason.value) of your \(productiveTripCount) productive trips at this spot.",
            supportingSampleCount: strongestSeason.value
        )
    }

    private static func strongestBucket<T: Hashable>(in counts: [T: Int]) -> (key: T, value: Int)? {
        guard counts.count > 0 else { return nil }

        let sortedCounts = counts.values.sorted(by: >)
        guard let topCount = sortedCounts.first, topCount >= 3 else { return nil }

        if sortedCounts.count > 1, sortedCounts[1] == topCount {
            return nil
        }

        return counts.first { $0.value == topCount }
    }

    private static func season(for date: Date, calendar: Calendar) -> TripSeasonFilter {
        switch calendar.component(.month, from: date) {
        case 3 ... 5:
            return .spring
        case 6 ... 8:
            return .summer
        case 9 ... 11:
            return .fall
        default:
            return .winter
        }
    }
}
