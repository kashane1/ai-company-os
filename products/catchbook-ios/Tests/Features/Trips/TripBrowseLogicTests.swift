import CoreLocation
import Foundation
import MapKit
import XCTest
@testable import Catchbook

final class TripBrowseLogicTests: XCTestCase {
    private func utcCalendar() -> Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private func utcDate(year: Int, month: Int, day: Int, hour: Int = 8) -> Date {
        utcCalendar().date(from: DateComponents(year: year, month: month, day: day, hour: hour))!
    }

    func testCalendarDaySummariesGroupsTripsByStartDay() {
        let calendar = utcCalendar()
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let firstTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2026, month: 4, day: 10, hour: 6))
        let secondTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2026, month: 4, day: 10, hour: 15))
        let nextDayTrip = Trip(waterbody: waterbody, startAt: utcDate(year: 2026, month: 4, day: 11))
        let catches = [
            CatchRecord(species: "Bass", trip: firstTrip),
            CatchRecord(species: "Bass", trip: secondTrip),
            CatchRecord(species: "Trout", trip: nextDayTrip),
        ]

        let summaries = TripBrowseLogic.calendarDaySummaries(
            trips: [firstTrip, secondTrip, nextDayTrip],
            catches: catches,
            calendar: calendar
        )

        XCTAssertEqual(summaries.count, 2)
        XCTAssertEqual(summaries[0].tripCount, 1)
        XCTAssertEqual(summaries[0].catchCount, 1)
        XCTAssertEqual(summaries[1].tripCount, 2)
        XCTAssertEqual(summaries[1].catchCount, 2)
        XCTAssertEqual(summaries[1].topSpeciesText, "Bass")
    }

    func testMonthGridPadsLeadingAndTrailingCells() {
        let calendar = utcCalendar()
        let displayedMonth = utcDate(year: 2026, month: 2, day: 1)

        let grid = TripBrowseLogic.monthGrid(
            displayedMonth: displayedMonth,
            daySummaries: [],
            calendar: calendar
        )

        XCTAssertEqual(grid.count, 35)
        XCTAssertEqual(grid.compactMap(\.date).count, 28)
        XCTAssertEqual(calendar.component(.day, from: grid.compactMap(\.date).first!), 1)
    }

    func testCatchGalleryItemsIncludesMultiplePhotosAndLegacyPhotoData() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let trip = Trip(waterbody: waterbody)
        let catchWithGallery = CatchRecord(species: "Bass", trip: trip, caughtAt: utcDate(year: 2026, month: 4, day: 12))
        let photoA = CatchPhoto(catchRecord: catchWithGallery, sortOrder: 0, photoData: Data([0x00, 0x01]))
        let photoB = CatchPhoto(catchRecord: catchWithGallery, sortOrder: 1, photoData: Data([0x00, 0x02]))
        catchWithGallery.photos = [photoB, photoA]

        let legacyCatch = CatchRecord(
            species: "Trout",
            trip: trip,
            caughtAt: utcDate(year: 2026, month: 4, day: 11),
            photoData: Data([0x00, 0x03])
        )

        let items = TripBrowseLogic.catchGalleryItems(catches: [legacyCatch, catchWithGallery])

        XCTAssertEqual(items.count, 3)
        XCTAssertEqual(items[0].catchID, catchWithGallery.id)
        XCTAssertEqual(items[0].photoIndex, 0)
        XCTAssertEqual(items[1].photoIndex, 1)
        XCTAssertEqual(items[2].catchID, legacyCatch.id)
    }

    func testCatchMapMarkersGroupCatchesByTripCoordinate() {
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let spot = Spot(title: "Dock", waterbody: waterbody, latitude: 47.61, longitude: -122.33)
        let trip = Trip(waterbody: waterbody, spot: spot)
        let catches = [
            CatchRecord(species: "Bass", trip: trip),
            CatchRecord(species: "Bass", trip: trip),
            CatchRecord(species: "Perch", trip: trip),
        ]

        let markers = TripBrowseLogic.catchMapMarkers(for: catches)

        XCTAssertEqual(markers.count, 1)
        XCTAssertEqual(markers[0].catchCount, 3)
        XCTAssertEqual(markers[0].confidenceLabel, "Near")
        XCTAssertEqual(markers[0].speciesText, "Bass")
    }

    func testMapRegionFallsBackToProvidedCoordinate() {
        let coordinate = CLLocationCoordinate2D(latitude: 47.61, longitude: -122.33)

        let region = TripBrowseLogic.mapRegion(for: [], fallbackCoordinate: coordinate)

        XCTAssertEqual(region.center.latitude, coordinate.latitude, accuracy: 0.0001)
        XCTAssertEqual(region.center.longitude, coordinate.longitude, accuracy: 0.0001)
        XCTAssertEqual(region.span.latitudeDelta, 0.03, accuracy: 0.0001)
    }
}
