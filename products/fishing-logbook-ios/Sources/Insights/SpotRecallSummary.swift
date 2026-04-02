import Foundation

struct SpotRecallSummary {
    struct RecencyInsight {
        let title: String
        let body: String
        let supportingSampleCount: Int
    }

    struct ProductivityInsight {
        let title: String
        let body: String
        let supportingSampleCount: Int
    }

    struct SeasonalityInsight {
        let title: String
        let body: String
        let supportingSampleCount: Int
    }

    let recentTrips: [Trip]
    let catchCount: Int
    let successfulTripCount: Int
    let recencyInsight: RecencyInsight?
    let productivityInsight: ProductivityInsight?
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

        if let recencyInsight {
            cards.append(
                DeterministicInsightCard(
                    kind: .recency,
                    title: recencyInsight.title,
                    body: recencyInsight.body,
                    supportingSampleCount: recencyInsight.supportingSampleCount,
                    systemImage: "waveform.path.ecg"
                )
            )
        }

        if let productivityInsight {
            cards.append(
                DeterministicInsightCard(
                    kind: .productivity,
                    title: productivityInsight.title,
                    body: productivityInsight.body,
                    supportingSampleCount: productivityInsight.supportingSampleCount,
                    systemImage: "chart.line.uptrend.xyaxis"
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
        let completedTrips = spotTrips.filter { $0.endAt != nil }
        let productiveTrips = spotTrips.filter { successfulTripIDs.contains($0.id) }
        let catchCountsByTripID = Dictionary(grouping: spotCatches.compactMap { catchRecord -> UUID? in
            catchRecord.trip?.id
        }, by: { $0 }).mapValues(\.count)
        let bestTimeWindow = timeWindowCounts.max(by: { $0.value < $1.value })?.key

        var similarityCounts: [String: Int] = [:]
        for trip in spotTrips where successfulTripIDs.contains(trip.id) {
            let signature = trip.conditionSnapshot?.similarityDescription ?? timeWindowLabel(for: trip.startAt)
            similarityCounts[signature, default: 0] += 1
        }

        let mostCommonSimilarity = similarityCounts.max(by: { $0.value < $1.value })
        let recencyInsight = recentActivityInsight(
            completedTrips: completedTrips,
            successfulTripIDs: successfulTripIDs,
        catchCountsByTripID: catchCountsByTripID
        )
        let productivityInsight = recentProductivityInsight(
            completedTrips: completedTrips,
            successfulTripIDs: successfulTripIDs
        )
        let seasonalityInsight = strongestSeasonalityInsight(for: productiveTrips)

        return SpotRecallSummary(
            recentTrips: Array(spotTrips.prefix(3)),
            catchCount: spotCatches.count,
            successfulTripCount: successfulTripIDs.count,
            recencyInsight: recencyInsight,
            productivityInsight: productivityInsight,
            bestTimeWindow: bestTimeWindow,
            mostEffectiveLure: lureCounts.max(by: { $0.value < $1.value })?.key,
            seasonalityInsight: seasonalityInsight,
            similarConditionsCount: mostCommonSimilarity?.value ?? 0,
            similarConditionsLabel: mostCommonSimilarity?.key
        )
    }

    private static func recentProductivityInsight(
        completedTrips: [Trip],
        successfulTripIDs: Set<UUID>
    ) -> ProductivityInsight? {
        let recentCompletedTrips = Array(completedTrips.prefix(5))
        let completedTripCount = recentCompletedTrips.count

        guard completedTripCount >= 3 else { return nil }

        let productiveTripCount = recentCompletedTrips.reduce(into: 0) { count, trip in
            if successfulTripIDs.contains(trip.id) {
                count += 1
            }
        }

        guard productiveTripCount == completedTripCount
            || productiveTripCount == completedTripCount - 1
            || productiveTripCount == 0
        else {
            return nil
        }

        if productiveTripCount == completedTripCount {
            return ProductivityInsight(
                title: "Recent success here",
                body: "You caught fish on all \(completedTripCount) of your last \(completedTripCount) completed trips here.",
                supportingSampleCount: completedTripCount
            )
        }

        if productiveTripCount == 0 {
            return ProductivityInsight(
                title: "Recent success here",
                body: "Your last \(completedTripCount) completed trips here ended without a catch.",
                supportingSampleCount: completedTripCount
            )
        }

        return ProductivityInsight(
            title: "Recent success here",
            body: "You caught fish on \(productiveTripCount) of your last \(completedTripCount) completed trips here.",
            supportingSampleCount: completedTripCount
        )
    }

    private static func recentActivityInsight(
        completedTrips: [Trip],
        successfulTripIDs: Set<UUID>,
        catchCountsByTripID: [UUID: Int]
    ) -> RecencyInsight? {
        guard completedTrips.count >= 4 else { return nil }

        let recentCompletedTrips = Array(completedTrips.prefix(4))
        let latestTwoTrips = Array(recentCompletedTrips.prefix(2))
        let previousTwoTrips = Array(recentCompletedTrips.dropFirst(2))
        let latestThreeTrips = Array(recentCompletedTrips.prefix(3))

        let latestTwoCatchCount = latestTwoTrips.reduce(into: 0) { count, trip in
            count += catchCountsByTripID[trip.id] ?? 0
        }
        let previousTwoCatchCount = previousTwoTrips.reduce(into: 0) { count, trip in
            count += catchCountsByTripID[trip.id] ?? 0
        }
        let latestTwoSuccessfulTripCount = latestTwoTrips.reduce(into: 0) { count, trip in
            if successfulTripIDs.contains(trip.id) {
                count += 1
            }
        }
        let latestThreeSuccessfulTripCount = latestThreeTrips.reduce(into: 0) { count, trip in
            if successfulTripIDs.contains(trip.id) {
                count += 1
            }
        }
        let earlierTripWasProductive = previousTwoTrips.contains { successfulTripIDs.contains($0.id) }

        if latestTwoSuccessfulTripCount == 2,
           latestTwoCatchCount >= 3,
           previousTwoCatchCount == 0 {
            return RecencyInsight(
                title: "Recently active here",
                body: "Your catches here have clustered recently: \(latestTwoCatchCount) fish across your last 2 completed trips.",
                supportingSampleCount: recentCompletedTrips.count
            )
        }

        if latestThreeSuccessfulTripCount == 0, earlierTripWasProductive {
            return RecencyInsight(
                title: "Quiet lately here",
                body: "This spot has been quiet lately: no fish on your last 3 completed trips here.",
                supportingSampleCount: recentCompletedTrips.count
            )
        }

        return nil
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
