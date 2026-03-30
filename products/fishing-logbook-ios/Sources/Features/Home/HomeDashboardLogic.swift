import Foundation

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
}
