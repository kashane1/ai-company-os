import Foundation

struct SpotRecallSummary {
    struct ConditionsInsight {
        let title: String
        let body: String
        let supportingSampleCount: Int
    }

    struct SpeciesInsight {
        let title: String
        let body: String
        let supportingSampleCount: Int
    }

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

    struct LureInsight {
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
    let speciesInsight: SpeciesInsight?
    let conditionsInsight: ConditionsInsight?
    let lureInsight: LureInsight?
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

        if let speciesInsight {
            cards.append(
                DeterministicInsightCard(
                    kind: .species,
                    title: speciesInsight.title,
                    body: speciesInsight.body,
                    supportingSampleCount: speciesInsight.supportingSampleCount,
                    systemImage: "fish"
                )
            )
        }

        if let conditionsInsight {
            cards.append(
                DeterministicInsightCard(
                    kind: .conditions,
                    title: conditionsInsight.title,
                    body: conditionsInsight.body,
                    supportingSampleCount: conditionsInsight.supportingSampleCount,
                    systemImage: "cloud.sun"
                )
            )
        }

        if let lureInsight {
            cards.append(
                DeterministicInsightCard(
                    kind: .lure,
                    title: lureInsight.title,
                    body: lureInsight.body,
                    supportingSampleCount: lureInsight.supportingSampleCount,
                    systemImage: "bolt.horizontal"
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
                    body: "\(similarConditionsCount) completed trips with catches here lined up with \(similarConditionsLabel).",
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

        let recencyInsight = recentActivityInsight(
            completedTrips: completedTrips,
            successfulTripIDs: successfulTripIDs,
            catchCountsByTripID: catchCountsByTripID
        )
        let productivityInsight = recentProductivityInsight(
            completedTrips: completedTrips,
            successfulTripIDs: successfulTripIDs
        )
        let speciesInsight = mostReliableSpeciesInsight(
            completedTrips: completedTrips,
            catches: spotCatches
        )
        let conditionsInsight = strongestConditionsInsight(
            completedTrips: completedTrips,
            successfulTripIDs: successfulTripIDs
        )
        let lureInsight = strongestLureInsight(
            completedTrips: completedTrips,
            catches: spotCatches
        )
        let similarConditionsInsight = strongestSimilarConditionsInsight(
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
            speciesInsight: speciesInsight,
            conditionsInsight: conditionsInsight,
            lureInsight: lureInsight,
            bestTimeWindow: bestTimeWindow,
            mostEffectiveLure: lureCounts.max(by: { $0.value < $1.value })?.key,
            seasonalityInsight: seasonalityInsight,
            similarConditionsCount: similarConditionsInsight?.supportingSampleCount ?? 0,
            similarConditionsLabel: similarConditionsInsight?.displayLabel
        )
    }

    private static func strongestLureInsight(
        completedTrips: [Trip],
        catches: [CatchRecord]
    ) -> LureInsight? {
        struct LureStats {
            let normalizedLabel: String
            let displayLabel: String
            let tripCount: Int
        }

        let completedTripIDs = Set(completedTrips.map(\.id))
        let eligibleCatches = catches.compactMap { catchRecord -> (tripID: UUID, normalizedLabel: String, displayLabel: String)? in
            guard
                let tripID = catchRecord.trip?.id,
                completedTripIDs.contains(tripID)
            else {
                return nil
            }

            let displayLabel = catchRecord.lureOrBait.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !displayLabel.isEmpty else { return nil }

            return (tripID, displayLabel.lowercased(), displayLabel)
        }

        let catchesByTrip = Dictionary(grouping: eligibleCatches, by: \.tripID)
        let eligibleTripIDs = Set(catchesByTrip.keys)
        guard eligibleTripIDs.count >= 4 else { return nil }

        let statsByLure = Dictionary(grouping: eligibleCatches, by: \.normalizedLabel).compactMapValues { catchesForLure -> LureStats? in
            guard let first = catchesForLure.first else { return nil }
            let tripIDs = Set(catchesForLure.map(\.tripID))

            return LureStats(
                normalizedLabel: first.normalizedLabel,
                displayLabel: first.displayLabel,
                tripCount: tripIDs.count
            )
        }

        let sortedStats = statsByLure.values.sorted { lhs, rhs in
            if lhs.tripCount != rhs.tripCount {
                return lhs.tripCount > rhs.tripCount
            }

            return lhs.normalizedLabel < rhs.normalizedLabel
        }

        guard let winningStats = sortedStats.first else { return nil }
        guard winningStats.tripCount >= 3 else { return nil }

        if sortedStats.count > 1 {
            let runnerUp = sortedStats[1]
            guard runnerUp.tripCount < winningStats.tripCount - 1 else { return nil }
        }

        return LureInsight(
            title: "Most reliable lure here",
            body: "\(winningStats.displayLabel) has shown up on \(winningStats.tripCount) completed trips with catches here.",
            supportingSampleCount: winningStats.tripCount
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

    private static func strongestConditionsInsight(
        completedTrips: [Trip],
        successfulTripIDs: Set<UUID>
    ) -> ConditionsInsight? {
        let productiveCompletedTrips = completedTrips.filter { successfulTripIDs.contains($0.id) }
        guard productiveCompletedTrips.count >= 4 else { return nil }

        var timeWindowCounts: [String: Int] = [:]
        for trip in productiveCompletedTrips {
            let timeWindow = trip.conditionSnapshot?.timeWindowSummary?.trimmingCharacters(in: .whitespacesAndNewlines)
            guard let timeWindow, !timeWindow.isEmpty else { continue }
            timeWindowCounts[timeWindow, default: 0] += 1
        }

        guard let strongestWindow = strongestConditionsBucket(in: timeWindowCounts) else { return nil }

        return ConditionsInsight(
            title: "Most consistent catch window here",
            body: "Your catches here have lined up most often in \(strongestWindow.key.lowercased()): \(strongestWindow.value) completed trips with catches.",
            supportingSampleCount: strongestWindow.value
        )
    }

    private static func mostReliableSpeciesInsight(
        completedTrips: [Trip],
        catches: [CatchRecord]
    ) -> SpeciesInsight? {
        struct SpeciesStats {
            let normalizedLabel: String
            let displayLabel: String
            let catchCount: Int
            let tripCount: Int
            let maxSingleTripCatchCount: Int
        }

        guard completedTrips.count >= 4 else { return nil }

        let completedTripIDs = Set(completedTrips.map(\.id))
        let eligibleCatches = catches.compactMap { catchRecord -> (tripID: UUID, normalizedLabel: String, displayLabel: String)? in
            guard
                let tripID = catchRecord.trip?.id,
                completedTripIDs.contains(tripID)
            else {
                return nil
            }

            let displayLabel = catchRecord.species.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !displayLabel.isEmpty else { return nil }

            return (tripID, displayLabel.lowercased(), displayLabel)
        }

        let statsBySpecies = Dictionary(grouping: eligibleCatches, by: \.normalizedLabel).compactMapValues { catchesForSpecies -> SpeciesStats? in
            guard let first = catchesForSpecies.first else { return nil }

            let catchesByTrip = Dictionary(grouping: catchesForSpecies, by: \.tripID)
            return SpeciesStats(
                normalizedLabel: first.normalizedLabel,
                displayLabel: first.displayLabel,
                catchCount: catchesForSpecies.count,
                tripCount: catchesByTrip.count,
                maxSingleTripCatchCount: catchesByTrip.values.map(\.count).max() ?? 0
            )
        }

        let sortedStats = statsBySpecies.values.sorted { lhs, rhs in
            if lhs.tripCount != rhs.tripCount {
                return lhs.tripCount > rhs.tripCount
            }
            if lhs.catchCount != rhs.catchCount {
                return lhs.catchCount > rhs.catchCount
            }
            return lhs.normalizedLabel < rhs.normalizedLabel
        }

        guard let winningStats = sortedStats.first else { return nil }
        guard winningStats.tripCount >= 3, winningStats.catchCount >= 4 else { return nil }

        if sortedStats.count == 1 {
            return SpeciesInsight(
                title: "Most reliable species here",
                body: "\(winningStats.displayLabel) has been your most reliable species here: \(winningStats.catchCount) \(winningStats.normalizedLabel) across \(winningStats.tripCount) completed trips.",
                supportingSampleCount: winningStats.tripCount
            )
        }

        let runnerUp = sortedStats[1]

        if winningStats.tripCount == runnerUp.tripCount {
            guard winningStats.catchCount >= runnerUp.catchCount + 2 else { return nil }

            if winningStats.maxSingleTripCatchCount >= runnerUp.catchCount {
                return nil
            }
        } else {
            guard winningStats.tripCount >= runnerUp.tripCount + 1 else { return nil }

            if winningStats.tripCount == runnerUp.tripCount + 1,
               winningStats.maxSingleTripCatchCount >= runnerUp.catchCount {
                return nil
            }
        }

        let body: String
        if winningStats.tripCount >= runnerUp.tripCount + 2 {
            body = "\(winningStats.displayLabel) has been your most reliable species here: \(winningStats.catchCount) \(winningStats.normalizedLabel) across \(winningStats.tripCount) completed trips."
        } else {
            body = "\(winningStats.displayLabel) shows up most often here: \(winningStats.catchCount) \(winningStats.normalizedLabel) across \(winningStats.tripCount) completed trips."
        }

        return SpeciesInsight(
            title: "Most reliable species here",
            body: body,
            supportingSampleCount: winningStats.tripCount
        )
    }

    private static func strongestSimilarConditionsInsight(
        completedTrips: [Trip],
        successfulTripIDs: Set<UUID>
    ) -> (displayLabel: String, supportingSampleCount: Int)? {
        struct SimilarityStats {
            let normalizedLabel: String
            let displayLabel: String
            let tripCount: Int
        }

        let productiveCompletedTrips = completedTrips.filter { successfulTripIDs.contains($0.id) }
        guard productiveCompletedTrips.count >= 4 else { return nil }

        let eligibleTrips = productiveCompletedTrips.compactMap { trip -> (normalizedLabel: String, displayLabel: String, isOnlyTimeWindow: Bool)? in
            guard let conditionSnapshot = trip.conditionSnapshot else {
                return nil
            }

            let rawParts = [
                conditionSnapshot.timeWindowSummary?.trimmingCharacters(in: .whitespacesAndNewlines),
                conditionSnapshot.lightLevelSummary?.trimmingCharacters(in: .whitespacesAndNewlines),
                conditionSnapshot.windSummary?.trimmingCharacters(in: .whitespacesAndNewlines),
                conditionSnapshot.precipitationSummary?.trimmingCharacters(in: .whitespacesAndNewlines),
            ].compactMap { value -> String? in
                guard let value, !value.isEmpty else { return nil }
                return value
            }

            guard !rawParts.isEmpty else { return nil }

            let displayLabel = conditionSnapshot.similarityDescription.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !displayLabel.isEmpty, displayLabel.lowercased() != "recent trip context" else { return nil }

            return (
                normalizedLabel: displayLabel.lowercased(),
                displayLabel: displayLabel,
                isOnlyTimeWindow: rawParts.count == 1 && rawParts.first == conditionSnapshot.timeWindowSummary?.trimmingCharacters(in: .whitespacesAndNewlines)
            )
        }

        let eligibleTripCount = eligibleTrips.count
        guard eligibleTripCount >= 4 else { return nil }

        let statsBySignature = Dictionary(grouping: eligibleTrips, by: \.normalizedLabel).compactMapValues { tripsForSignature -> SimilarityStats? in
            guard let first = tripsForSignature.first else { return nil }
            return SimilarityStats(
                normalizedLabel: first.normalizedLabel,
                displayLabel: first.displayLabel,
                tripCount: tripsForSignature.count
            )
        }

        let sortedStats = statsBySignature.values.sorted { lhs, rhs in
            if lhs.tripCount != rhs.tripCount {
                return lhs.tripCount > rhs.tripCount
            }

            return lhs.normalizedLabel < rhs.normalizedLabel
        }

        guard let winningStats = sortedStats.first else { return nil }
        guard winningStats.tripCount >= 3 else { return nil }

        if sortedStats.count > 1 {
            let runnerUp = sortedStats[1]
            guard runnerUp.tripCount < winningStats.tripCount - 1 else { return nil }
        }

        let winningTrips = eligibleTrips.filter { $0.normalizedLabel == winningStats.normalizedLabel }
        if winningTrips.allSatisfy(\.isOnlyTimeWindow) {
            return nil
        }

        return (
            displayLabel: winningStats.displayLabel,
            supportingSampleCount: winningStats.tripCount
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

    private static func strongestConditionsBucket(in counts: [String: Int]) -> (key: String, value: Int)? {
        guard counts.count > 0 else { return nil }

        let sortedCounts = counts.values.sorted(by: >)
        guard let topCount = sortedCounts.first, topCount >= 3 else { return nil }

        if sortedCounts.count > 1, sortedCounts[1] >= topCount - 1 {
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
