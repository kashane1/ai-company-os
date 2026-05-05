import XCTest
@testable import LifeClock

final class MorningWakeTests: XCTestCase {
    private var defaults: UserDefaults!
    private let suiteName = "MorningWakeTests.suite"

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: suiteName)
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        super.tearDown()
    }

    func test_shouldWake_isTrueOnFirstCallEachDay() {
        let day1 = Date(timeIntervalSince1970: 1_800_000_000)
        XCTAssertTrue(MorningWake.shouldWake(now: day1, defaults: defaults))
    }

    func test_mark_makesShouldWakeFalseSameDay() {
        let day1 = Date(timeIntervalSince1970: 1_800_000_000)
        MorningWake.mark(now: day1, defaults: defaults)
        XCTAssertFalse(MorningWake.shouldWake(now: day1, defaults: defaults))
    }

    func test_shouldWake_isTrueAgainOnNextDay() {
        let day1 = Date(timeIntervalSince1970: 1_800_000_000)
        let day2 = day1.addingTimeInterval(60 * 60 * 24)
        MorningWake.mark(now: day1, defaults: defaults)
        XCTAssertTrue(MorningWake.shouldWake(now: day2, defaults: defaults))
    }

    func test_reset_clearsStoredKey() {
        let day1 = Date(timeIntervalSince1970: 1_800_000_000)
        MorningWake.mark(now: day1, defaults: defaults)
        MorningWake.reset(defaults: defaults)
        XCTAssertTrue(MorningWake.shouldWake(now: day1, defaults: defaults))
    }
}
