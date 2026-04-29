import XCTest
@testable import LifeClock

final class AgeGateTests: XCTestCase {
    private let calendar = Calendar.lifeClockUTC
    // 2027-01-15 in UTC, fixed for determinism.
    private let asOf = Date(timeIntervalSince1970: 1_800_000_000)

    private func birthDate(year: Int, month: Int, day: Int) -> Date {
        calendar.date(from: DateComponents(year: year, month: month, day: day))!
    }

    func testAdultByASignificantMargin() {
        // 1990-01-01 is 37 on 2027-01-15
        let dob = birthDate(year: 1990, month: 1, day: 1)
        XCTAssertTrue(AgeGate.isAdult(birthDate: dob, asOf: asOf, calendar: calendar))
        XCTAssertEqual(AgeGate.ageInYears(birthDate: dob, asOf: asOf, calendar: calendar), 37)
    }

    func testExactly18ButOneDayBeforeBirthdayCounts17() {
        // Birthday is 2009-01-16 (one day after asOf 2027-01-15) → still 17
        let dob = birthDate(year: 2009, month: 1, day: 16)
        XCTAssertFalse(AgeGate.isAdult(birthDate: dob, asOf: asOf, calendar: calendar))
        XCTAssertEqual(AgeGate.ageInYears(birthDate: dob, asOf: asOf, calendar: calendar), 17)
    }

    func testExactly18OnTheBirthday() {
        // 2009-01-15 → 18 exactly on 2027-01-15
        let dob = birthDate(year: 2009, month: 1, day: 15)
        XCTAssertTrue(AgeGate.isAdult(birthDate: dob, asOf: asOf, calendar: calendar))
    }

    func testTeenIsNotAdult() {
        let dob = birthDate(year: 2013, month: 6, day: 1)
        XCTAssertFalse(AgeGate.isAdult(birthDate: dob, asOf: asOf, calendar: calendar))
    }

    func testFutureBirthDateNotAdult() {
        // Pathological input — onboarding picker shouldn't allow this but
        // the helper must handle it without crashing.
        let dob = birthDate(year: 2030, month: 1, day: 1)
        XCTAssertFalse(AgeGate.isAdult(birthDate: dob, asOf: asOf, calendar: calendar))
    }
}
