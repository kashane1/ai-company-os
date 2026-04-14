import XCTest
@testable import Catchbook

final class AppTabTests: XCTestCase {
    func testAllFourCasesExist() {
        let cases: [AppTab] = [.home, .spots, .trips, .more]
        XCTAssertEqual(cases.count, 4)
    }

    func testHomeTabCaseExists() {
        let tab = AppTab.home
        XCTAssertNotNil(tab)
    }

    func testTripsTabCaseExists() {
        let tab = AppTab.trips
        XCTAssertNotNil(tab)
    }

    func testSpotsTabCaseExists() {
        let tab = AppTab.spots
        XCTAssertNotNil(tab)
    }

    func testMoreTabCaseExists() {
        let tab = AppTab.more
        XCTAssertNotNil(tab)
    }

    func testTabHashableConformanceWithSet() {
        let tabSet: Set<AppTab> = [.home, .spots, .trips, .more]
        XCTAssertEqual(tabSet.count, 4)
    }

    func testTabHashableConformanceInsertingDuplicates() {
        var tabSet: Set<AppTab> = [.home, .trips]
        tabSet.insert(.home)
        XCTAssertEqual(tabSet.count, 2, "Inserting duplicate should not increase Set count")
    }

    func testTabHashableConformanceAllCasesInSet() {
        let allTabs: Set<AppTab> = [.home, .spots, .trips, .more]
        XCTAssertTrue(allTabs.contains(.home))
        XCTAssertTrue(allTabs.contains(.spots))
        XCTAssertTrue(allTabs.contains(.trips))
        XCTAssertTrue(allTabs.contains(.more))
    }

    func testTabEquality() {
        XCTAssertEqual(AppTab.home, AppTab.home)
        XCTAssertEqual(AppTab.trips, AppTab.trips)
        XCTAssertEqual(AppTab.spots, AppTab.spots)
        XCTAssertEqual(AppTab.more, AppTab.more)
    }

    func testTabInequality() {
        XCTAssertNotEqual(AppTab.home, AppTab.trips)
        XCTAssertNotEqual(AppTab.trips, AppTab.more)
        XCTAssertNotEqual(AppTab.more, AppTab.spots)
        XCTAssertNotEqual(AppTab.spots, AppTab.home)
    }

    func testTabCanBeUsedInArray() {
        let tabs: [AppTab] = [.home, .spots, .trips, .more]
        XCTAssertEqual(tabs.count, 4)
        XCTAssertEqual(tabs[0], .home)
        XCTAssertEqual(tabs[3], .more)
    }

    func testTabCanBeUsedInDictionary() {
        var tabNames: [AppTab: String] = [:]
        tabNames[.home] = "Home"
        tabNames[.spots] = "Spots"
        tabNames[.trips] = "Trips"
        tabNames[.more] = "More"

        XCTAssertEqual(tabNames[.home], "Home")
        XCTAssertEqual(tabNames[.spots], "Spots")
        XCTAssertEqual(tabNames[.trips], "Trips")
        XCTAssertEqual(tabNames[.more], "More")
    }
}
