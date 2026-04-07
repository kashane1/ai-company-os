import Foundation
import SwiftUI
import XCTest
@testable import Fishing_Logbook

final class TripPresentationLogicTests: XCTestCase {
    private func utcCalendar() -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private func utcDate(year: Int, month: Int, day: Int, hour: Int, minute: Int = 0) -> Date {
        utcCalendar().date(from: DateComponents(year: year, month: month, day: day, hour: hour, minute: minute))!
    }

    private func formatter() -> DateComponentsFormatter {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = [.hour, .minute]
        formatter.unitsStyle = .abbreviated
        return formatter
    }

    func testTripRowSummaryReflectsActiveAndSkunkedStates() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let spot = Spot(title: "Dock", waterbody: waterbody)
        let activeTrip = Trip(waterbody: waterbody, spot: spot, startAt: Date(timeIntervalSince1970: 100))
        let completedTrip = Trip(waterbody: waterbody, spot: spot, startAt: Date(timeIntervalSince1970: 100))
        completedTrip.endAt = Date(timeIntervalSince1970: 4_300)

        let activeSummary = TripPresentationLogic.tripRowSummary(
            trip: activeTrip,
            catchCount: 2,
            durationFormatter: formatter()
        )
        let skunkedSummary = TripPresentationLogic.tripRowSummary(
            trip: completedTrip,
            catchCount: 0,
            durationFormatter: formatter()
        )

        XCTAssertEqual(activeSummary.catchCountText, "2")
        XCTAssertFalse(activeSummary.showsSkunkedStyle)
        XCTAssertNil(activeSummary.durationText)
        XCTAssertEqual(activeSummary.spotTitle, "Dock")

        XCTAssertEqual(skunkedSummary.catchCountText, "Skunked")
        XCTAssertTrue(skunkedSummary.showsSkunkedStyle)
        XCTAssertEqual(skunkedSummary.durationText, "1h 10m")
    }

    func testTopStatsIncludeDurationAndTargetSpeciesOnlyWhenPresent() {
        let withExtras = TripPresentationLogic.topStats(
            catchCount: 3,
            durationText: "2h 15m",
            targetSpeciesCount: 2
        )
        let basic = TripPresentationLogic.topStats(
            catchCount: 1,
            durationText: nil,
            targetSpeciesCount: 0
        )

        XCTAssertEqual(withExtras.map(\.id), ["catches", "duration", "targets"])
        XCTAssertEqual(withExtras.map(\.label), ["Catches", "Duration", "Targets"])
        XCTAssertEqual(withExtras.map(\.value), ["3", "2h 15m", "2"])

        XCTAssertEqual(basic.map(\.id), ["catches"])
        XCTAssertEqual(basic.first?.label, "Catch")
        XCTAssertEqual(basic.first?.value, "1")
    }

    func testTripMemoryRecapHighlightsCatchOutcomeSpeciesLureAndWindow() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let trip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 1, day: 3, hour: 6))
        trip.endAt = utcDate(year: 2025, month: 1, day: 3, hour: 8)
        let catches = [
            CatchRecord(species: "Bass", trip: trip, caughtAt: utcDate(year: 2025, month: 1, day: 3, hour: 6, minute: 10), lureOrBait: "Spinner"),
            CatchRecord(species: "Bass", trip: trip, caughtAt: utcDate(year: 2025, month: 1, day: 3, hour: 6, minute: 20), lureOrBait: "Spinner"),
            CatchRecord(species: "Trout", trip: trip, caughtAt: utcDate(year: 2025, month: 1, day: 3, hour: 6, minute: 30), lureOrBait: "Jig"),
        ]

        let recap = TripPresentationLogic.tripMemoryRecap(
            trip: trip,
            catches: catches,
            calendar: utcCalendar()
        )

        XCTAssertEqual(recap.primaryLine, "3 catches · Top species Bass")
        XCTAssertEqual(recap.secondaryLine, "Top lure Spinner · 6-9 AM")
    }

    func testTripMemoryRecapFallsBackToSkunkedTripWindow() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let trip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 1, day: 3, hour: 6))
        trip.endAt = utcDate(year: 2025, month: 1, day: 3, hour: 7)

        let recap = TripPresentationLogic.tripMemoryRecap(
            trip: trip,
            catches: [],
            calendar: utcCalendar()
        )

        XCTAssertEqual(recap.primaryLine, "Skunked")
        XCTAssertEqual(recap.secondaryLine, "6-9 AM")
    }

    func testTripDetailRecallSummaryUsesTripDataForSpeciesLureBestCatchAndWindow() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let trip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 1, day: 3, hour: 6))
        trip.endAt = utcDate(year: 2025, month: 1, day: 3, hour: 9)
        let catches = [
            CatchRecord(species: "Bass", trip: trip, caughtAt: utcDate(year: 2025, month: 1, day: 3, hour: 6, minute: 15), lureOrBait: "Spinner", weightKg: 2.4, lengthCm: 51),
            CatchRecord(species: "Bass", trip: trip, caughtAt: utcDate(year: 2025, month: 1, day: 3, hour: 6, minute: 40), lureOrBait: "Spinner"),
            CatchRecord(species: "Trout", trip: trip, caughtAt: utcDate(year: 2025, month: 1, day: 3, hour: 9, minute: 15), lureOrBait: "Jig", lengthCm: 40),
        ]

        let summary = TripPresentationLogic.tripDetailRecallSummary(
            trip: trip,
            catches: catches,
            calendar: utcCalendar()
        )

        XCTAssertEqual(summary.headline, "3 catches logged")
        XCTAssertEqual(summary.supportingText, "Bass showed up most often in this trip's catch log.")
        XCTAssertEqual(summary.items.map(\.title), ["Catch outcome", "Top species", "Strongest lure signal", "Best catch", "Time window"])
        XCTAssertEqual(summary.items.first?.value, "Productive")
        XCTAssertEqual(summary.items.first?.evidence, "3 catches logged")
        XCTAssertEqual(summary.items[1].value, "Bass")
        XCTAssertEqual(summary.items[1].evidence, "2 catches")
        XCTAssertEqual(summary.items[2].value, "Spinner")
        XCTAssertEqual(summary.items[2].evidence, "2 catches")
        XCTAssertEqual(summary.items[3].value, "Bass")
        XCTAssertEqual(summary.items[3].evidence, "51 cm · 2.4 kg")
        XCTAssertEqual(summary.items[4].value, "6-9 AM")
        XCTAssertEqual(summary.items[4].evidence, "2 catches")
    }

    func testTripDetailRecallSummaryUsesSkunkFallbacksWithoutBestCatchOrLure() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let trip = Trip(waterbody: waterbody, startAt: utcDate(year: 2025, month: 1, day: 3, hour: 15))
        trip.endAt = utcDate(year: 2025, month: 1, day: 3, hour: 17)

        let summary = TripPresentationLogic.tripDetailRecallSummary(
            trip: trip,
            catches: [],
            calendar: utcCalendar()
        )

        XCTAssertEqual(summary.headline, "Skunked")
        XCTAssertEqual(summary.supportingText, "No catches were logged on this trip.")
        XCTAssertEqual(summary.items.map(\.title), ["Catch outcome", "Time window"])
        XCTAssertEqual(summary.items.first?.value, "Skunked")
        XCTAssertEqual(summary.items.last?.value, "3-7 PM")
        XCTAssertEqual(summary.items.last?.evidence, "From trip timing")
    }

    func testRecentSpotTripSummariesUseSameSpotExcludeCurrentTripAndSortNewestFirst() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let dock = Spot(title: "Dock", waterbody: waterbody)
        let point = Spot(title: "Point", waterbody: waterbody)
        let currentTrip = Trip(waterbody: waterbody, spot: dock, startAt: utcDate(year: 2025, month: 1, day: 10, hour: 6))
        let newestRelated = Trip(waterbody: waterbody, spot: dock, startAt: utcDate(year: 2025, month: 1, day: 9, hour: 6))
        let olderRelated = Trip(waterbody: waterbody, spot: dock, startAt: utcDate(year: 2025, month: 1, day: 7, hour: 6))
        olderRelated.endAt = utcDate(year: 2025, month: 1, day: 7, hour: 8)
        let otherSpot = Trip(waterbody: waterbody, spot: point, startAt: utcDate(year: 2025, month: 1, day: 8, hour: 6))
        let catches = [
            CatchRecord(species: "Bass", trip: newestRelated),
            CatchRecord(species: "Bass", trip: newestRelated),
        ]

        let summaries = TripPresentationLogic.recentSpotTripSummaries(
            currentTrip: currentTrip,
            allTrips: [olderRelated, otherSpot, newestRelated, currentTrip],
            catches: catches,
            limit: 3,
            dateFormatter: {
                let formatter = DateFormatter()
                formatter.timeZone = TimeZone(secondsFromGMT: 0)
                formatter.dateFormat = "yyyy-MM-dd"
                return formatter
            }()
        )

        XCTAssertEqual(summaries.map(\.id), [newestRelated.id, olderRelated.id])
        XCTAssertEqual(summaries.first?.catchText, "2 catches")
        XCTAssertEqual(summaries.last?.catchText, "Skunked")
        XCTAssertTrue(summaries.last?.isSkunked ?? false)
        XCTAssertEqual(summaries.first?.dateText, "2025-01-09")
    }

    func testCatchShareCardContentUsesOnlyApprovedFields() {
        let waterbody = Waterbody(name: "Secret Lake", type: .lake, latitude: 45, longitude: -122)
        let spot = Spot(title: "Hidden Dock", waterbody: waterbody, latitude: 46, longitude: -123)
        let snapshot = ConditionSnapshot(
            capturedAt: Date(timeIntervalSince1970: 1_700_000_000),
            placeSummary: "Hidden Dock • Secret Lake",
            timeWindowSummary: "6-9 AM",
            lightLevelSummary: "Morning light",
            windSummary: "10 kt",
            precipitationSummary: "Dry"
        )
        let trip = Trip(
            waterbody: waterbody,
            spot: spot,
            conditionSnapshot: snapshot,
            targetSpecies: "Bass",
            notes: "Do not expose this cove"
        )
        let catchRecord = CatchRecord(
            species: "Bass",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 1_700_000_000),
            lureOrBait: "Spinner",
            method: "Slow roll",
            weightKg: 2.5,
            lengthCm: 55,
            note: "Near the reeds"
        )

        let content = CatchShareCardLogic.content(for: catchRecord)

        XCTAssertEqual(content.speciesName, "Bass")
        XCTAssertEqual(content.lureOrBaitText, "Spinner")
        XCTAssertEqual(content.weightText, "2.5 kg")
        XCTAssertEqual(content.lengthText, "55 cm")
        XCTAssertFalse(content.dateText.contains(":"))
        XCTAssertTrue(content.dateText.contains("2023"))
    }

    @MainActor
    func testCatchShareCardRendererProducesSafeImageWithoutPhotoOrMetrics() {
        let waterbody = Waterbody(name: "Secret Lake", type: .lake)
        let spot = Spot(title: "Hidden Dock", waterbody: waterbody)
        let trip = Trip(waterbody: waterbody, spot: spot)
        let catchRecord = CatchRecord(
            species: "Trout",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 1_700_000_000),
            lureOrBait: "",
            method: "Twitch",
            note: "Private note"
        )

        let image = CatchShareCardRenderer.renderImage(for: catchRecord, scale: 1)

        XCTAssertNotNil(image)
        XCTAssertGreaterThan(image?.size.width ?? 0, 0)
        XCTAssertGreaterThan(image?.size.height ?? 0, 0)
    }
}
