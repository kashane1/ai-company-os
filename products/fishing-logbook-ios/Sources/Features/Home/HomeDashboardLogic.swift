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

enum HomeDashboardLogic {
    static func activeTrip(from trips: [Trip]) -> Trip? {
        trips.first(where: \.isActive)
    }

    static func latestCompletedTrip(from trips: [Trip]) -> Trip? {
        trips.first(where: { !$0.isActive })
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
}
