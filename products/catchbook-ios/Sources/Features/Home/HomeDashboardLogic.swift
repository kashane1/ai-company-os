import Foundation

struct HomeMemoryCard {
    let title: String
    let body: String
    let footer: String
}

struct HomeLastTripSummary {
    let catchText: String
    let durationText: String?
    let topSpeciesText: String?
}

struct HomeReplayCard {
    let title: String
    let body: String
    let footer: String
}

struct HomeSeasonalCard: Identifiable {
    enum Kind: Comparable {
        case pbAnniversary
        case sameMonthLastYear
        case seasonalSpot
        case genericSeasonal
    }

    let id: String
    let kind: Kind
    let title: String
    let body: String
    let footer: String
}

enum HomeDashboardLogic {
    static func activeTrip(from trips: [Trip]) -> Trip? {
        trips.first(where: \.isActive)
    }

    static func latestCompletedTrip(from trips: [Trip]) -> Trip? {
        trips.first(where: { !$0.isActive })
    }

    static func latestCompletedSpotTrip(from trips: [Trip]) -> Trip? {
        trips.first(where: { !$0.isActive && $0.spot != nil })
    }

    static func completedTripCount(from trips: [Trip]) -> Int {
        trips.filter { !$0.isActive }.count
    }

    static func totalCatchCount(from catches: [CatchRecord]) -> Int {
        catches.count
    }

    static func catchCount(for tripID: UUID, catches: [CatchRecord]) -> Int {
        catches.filter { $0.trip?.id == tripID }.count
    }

    static func shouldShowRecall(
        latestCompletedTrip: Trip?,
        summary: SpotRecallSummary?
    ) -> Bool {
        guard latestCompletedTrip?.spot != nil else { return false }
        guard let summary else { return false }
        return !summary.cards.isEmpty
    }

    static func personalBestLabel(count: Int) -> String {
        count == 1 ? "Best" : "Bests"
    }

    static func personalBestSummaryText(
        longestLengthCm: Double?,
        heaviestWeightKg: Double?,
        formatValue: (Double) -> String = { $0.formatted() }
    ) -> String {
        let parts: [String?] = [
            longestLengthCm.map { "\(formatValue($0)) cm" },
            heaviestWeightKg.map { "\(formatValue($0)) kg" },
        ]
        return parts.compactMap { $0 }.joined(separator: " · ")
    }

    static func elapsedText(
        startAt: Date,
        now: Date = Date(),
        formatDuration: (TimeInterval) -> String? = { AppFormatters.duration.string(from: $0) }
    ) -> String {
        formatDuration(now.timeIntervalSince(startAt)) ?? "now"
    }

    static func lastTripSummary(
        trip: Trip,
        catches: [CatchRecord],
        durationFormatter: DateComponentsFormatter = AppFormatters.duration
    ) -> HomeLastTripSummary {
        let durationText = trip.endAt.flatMap { endAt in
            durationFormatter.string(from: endAt.timeIntervalSince(trip.startAt))
        }
        let topSpeciesText = Dictionary(grouping: catches, by: \.speciesDisplayName)
            .max { lhs, rhs in
                if lhs.value.count != rhs.value.count {
                    return lhs.value.count < rhs.value.count
                }
                return lhs.key > rhs.key
            }?
            .key

        return HomeLastTripSummary(
            catchText: catches.isEmpty ? "Skunked" : "\(catches.count) \(catches.count == 1 ? "catch" : "catches")",
            durationText: durationText,
            topSpeciesText: topSpeciesText
        )
    }

    static func suggestedMemoryCard(
        latestCompletedTrip: Trip?,
        summary: SpotRecallSummary?,
        totalCompletedTrips: Int
    ) -> HomeMemoryCard? {
        guard let latestCompletedTrip else {
            return HomeMemoryCard(
                title: "Private memory starts here",
                body: "Each trip you save builds a sharper recall surface for your next outing.",
                footer: "Private by default"
            )
        }

        guard let summary, let spot = latestCompletedTrip.spot else {
            return HomeMemoryCard(
                title: "Keep your next trip easy to recall",
                body: totalCompletedTrips < 2
                    ? "Log a couple more trips and this home screen will start surfacing what worked."
                    : "Your recent trips are saved privately and ready when you want to look back before the next run.",
                footer: "Saved privately"
            )
        }

        if let bestTimeWindow = summary.bestTimeWindow {
            return HomeMemoryCard(
                title: "Before your next stop at \(spot.title)",
                body: "\(bestTimeWindow) has been your strongest window there so far.",
                footer: "Based on \(summary.bestTimeWindowSupportCount) logged catches"
            )
        }

        if let lure = summary.mostEffectiveLure {
            return HomeMemoryCard(
                title: "Private memory from \(spot.title)",
                body: "\(lure) has shown up most often in your catches there.",
                footer: "Based on \(summary.mostEffectiveLureSupportCount) catches"
            )
        }

        return HomeMemoryCard(
            title: "Private memory from \(spot.title)",
            body: "You have \(summary.tripCount) trips and \(summary.catchCount) catches saved there already.",
            footer: "Your spots stay yours"
        )
    }

    static func lastTimeHereCard(
        trip: Trip?,
        catches: [CatchRecord],
        calendar: Calendar = .current
    ) -> HomeReplayCard? {
        guard let trip, let spot = trip.spot else { return nil }

        let recap = TripPresentationLogic.tripMemoryRecap(
            trip: trip,
            catches: catches,
            calendar: calendar
        )
        return HomeReplayCard(
            title: "Last time at \(spot.title)",
            body: recap.primaryLine,
            footer: recap.secondaryLine ?? "Saved privately for your next pass here"
        )
    }

    // MARK: - Seasonal Memory Nudges & Personal-Best Story Moments

    static func seasonalNudgeCards(
        trips: [Trip],
        catches: [CatchRecord],
        personalBests: [PersonalBest],
        now: Date = .now,
        calendar: Calendar = .current
    ) -> [HomeSeasonalCard] {
        let completedTrips = trips.filter { !$0.isActive }
        guard !completedTrips.isEmpty else { return [] }

        let currentMonth = calendar.component(.month, from: now)
        let currentSeason = TripHistoryLogic.season(for: now, calendar: calendar)
        let catchesByTripID = Dictionary(grouping: catches) { $0.trip?.id }

        var candidates: [HomeSeasonalCard] = []

        // 1. PB anniversary nudge — any personal best set within ±7 days of today in a prior year
        candidates.append(contentsOf: pbAnniversaryCards(
            personalBests: personalBests,
            catches: catches,
            trips: completedTrips,
            now: now,
            calendar: calendar
        ))

        // 2. Same-month-last-year nudge — productive trip at any spot in same month of prior year
        candidates.append(contentsOf: sameMonthLastYearCards(
            trips: completedTrips,
            catchesByTripID: catchesByTripID,
            currentMonth: currentMonth,
            now: now,
            calendar: calendar
        ))

        // 3. Seasonal spot nudge — current season matches historically strong season at a spot (≥3 productive trips)
        candidates.append(contentsOf: seasonalSpotCards(
            trips: completedTrips,
            catchesByTripID: catchesByTripID,
            currentSeason: currentSeason,
            calendar: calendar
        ))

        // 4. Generic seasonal nudge — current month is historically productive across all spots (≥3 productive trips)
        candidates.append(contentsOf: genericSeasonalCards(
            trips: completedTrips,
            catchesByTripID: catchesByTripID,
            currentMonth: currentMonth,
            calendar: calendar
        ))

        // Sort by priority (Kind is Comparable — lower ordinal = higher priority), take at most 2
        return Array(candidates.sorted { $0.kind < $1.kind }.prefix(2))
    }

    // MARK: - Private Seasonal Helpers

    private static func pbAnniversaryCards(
        personalBests: [PersonalBest],
        catches: [CatchRecord],
        trips: [Trip],
        now: Date,
        calendar: Calendar
    ) -> [HomeSeasonalCard] {
        let currentYear = calendar.component(.year, from: now)
        let catchByID = Dictionary(uniqueKeysWithValues: catches.compactMap { ($0.id, $0) })
        let tripByID = Dictionary(uniqueKeysWithValues: trips.map { ($0.id, $0) })

        var cards: [HomeSeasonalCard] = []

        for pb in personalBests {
            let candidateCatchIDs = [pb.longestCatchID, pb.heaviestCatchID].compactMap { $0 }
            for catchID in candidateCatchIDs {
                guard let catchRecord = catchByID[catchID] else { continue }
                let catchYear = calendar.component(.year, from: catchRecord.caughtAt)
                guard catchYear < currentYear else { continue }

                // Build the anniversary date in the current year
                guard let anniversaryDate = calendar.date(
                    from: {
                        var comps = calendar.dateComponents([.month, .day], from: catchRecord.caughtAt)
                        comps.year = currentYear
                        return comps
                    }()
                ) else { continue }

                let dayDiff = abs(calendar.dateComponents([.day], from: anniversaryDate, to: now).day ?? Int.max)
                guard dayDiff <= 7 else { continue }

                let yearsAgo = currentYear - catchYear
                let yearsLabel = yearsAgo == 1 ? "One year ago" : "\(yearsAgo) years ago"
                let spotTitle = catchRecord.trip.flatMap { tripByID[$0.id] }?.spot?.title

                let isLongest = pb.longestCatchID == catchID
                if isLongest, let length = pb.longestLengthCm {
                    let spotSuffix = spotTitle.map { " at \($0)" } ?? ""
                    cards.append(HomeSeasonalCard(
                        id: "pb-longest-\(pb.species)-\(catchYear)",
                        kind: .pbAnniversary,
                        title: "\(yearsLabel) today",
                        body: "You set your longest \(pb.species) record — \(length.formatted()) cm\(spotSuffix).",
                        footer: "Personal best anniversary"
                    ))
                } else if let weight = pb.heaviestWeightKg {
                    let spotSuffix = spotTitle.map { " at \($0)" } ?? ""
                    cards.append(HomeSeasonalCard(
                        id: "pb-heaviest-\(pb.species)-\(catchYear)",
                        kind: .pbAnniversary,
                        title: "\(yearsLabel) today",
                        body: "You set your heaviest \(pb.species) record — \(weight.formatted()) kg\(spotSuffix).",
                        footer: "Personal best anniversary"
                    ))
                }
            }
        }

        return cards
    }

    private static func sameMonthLastYearCards(
        trips: [Trip],
        catchesByTripID: [UUID?: [CatchRecord]],
        currentMonth: Int,
        now: Date,
        calendar: Calendar
    ) -> [HomeSeasonalCard] {
        let currentYear = calendar.component(.year, from: now)

        // Find trips from the same month in the prior year with ≥1 catch
        let qualifying = trips.filter { trip in
            let tripMonth = calendar.component(.month, from: trip.startAt)
            let tripYear = calendar.component(.year, from: trip.startAt)
            guard tripMonth == currentMonth, tripYear == currentYear - 1 else { return false }
            let tripCatches = catchesByTripID[Optional(trip.id), default: []]
            return !tripCatches.isEmpty
        }

        guard let best = qualifying.max(by: { lhs, rhs in
            let lhsCount = catchesByTripID[Optional(lhs.id), default: []].count
            let rhsCount = catchesByTripID[Optional(rhs.id), default: []].count
            return lhsCount < rhsCount
        }) else { return [] }

        let catchCount = catchesByTripID[Optional(best.id), default: []].count
        let spotName = best.spot?.title ?? best.waterbody?.name ?? "a spot"

        return [HomeSeasonalCard(
            id: "same-month-\(best.id)",
            kind: .sameMonthLastYear,
            title: "This time last year",
            body: "You were fishing \(spotName) and caught \(catchCount) \(catchCount == 1 ? "fish" : "fish").",
            footer: AppFormatters.tripDate.string(from: best.startAt)
        )]
    }

    private static func seasonalSpotCards(
        trips: [Trip],
        catchesByTripID: [UUID?: [CatchRecord]],
        currentSeason: TripSeasonFilter,
        calendar: Calendar
    ) -> [HomeSeasonalCard] {
        guard currentSeason != .all else { return [] }

        // Group productive trips by spot and season
        let productiveTrips = trips.filter { trip in
            let tripSeason = TripHistoryLogic.season(for: trip.startAt, calendar: calendar)
            guard tripSeason == currentSeason, trip.spot != nil else { return false }
            return !catchesByTripID[Optional(trip.id), default: []].isEmpty
        }

        let bySpot = Dictionary(grouping: productiveTrips) { $0.spot!.id }

        // Find the spot with the most productive trips in this season (≥3 required)
        guard let (_, spotTrips) = bySpot.max(by: { lhs, rhs in
            if lhs.value.count != rhs.value.count { return lhs.value.count < rhs.value.count }
            return lhs.key.uuidString > rhs.key.uuidString
        }), spotTrips.count >= 3, let spotTitle = spotTrips.first?.spot?.title else { return [] }

        return [HomeSeasonalCard(
            id: "seasonal-spot-\(spotTrips.first!.spot!.id)",
            kind: .seasonalSpot,
            title: "\(currentSeason.label) at \(spotTitle)",
            body: "\(currentSeason.label) has been your strongest season there — \(spotTrips.count) productive trips.",
            footer: "Based on your trip history"
        )]
    }

    private static func genericSeasonalCards(
        trips: [Trip],
        catchesByTripID: [UUID?: [CatchRecord]],
        currentMonth: Int,
        calendar: Calendar
    ) -> [HomeSeasonalCard] {
        // Count productive trips in the current month across all years
        let productiveInMonth = trips.filter { trip in
            let tripMonth = calendar.component(.month, from: trip.startAt)
            guard tripMonth == currentMonth else { return false }
            return !catchesByTripID[Optional(trip.id), default: []].isEmpty
        }

        guard productiveInMonth.count >= 3 else { return [] }

        let monthName = Calendar.current.monthSymbols[currentMonth - 1]

        // Find the spot that appears most often
        let spotCounts = productiveInMonth.compactMap(\.spot).reduce(into: [UUID: (count: Int, title: String)]()) { dict, spot in
            dict[spot.id, default: (0, spot.title)].count += 1
        }
        let topSpot = spotCounts.max { $0.value.count < $1.value.count }

        let body: String
        if let topSpot, topSpot.value.count >= 2 {
            body = "\(monthName) has historically been productive — \(productiveInMonth.count) trips with catches, often at \(topSpot.value.title)."
        } else {
            body = "\(monthName) has historically been productive — \(productiveInMonth.count) trips with catches across your spots."
        }

        return [HomeSeasonalCard(
            id: "generic-seasonal-\(currentMonth)",
            kind: .genericSeasonal,
            title: "\(monthName) looks promising",
            body: body,
            footer: "Based on your trip history"
        )]
    }
}
