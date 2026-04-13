import CoreLocation
import XCTest
@testable import Catchbook

final class FishingModelsTests: XCTestCase {
    private var utcCalendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0) ?? .gmt
        return calendar
    }

    private func utcDate(hour: Int) -> Date {
        utcCalendar.date(from: DateComponents(year: 2026, month: 3, day: 30, hour: hour))!
    }

    func testWaterbodyTypeFallsBackToLakeForInvalidRawValue() {
        let waterbody = Waterbody(name: "Hidden Lake", type: .river)
        waterbody.typeRawValue = "unknown"

        XCTAssertEqual(waterbody.type, .lake)
    }

    func testWaterbodySubtitleReflectsPrivacy() {
        let privateWaterbody = Waterbody(name: "Hidden Lake", type: .river, isPrivate: true)
        let publicWaterbody = Waterbody(name: "Pier", type: .coastal, isPrivate: false)

        XCTAssertEqual(privateWaterbody.subtitle, "River • Private")
        XCTAssertEqual(publicWaterbody.subtitle, "Coastal")
    }

    func testSpotCoordinateSummaryFormatsCoordinatesWhenPresent() {
        let spot = Spot(title: "Dock", waterbody: nil, latitude: 47.6205, longitude: -122.3493)

        XCTAssertEqual(spot.coordinateSummary, "47.6205, -122.3493")
    }

    func testSpotCoordinateSummaryFallsBackWhenCoordinatesAreMissing() {
        let spot = Spot(title: "Dock", waterbody: nil)

        XCTAssertEqual(spot.coordinateSummary, "Coordinates not captured yet")
    }

    func testConditionSnapshotFallsBackForInvalidRawValues() {
        let snapshot = ConditionSnapshot()
        snapshot.captureStatusRawValue = "not-valid"
        snapshot.sourceRawValue = "not-valid"
        snapshot.waterClarityRawValue = "not-valid"
        snapshot.moonPhaseRawValue = "not-valid"
        snapshot.tideStateRawValue = "not-valid"

        XCTAssertEqual(snapshot.captureStatus, .fallback)
        XCTAssertEqual(snapshot.source, .tripFallback)
        XCTAssertEqual(snapshot.waterClarity, .notRecorded)
        XCTAssertEqual(snapshot.tideState, .notRecorded)
        XCTAssertEqual(snapshot.moonPhase, moonPhaseValue(for: snapshot.capturedAt))
    }

    func testConditionSnapshotComputedPropertiesStayReadableAndOrdered() {
        let snapshot = ConditionSnapshot(
            capturedAt: utcDate(hour: 6),
            latitude: 47.6205,
            longitude: -122.3493,
            placeSummary: "Dock • Lake",
            timeWindowSummary: "6-9 AM",
            lightLevelSummary: "Morning light",
            temperatureC: 12,
            weatherSummary: "Cloudy",
            windSummary: "5 kt",
            cloudCoverSummary: "Low clouds",
            precipitationSummary: "Dry",
            waterClarity: .clear,
            moonPhase: .fullMoon,
            pressureHPa: 1_013.2,
            tideState: .incoming,
            captureStatus: .ready,
            source: .deviceLocation
        )

        XCTAssertEqual(snapshot.coordinateSummary, "47.6205, -122.3493")
        XCTAssertEqual(snapshot.statusLine, "Conditions captured")
        XCTAssertEqual(snapshot.locationConfidenceLabel, "At")
        XCTAssertEqual(snapshot.locationSummaryLine, "At Dock • Lake · 47.6205, -122.3493")
        XCTAssertEqual(snapshot.weatherLine, "12°C • Cloudy • 5 kt • Low clouds • Dry • 1,013 hPa")
        XCTAssertEqual(snapshot.similarityDescription, "6-9 AM • Morning light • 5 kt • Dry")
        XCTAssertEqual(
            snapshot.displaySummary,
            "Dock • Lake • 6-9 AM • Morning light • 47.6205, -122.3493 • 12°C • Cloudy • 5 kt • Low clouds • Dry • 1,013 hPa"
        )
        XCTAssertEqual(snapshot.claritySummary, "Clear")
        XCTAssertEqual(snapshot.tideSummary, "Incoming")
        XCTAssertEqual(snapshot.moonPhase.label, "Full moon")
    }

    func testConditionSnapshotFallbackStringsHandleEmptyWeatherContext() {
        let snapshot = ConditionSnapshot(captureStatus: .pending, source: .weatherDeferred)

        XCTAssertNil(snapshot.coordinateSummary)
        XCTAssertNil(snapshot.locationConfidenceLabel)
        XCTAssertNil(snapshot.locationSummaryLine)
        XCTAssertEqual(snapshot.statusLine, "Conditions pending")
        XCTAssertEqual(snapshot.weatherLine, "Weather data unavailable")
        XCTAssertEqual(snapshot.similarityDescription, "recent trip context")
        XCTAssertEqual(snapshot.displaySummary, "Weather data unavailable")
    }

    func testConditionSnapshotLocationSummaryUsesNearForFallbackCoordinates() {
        let snapshot = ConditionSnapshot(
            capturedAt: utcDate(hour: 7),
            latitude: 47.5,
            longitude: -122.2,
            placeSummary: "Dock • Lake",
            captureStatus: .fallback,
            source: .spotFallback
        )

        XCTAssertEqual(snapshot.locationConfidenceLabel, "Near")
        XCTAssertEqual(snapshot.locationSummaryLine, "Near Dock • Lake · 47.5000, -122.2000")
    }

    func testTripComputedPropertiesRespectFallbackOrder() {
        let waterbody = Waterbody(name: "Lake Union", type: .lake)
        let spot = Spot(title: "Canal", waterbody: waterbody)
        let trip = Trip(waterbody: waterbody, spot: spot, targetSpecies: "Bass, trout\nBass ; Pike")
        trip.outcomeRawValue = "invalid"

        XCTAssertEqual(trip.outcome, .active)
        XCTAssertTrue(trip.isActive)
        XCTAssertEqual(trip.title, "Canal")
        XCTAssertEqual(trip.targetSpeciesList, ["Bass", "trout", "Pike"])

        trip.spot = nil
        XCTAssertEqual(trip.title, "Lake Union")

        trip.waterbody = nil
        XCTAssertEqual(trip.title, "Untitled trip")

        trip.endAt = utcDate(hour: 12)
        XCTAssertFalse(trip.isActive)
    }

    func testTripResolvedCoordinatePrefersSnapshotThenSpotThenWaterbody() {
        let waterbody = Waterbody(name: "Lake", type: .lake, latitude: 10, longitude: 20)
        let spot = Spot(title: "Dock", waterbody: waterbody, latitude: 30, longitude: 40)
        let snapshot = ConditionSnapshot(latitude: 50, longitude: 60, source: .deviceLocation)
        let trip = Trip(waterbody: waterbody, spot: spot, conditionSnapshot: snapshot)

        XCTAssertEqual(trip.coordinateSource, .observed)
        XCTAssertEqual(trip.locationConfidenceLabel, "At")
        XCTAssertEqual(trip.resolvedCoordinate?.latitude, 50)

        trip.conditionSnapshot = nil
        XCTAssertEqual(trip.coordinateSource, .spotFallback)
        XCTAssertEqual(trip.locationConfidenceLabel, "Near")
        XCTAssertEqual(trip.resolvedCoordinate?.latitude, 30)

        trip.spot = Spot(title: "Dock", waterbody: waterbody)
        XCTAssertEqual(trip.coordinateSource, .waterbodyFallback)
        XCTAssertEqual(trip.resolvedCoordinate?.latitude, 10)

        trip.waterbody = nil
        XCTAssertEqual(trip.coordinateSource, .unresolved)
        XCTAssertNil(trip.resolvedCoordinate)
    }

    func testCatchRecordComputedPropertiesReflectPhotoAndSpeciesFallback() {
        let catchRecord = CatchRecord(species: "   ", trip: nil, photoData: Data([1, 2, 3]))

        XCTAssertTrue(catchRecord.hasPhoto)
        XCTAssertEqual(catchRecord.speciesDisplayName, "Species not logged")
        XCTAssertEqual(catchRecord.disposition, .notRecorded)

        catchRecord.species = "  Bass "
        catchRecord.disposition = .released
        XCTAssertEqual(catchRecord.speciesDisplayName, "Bass")
        XCTAssertEqual(catchRecord.disposition.label, "Released")
    }

    func testTripDurationIntervalReturnsPositiveEndedDurationOnly() {
        let trip = Trip(waterbody: Waterbody(name: "Lake", type: .lake), startAt: utcDate(hour: 6))
        XCTAssertNil(trip.durationInterval)

        trip.endAt = utcDate(hour: 8)
        XCTAssertEqual(trip.durationInterval, 7_200)

        trip.endAt = utcDate(hour: 5)
        XCTAssertNil(trip.durationInterval)
    }

    func testMoonPhaseReturnsExpectedSeasonalPhases() {
        XCTAssertEqual(
            moonPhaseValue(for: utcCalendar.date(from: DateComponents(year: 2025, month: 3, day: 14, hour: 6))!, calendar: utcCalendar),
            .fullMoon
        )
        XCTAssertEqual(
            moonPhaseValue(for: utcCalendar.date(from: DateComponents(year: 2025, month: 3, day: 29, hour: 10))!, calendar: utcCalendar),
            .newMoon
        )
    }

    func testTimeWindowLabelUsesProvidedCalendarAtBoundaryHours() {
        XCTAssertEqual(timeWindowLabel(for: utcDate(hour: 5), calendar: utcCalendar), "6-9 AM")
        XCTAssertEqual(timeWindowLabel(for: utcDate(hour: 9), calendar: utcCalendar), "9 AM-Noon")
        XCTAssertEqual(timeWindowLabel(for: utcDate(hour: 12), calendar: utcCalendar), "Noon-3 PM")
        XCTAssertEqual(timeWindowLabel(for: utcDate(hour: 15), calendar: utcCalendar), "3-7 PM")
        XCTAssertEqual(timeWindowLabel(for: utcDate(hour: 21), calendar: utcCalendar), "Evening")
    }

    func testLightLevelLabelUsesProvidedCalendarAtBoundaryHours() {
        XCTAssertEqual(lightLevelLabel(for: utcDate(hour: 4), calendar: utcCalendar), "First light")
        XCTAssertEqual(lightLevelLabel(for: utcDate(hour: 6), calendar: utcCalendar), "Morning light")
        XCTAssertEqual(lightLevelLabel(for: utcDate(hour: 11), calendar: utcCalendar), "Midday light")
        XCTAssertEqual(lightLevelLabel(for: utcDate(hour: 16), calendar: utcCalendar), "Evening light")
        XCTAssertEqual(lightLevelLabel(for: utcDate(hour: 22), calendar: utcCalendar), "Low light")
    }

    func testBestAvailableCoordinatePrefersDeviceThenSpotThenWaterbody() {
        let waterbody = Waterbody(name: "Lake", type: .lake, latitude: 10, longitude: 20)
        let spot = Spot(title: "Dock", waterbody: waterbody, latitude: 30, longitude: 40)
        let location = CLLocation(latitude: 50, longitude: 60)

        XCTAssertEqual(bestAvailableCoordinate(location: location, spot: spot, waterbody: waterbody)?.latitude, 50)
        XCTAssertEqual(bestAvailableCoordinate(location: nil, spot: spot, waterbody: waterbody)?.latitude, 30)
        XCTAssertEqual(
            bestAvailableCoordinate(location: nil, spot: Spot(title: "Dock", waterbody: waterbody), waterbody: waterbody)?.latitude,
            10
        )
        XCTAssertNil(bestAvailableCoordinate(location: nil, spot: Spot(title: "Dock", waterbody: nil), waterbody: nil))
    }

    func testBestAvailableConditionSourceTracksSelectedFallbackLayer() {
        let waterbody = Waterbody(name: "Lake", type: .lake, latitude: 10, longitude: 20)
        let spot = Spot(title: "Dock", waterbody: waterbody, latitude: 30, longitude: 40)
        let location = CLLocation(latitude: 50, longitude: 60)

        XCTAssertEqual(bestAvailableConditionSource(location: location, spot: spot, waterbody: waterbody), .deviceLocation)
        XCTAssertEqual(bestAvailableConditionSource(location: nil, spot: spot, waterbody: waterbody), .spotFallback)
        XCTAssertEqual(
            bestAvailableConditionSource(location: nil, spot: Spot(title: "Dock", waterbody: waterbody), waterbody: waterbody),
            .waterbodyFallback
        )
        XCTAssertEqual(
            bestAvailableConditionSource(location: nil, spot: Spot(title: "Dock", waterbody: nil), waterbody: nil),
            .tripFallback
        )
    }

    func testNormalizedSpeciesTokensTrimsFiltersAndDeduplicatesCaseInsensitively() {
        XCTAssertEqual(
            normalizedSpeciesTokens(from: "Bass, trout\nBass ; Pike ; trout ;  "),
            ["Bass", "trout", "Pike"]
        )
    }
}
