import XCTest
@testable import Catchbook

final class AppTabTests: XCTestCase {
    func testAllFourCasesExist() {
        let cases: [AppTab] = [.home, .trips, .log, .spots]
        XCTAssertEqual(cases.count, 4)
    }

    func testHomeTabCaseExists() {
        let tab = AppTab.home
        // Verify case is constructible
        XCTAssertNotNil(tab)
    }

    func testTripsTabCaseExists() {
        let tab = AppTab.trips
        XCTAssertNotNil(tab)
    }

    func testLogTabCaseExists() {
        let tab = AppTab.log
        XCTAssertNotNil(tab)
    }

    func testSpotsTabCaseExists() {
        let tab = AppTab.spots
        XCTAssertNotNil(tab)
    }

    func testTabHashableConformanceWithSet() {
        let tabSet: Set<AppTab> = [.home, .trips, .log, .spots]
        XCTAssertEqual(tabSet.count, 4)
    }

    func testTabHashableConformanceInsertingDuplicates() {
        var tabSet: Set<AppTab> = [.home, .trips]
        tabSet.insert(.home)
        XCTAssertEqual(tabSet.count, 2, "Inserting duplicate should not increase Set count")
    }

    func testTabHashableConformanceAllCasesInSet() {
        let allTabs: Set<AppTab> = [.home, .trips, .log, .spots]
        XCTAssertTrue(allTabs.contains(.home))
        XCTAssertTrue(allTabs.contains(.trips))
        XCTAssertTrue(allTabs.contains(.log))
        XCTAssertTrue(allTabs.contains(.spots))
    }

    func testTabEquality() {
        XCTAssertEqual(AppTab.home, AppTab.home)
        XCTAssertEqual(AppTab.trips, AppTab.trips)
        XCTAssertEqual(AppTab.log, AppTab.log)
        XCTAssertEqual(AppTab.spots, AppTab.spots)
    }

    func testTabInequality() {
        XCTAssertNotEqual(AppTab.home, AppTab.trips)
        XCTAssertNotEqual(AppTab.trips, AppTab.log)
        XCTAssertNotEqual(AppTab.log, AppTab.spots)
        XCTAssertNotEqual(AppTab.spots, AppTab.home)
    }

    func testTabCanBeUsedInArray() {
        let tabs: [AppTab] = [.home, .trips, .log, .spots]
        XCTAssertEqual(tabs.count, 4)
        XCTAssertEqual(tabs[0], .home)
        XCTAssertEqual(tabs[3], .spots)
    }

    func testTabCanBeUsedInDictionary() {
        var tabNames: [AppTab: String] = [:]
        tabNames[.home] = "Home"
        tabNames[.trips] = "Trips"
        tabNames[.log] = "Log"
        tabNames[.spots] = "Spots"

        XCTAssertEqual(tabNames[.home], "Home")
        XCTAssertEqual(tabNames[.trips], "Trips")
        XCTAssertEqual(tabNames[.log], "Log")
        XCTAssertEqual(tabNames[.spots], "Spots")
    }
}
