import XCTest
@testable import Fishing_Logbook

final class HomeDashboardLogicTests: XCTestCase {
    func testActiveTripSelectsFirstActiveTrip() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let completedTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 100))
        completedTrip.endAt = Date(timeIntervalSince1970: 200)
        let activeTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 300))

        let selected = HomeDashboardLogic.activeTrip(from: [completedTrip, activeTrip])

        XCTAssertEqual(selected?.id, activeTrip.id)
    }

    func testLatestCompletedTripIgnoresActiveTrips() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let latestCompletedTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 300))
        latestCompletedTrip.endAt = Date(timeIntervalSince1970: 400)
        let activeTrip = Trip(waterbody: waterbody, startAt: Date(timeIntervalSince1970: 500))

        let selected = HomeDashboardLogic.latestCompletedTrip(from: [activeTrip, latestCompletedTrip])

        XCTAssertEqual(selected?.id, latestCompletedTrip.id)
    }

    func testCompletedTripCountExcludesActiveTrips() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let completedTripA = Trip(waterbody: waterbody)
        completedTripA.endAt = Date(timeIntervalSince1970: 10)
        let completedTripB = Trip(waterbody: waterbody)
        completedTripB.endAt = Date(timeIntervalSince1970: 20)
        let activeTrip = Trip(waterbody: waterbody)

        XCTAssertEqual(
            HomeDashboardLogic.completedTripCount(from: [completedTripA, activeTrip, completedTripB]),
            2
        )
    }

    func testCatchCountCountsOnlyMatchingTrip() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let trip = Trip(waterbody: waterbody)
        let otherTrip = Trip(waterbody: waterbody)
        let catches = [
            CatchRecord(species: "Bass", trip: trip),
            CatchRecord(species: "Bass", trip: trip),
            CatchRecord(species: "Trout", trip: otherTrip),
            CatchRecord(species: "Perch", trip: nil),
        ]

        XCTAssertEqual(HomeDashboardLogic.catchCount(for: trip.id, catches: catches), 2)
    }

    func testShouldShowRecallRequiresCompletedTripSpotAndCards() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let completedTripWithoutSpot = Trip(waterbody: waterbody)
        completedTripWithoutSpot.endAt = Date(timeIntervalSince1970: 20)
        let completedTripWithSpot = Trip(waterbody: waterbody, spot: spot)
        completedTripWithSpot.endAt = Date(timeIntervalSince1970: 30)
        let emptySummary = SpotRecallSummary(
            recentTrips: [],
            catchCount: 0,
            successfulTripCount: 0,
            bestTimeWindow: nil,
            mostEffectiveLure: nil,
            seasonalityInsight: nil,
            similarConditionsCount: 0,
            similarConditionsLabel: nil
        )
        let populatedSummary = SpotRecallSummary(
            recentTrips: [completedTripWithSpot],
            catchCount: 2,
            successfulTripCount: 1,
            bestTimeWindow: "6-9 AM",
            mostEffectiveLure: "Spinner",
            seasonalityInsight: nil,
            similarConditionsCount: 1,
            similarConditionsLabel: "6-9 AM • Morning light"
        )

        XCTAssertFalse(
            HomeDashboardLogic.shouldShowRecall(latestCompletedTrip: nil, summary: populatedSummary)
        )
        XCTAssertFalse(
            HomeDashboardLogic.shouldShowRecall(
                latestCompletedTrip: completedTripWithoutSpot,
                summary: populatedSummary
            )
        )
        XCTAssertFalse(
            HomeDashboardLogic.shouldShowRecall(
                latestCompletedTrip: completedTripWithSpot,
                summary: emptySummary
            )
        )
        XCTAssertTrue(
            HomeDashboardLogic.shouldShowRecall(
                latestCompletedTrip: completedTripWithSpot,
                summary: populatedSummary
            )
        )
    }

    func testPersonalBestLabelUsesSingularAndPlural() {
        XCTAssertEqual(HomeDashboardLogic.personalBestLabel(count: 1), "Best")
        XCTAssertEqual(HomeDashboardLogic.personalBestLabel(count: 2), "Bests")
    }

    func testPersonalBestSummaryTextFormatsPresentValuesOnly() {
        let formatValue: (Double) -> String = { String(format: "%.1f", $0) }

        XCTAssertEqual(
            HomeDashboardLogic.personalBestSummaryText(
                longestLengthCm: 42,
                heaviestWeightKg: nil,
                formatValue: formatValue
            ),
            "42.0 cm"
        )
        XCTAssertEqual(
            HomeDashboardLogic.personalBestSummaryText(
                longestLengthCm: nil,
                heaviestWeightKg: 1.8,
                formatValue: formatValue
            ),
            "1.8 kg"
        )
        XCTAssertEqual(
            HomeDashboardLogic.personalBestSummaryText(
                longestLengthCm: 42,
                heaviestWeightKg: 1.8,
                formatValue: formatValue
            ),
            "42.0 cm · 1.8 kg"
        )
        XCTAssertEqual(
            HomeDashboardLogic.personalBestSummaryText(
                longestLengthCm: nil,
                heaviestWeightKg: nil,
                formatValue: formatValue
            ),
            ""
        )
    }

    func testElapsedTextUsesInjectedNowAndFormatterFallback() {
        let startAt = Date(timeIntervalSince1970: 100)
        let now = Date(timeIntervalSince1970: 220)

        let formatted = HomeDashboardLogic.elapsedText(
            startAt: startAt,
            now: now,
            formatDuration: { duration in
                XCTAssertEqual(duration, 120, accuracy: 0.001)
                return "2m"
            }
        )
        XCTAssertEqual(formatted, "2m")

        let fallback = HomeDashboardLogic.elapsedText(
            startAt: startAt,
            now: now,
            formatDuration: { _ in nil }
        )
        XCTAssertEqual(fallback, "now")
    }
}
