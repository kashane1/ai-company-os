import Foundation

struct SpotRecallSummary {
    let recentTrips: [Trip]
    let catchCount: Int
    let bestTimeWindow: String?
    let mostEffectiveLure: String?

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

        return SpotRecallSummary(
            recentTrips: Array(spotTrips.prefix(3)),
            catchCount: spotCatches.count,
            bestTimeWindow: timeWindowCounts.max(by: { $0.value < $1.value })?.key,
            mostEffectiveLure: lureCounts.max(by: { $0.value < $1.value })?.key
        )
    }
}
