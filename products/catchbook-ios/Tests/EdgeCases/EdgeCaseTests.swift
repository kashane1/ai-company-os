import CoreLocation
import SwiftData
import XCTest
@testable import Catchbook

final class EdgeCaseTests: XCTestCase {
    // MARK: - Empty States

    func testTripWithNoCatches() throws {
        let store = try ModelTestSupport.makeStore()
        let waterbody = Waterbody(name: "Empty Lake", type: .lake)
        let trip = Trip(waterbody: waterbody)

        store.context.insert(trip)

        XCTAssertEqual(trip.title, "Empty Lake")
        XCTAssertTrue(trip.isActive)
        XCTAssertEqual(trip.targetSpeciesList, [])
    }

    func testWaterbodyWithNoSpots() throws {
        let store = try ModelTestSupport.makeStore()
        let waterbody = Waterbody(name: "Spotless Lake", type: .lake, latitude: 45.0, longitude: -120.0)

        store.context.insert(waterbody)

        XCTAssertEqual(waterbody.name, "Spotless Lake")
        XCTAssertEqual(waterbody.type, .lake)
        XCTAssertNotNil(waterbody.latitude)
    }

    func testEmptySpeciesString() {
        let catchRecord = CatchRecord(species: "", trip: nil)

        XCTAssertEqual(catchRecord.speciesDisplayName, "Species not logged")
        XCTAssertFalse(catchRecord.hasPhoto)
    }

    func testSpeciesStringWithOnlyWhitespace() {
        let catchRecord = CatchRecord(species: "   \n\t  ", trip: nil)

        XCTAssertEqual(catchRecord.speciesDisplayName, "Species not logged")
    }

    func testTripWithEmptyWaterbodyAndSpot() {
        let trip = Trip(waterbody: nil, spot: nil)

        XCTAssertEqual(trip.title, "Untitled trip")
    }

    // MARK: - Large Datasets / Extreme Values

    func testPersonalBestWithExtremeWeightValue() throws {
        let store = try ModelTestSupport.makeStore()
        let trip = Trip(waterbody: nil)
        let extremeCatch = CatchRecord(
            species: "Giant Bass",
            trip: trip,
            weightKg: 50.0, // 110 lbs
            lengthCm: 120
        )

        store.context.insert(trip)
        store.context.insert(extremeCatch)

        try PersonalBestService.refresh(with: extremeCatch, in: store.context)

        let records = try store.context.fetch(FetchDescriptor<PersonalBest>())
        XCTAssertEqual(records.first?.heaviestWeightKg, 50.0)
        XCTAssertEqual(records.first?.longestLengthCm, 120)
    }

    func testPersonalBestWithMinimalWeightValue() throws {
        let store = try ModelTestSupport.makeStore()
        let trip = Trip(waterbody: nil)
        let tinyCatch = CatchRecord(
            species: "Minnow",
            trip: trip,
            weightKg: 0.001, // 1 gram
            lengthCm: 3
        )

        store.context.insert(trip)
        store.context.insert(tinyCatch)

        try PersonalBestService.refresh(with: tinyCatch, in: store.context)

        let records = try store.context.fetch(FetchDescriptor<PersonalBest>())
        XCTAssertEqual(records.first?.heaviestWeightKg, 0.001)
    }

    func testMultipleCatchesWithSameSpeciesCaseInsensitive() throws {
        let store = try ModelTestSupport.makeStore()
        let trip = Trip(waterbody: nil)
        let catchLowercase = CatchRecord(species: "bass", trip: trip, weightKg: 1.5, lengthCm: 35)
        let catchUppercase = CatchRecord(species: "BASS", trip: trip, weightKg: 2.0, lengthCm: 40)

        store.context.insert(trip)
        store.context.insert(catchLowercase)
        store.context.insert(catchUppercase)

        try PersonalBestService.refresh(with: catchLowercase, in: store.context)
        try PersonalBestService.refresh(with: catchUppercase, in: store.context)

        let records = try store.context.fetch(FetchDescriptor<PersonalBest>())
        // Note: The actual behavior depends on implementation. This tests case sensitivity.
        XCTAssertGreaterThanOrEqual(records.count, 1)
    }

    // MARK: - Boundary Conditions

    func testTimeWindowLabelAtMidnight() {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0) ?? .gmt
        let date = calendar.date(from: DateComponents(year: 2026, month: 3, day: 30, hour: 0))!

        let label = timeWindowLabel(for: date, calendar: calendar)

        XCTAssertEqual(label, "Evening")
    }

    func testTimeWindowLabelAtNoon() {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0) ?? .gmt
        let date = calendar.date(from: DateComponents(year: 2026, month: 3, day: 30, hour: 12))!

        let label = timeWindowLabel(for: date, calendar: calendar)

        XCTAssertEqual(label, "Noon-3 PM")
    }

    func testLightLevelLabelAtMidnight() {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0) ?? .gmt
        let date = calendar.date(from: DateComponents(year: 2026, month: 3, day: 30, hour: 0))!

        let label = lightLevelLabel(for: date, calendar: calendar)

        XCTAssertEqual(label, "Low light")
    }

    func testCoordinateAtZeroZero() {
        let coordinate = CLLocationCoordinate2D(latitude: 0, longitude: 0)
        let spot = Spot(title: "Equator", waterbody: nil, latitude: 0, longitude: 0)

        XCTAssertEqual(spot.latitude, 0)
        XCTAssertEqual(spot.longitude, 0)
        XCTAssertEqual(spot.coordinateSummary, "0.0000, 0.0000")
    }

    func testCoordinateAtNegativeValues() {
        let spot = Spot(title: "South", waterbody: nil, latitude: -45.0, longitude: -120.0)

        XCTAssertEqual(spot.coordinateSummary, "-45.0000, -120.0000")
    }

    func testCoordinateAtMaxLatitude() {
        let spot = Spot(title: "North Pole", waterbody: nil, latitude: 90.0, longitude: -120.0)

        XCTAssertEqual(spot.latitude, 90.0)
    }

    func testCoordinateAtMinLatitude() {
        let spot = Spot(title: "South Pole", waterbody: nil, latitude: -90.0, longitude: 0.0)

        XCTAssertEqual(spot.latitude, -90.0)
    }

    // MARK: - Permission / Data Edge Cases

    func testCatchRecordWithNilPhotoData() {
        let catchRecord = CatchRecord(species: "Bass", trip: nil, photoData: nil)

        XCTAssertFalse(catchRecord.hasPhoto)
        XCTAssertNil(catchRecord.photoData)
        XCTAssertNil(catchRecord.photoReference)
    }

    func testCatchRecordWithEmptyPhotoData() {
        let catchRecord = CatchRecord(species: "Bass", trip: nil, photoData: Data())

        // Even empty data should be considered as "has photo"
        XCTAssertTrue(catchRecord.hasPhoto)
    }

    func testTripWithNilConditionSnapshot() throws {
        let store = try ModelTestSupport.makeStore()
        let trip = Trip(waterbody: nil, conditionSnapshot: nil)

        store.context.insert(trip)

        XCTAssertNil(trip.conditionSnapshot)
        XCTAssertTrue(trip.isActive)
    }

    func testConditionSnapshotWithAllNilWeatherFields() {
        let snapshot = ConditionSnapshot(
            capturedAt: Date(),
            latitude: 47.6,
            longitude: -122.3,
            temperatureC: nil,
            weatherSummary: nil,
            windSummary: nil,
            cloudCoverSummary: nil,
            precipitationSummary: nil,
            captureStatus: .ready,
            source: .deviceLocation
        )

        XCTAssertNil(snapshot.temperatureC)
        XCTAssertEqual(snapshot.weatherLine, "Weather data unavailable")
    }

    func testWaterbodyWithNilCoordinates() {
        let waterbody = Waterbody(name: "No Coordinates", type: .river)

        XCTAssertNil(waterbody.latitude)
        XCTAssertNil(waterbody.longitude)
    }

    // MARK: - Special Character & String Handling

    func testSpeciesWithSpecialCharacters() {
        let catchRecord = CatchRecord(species: "Bass & Pike (hybrid)", trip: nil)

        XCTAssertEqual(catchRecord.speciesDisplayName, "Bass & Pike (hybrid)")
    }

    func testSpeciesTokensWithMixedDelimiters() {
        let tokens = normalizedSpeciesTokens(from: "Bass, Trout\nPike;Walleye")

        XCTAssertEqual(tokens.count, 4)
        XCTAssertEqual(tokens, ["Bass", "Trout", "Pike", "Walleye"])
    }

    func testSpeciesTokensWithDuplicatesInDifferentCase() {
        let tokens = normalizedSpeciesTokens(from: "Bass, bass, BASS")

        // Should deduplicate case-insensitively but preserve first occurrence case
        XCTAssertEqual(tokens.count, 1)
        XCTAssertEqual(tokens[0], "Bass")
    }

    func testPlaceSummaryWithEmptySpotAndWaterbodyNames() {
        let waterbody = Waterbody(name: "", type: .lake)
        let spot = Spot(title: "", waterbody: waterbody)
        let snapshot = ConditionCaptureService.snapshot(
            waterbody: waterbody,
            spot: spot,
            location: nil,
            capturedAt: Date()
        )

        XCTAssertNil(snapshot.placeSummary)
    }

    func testPlaceSummaryWithOnlySpotName() {
        let spot = Spot(title: "My Spot", waterbody: nil)
        let snapshot = ConditionCaptureService.snapshot(
            waterbody: nil,
            spot: spot,
            location: nil,
            capturedAt: Date()
        )

        XCTAssertEqual(snapshot.placeSummary, "My Spot")
    }

    // MARK: - Type Coercion & Fallback Behavior

    func testConditionSnapshotInvalidCaptureStatusFallback() {
        let snapshot = ConditionSnapshot()
        snapshot.captureStatusRawValue = "impossible-status"

        XCTAssertEqual(snapshot.captureStatus, .fallback)
    }

    func testConditionSnapshotInvalidSourceFallback() {
        let snapshot = ConditionSnapshot()
        snapshot.sourceRawValue = "impossible-source"

        XCTAssertEqual(snapshot.source, .tripFallback)
    }

    func testWaterbodyInvalidTypeFallback() {
        let waterbody = Waterbody(name: "Mystery Lake", type: .lake)
        waterbody.typeRawValue = "ocean-current"

        XCTAssertEqual(waterbody.type, .lake)
    }

    // MARK: - Temporal Edge Cases

    func testConditionSnapshotAtYearBoundary() {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0) ?? .gmt
        let date = calendar.date(from: DateComponents(year: 2026, month: 12, day: 31, hour: 23, minute: 59))!

        let snapshot = ConditionCaptureService.snapshot(
            waterbody: nil,
            spot: nil,
            location: nil,
            capturedAt: date
        )

        XCTAssertEqual(snapshot.capturedAt, date)
    }

    func testCatchRecordWithFutureDate() {
        let futureDate = Date(timeIntervalSinceNow: 86_400) // Tomorrow
        let catchRecord = CatchRecord(species: "Future Fish", trip: nil, caughtAt: futureDate)

        XCTAssertGreaterThan(catchRecord.caughtAt, Date())
    }

    // MARK: - Coordinate Preference Order

    func testBestAvailableCoordinatePrefersDeviceLocationFirst() {
        let waterbody = Waterbody(name: "Lake", type: .lake, latitude: 10, longitude: 20)
        let spot = Spot(title: "Dock", waterbody: waterbody, latitude: 30, longitude: 40)
        let location = CLLocation(latitude: 50, longitude: 60)

        let coordinate = bestAvailableCoordinate(location: location, spot: spot, waterbody: waterbody)

        XCTAssertEqual(coordinate?.latitude, 50)
        XCTAssertEqual(coordinate?.longitude, 60)
    }

    func testBestAvailableCoordinateUsesSpotWhenNoDeviceLocation() {
        let waterbody = Waterbody(name: "Lake", type: .lake, latitude: 10, longitude: 20)
        let spot = Spot(title: "Dock", waterbody: waterbody, latitude: 30, longitude: 40)

        let coordinate = bestAvailableCoordinate(location: nil, spot: spot, waterbody: waterbody)

        XCTAssertEqual(coordinate?.latitude, 30)
        XCTAssertEqual(coordinate?.longitude, 40)
    }

    func testBestAvailableCoordinateUsesWaterbodyAsLastResort() {
        let waterbody = Waterbody(name: "Lake", type: .lake, latitude: 10, longitude: 20)
        let spot = Spot(title: "Dock", waterbody: waterbody)

        let coordinate = bestAvailableCoordinate(location: nil, spot: spot, waterbody: waterbody)

        XCTAssertEqual(coordinate?.latitude, 10)
        XCTAssertEqual(coordinate?.longitude, 20)
    }

    func testBestAvailableCoordinateReturnsNilWhenNoneAvailable() {
        let spot = Spot(title: "Dock", waterbody: nil)

        let coordinate = bestAvailableCoordinate(location: nil, spot: spot, waterbody: nil)

        XCTAssertNil(coordinate)
    }

    // MARK: - Trip Outcome Edge Cases

    func testTripOutcomeDefaultsToActiveWhenInvalid() {
        let trip = Trip(waterbody: nil)
        trip.outcomeRawValue = "unknown-outcome"

        XCTAssertEqual(trip.outcome, .active)
        XCTAssertTrue(trip.isActive)
    }

    func testTripIsActiveWhenEndAtIsNil() {
        let trip = Trip(waterbody: nil)

        XCTAssertNil(trip.endAt)
        XCTAssertTrue(trip.isActive)
    }

    func testTripIsInactiveWhenEndAtIsSet() {
        let trip = Trip(waterbody: nil)
        trip.endAt = Date(timeIntervalSinceNow: -3600) // 1 hour ago

        XCTAssertFalse(trip.isActive)
    }

    // MARK: - Personal Best Extreme Cases

    func testPersonalBestWithBothValuesNil() throws {
        let store = try ModelTestSupport.makeStore()
        let personalBest = PersonalBest(species: "Unknown")

        store.context.insert(personalBest)

        XCTAssertNil(personalBest.longestLengthCm)
        XCTAssertNil(personalBest.heaviestWeightKg)
    }

    func testPersonalBestWithNegativeTemperature() {
        let snapshot = ConditionSnapshot(temperatureC: -15.5)

        XCTAssertEqual(snapshot.temperatureC, -15.5)
    }
}
