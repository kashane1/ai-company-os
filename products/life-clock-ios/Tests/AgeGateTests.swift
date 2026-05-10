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

    // MARK: - Onboarding routing

    func testAfterBodyCompAdultGoesToSmoking() {
        let dob = birthDate(year: 1990, month: 1, day: 1)
        let next = OnboardingScreen.afterBodyComp(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .smoking)
    }

    func testAfterBodyCompMinorSkipsToStrength() {
        // 12-year-old — well under any plausible alcohol/tobacco gate.
        let dob = birthDate(year: 2014, month: 6, day: 1)
        let next = OnboardingScreen.afterBodyComp(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .strength)
    }

    func testAfterBodyCompSeventeenSkipsToStrength() {
        // 17, day before 18th birthday — still a minor.
        let dob = birthDate(year: 2009, month: 1, day: 16)
        let next = OnboardingScreen.afterBodyComp(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .strength)
    }

    func testAfterBodyCompExactlyEighteenSeesSmoking() {
        // Exactly 18 on asOf — adult bound is inclusive.
        let dob = birthDate(year: 2009, month: 1, day: 15)
        let next = OnboardingScreen.afterBodyComp(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .smoking)
    }

    func testAfterBodyCompMissingBirthDateSkipsToStrength() {
        // Defensive: nil DOB falls through as skip — suppressing the
        // alcohol/tobacco prompts is the safer default for unknown age.
        let next = OnboardingScreen.afterBodyComp(
            birthDate: nil, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .strength)
    }

    // MARK: - Under-13 block routing
    //
    // Pins the COPPA actual-knowledge + FTC Feb 2026 safe-harbor
    // posture: < 13 → terminal block; >= 13 → proceed. See
    // docs/products/life-clock/09b_AGE_COMPLIANCE.md.

    func testAfterBaselineDOBTwelveYearOldGoesToBlock() {
        // 14 years before 2027-01-15 = 2013-01-15 → exactly 13.
        // 12-year-old DOB is 2014-06-01.
        let dob = birthDate(year: 2014, month: 6, day: 1)
        let next = OnboardingScreen.afterBaselineDOB(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .under13Block)
    }

    func testAfterBaselineDOBExactlyThirteenProceeds() {
        // 13 exactly on the asOf date — at-or-above threshold, so OK.
        let dob = birthDate(year: 2014, month: 1, day: 15)
        let next = OnboardingScreen.afterBaselineDOB(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .baselineSex)
    }

    func testAfterBaselineDOBDayBeforeThirteenthBirthdayBlocks() {
        // Birthday is 2014-01-16, asOf is 2014-01-15 → still 12.
        let dob = birthDate(year: 2014, month: 1, day: 16)
        let next = OnboardingScreen.afterBaselineDOB(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .under13Block)
    }

    func testAfterBaselineDOBSeventeenProceeds() {
        // 17-year-old reaches baselineSex; the smoking/alcohol skip
        // for under-18 fires later at afterBodyComp.
        let dob = birthDate(year: 2009, month: 6, day: 1)
        let next = OnboardingScreen.afterBaselineDOB(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .baselineSex)
    }

    func testAfterBaselineDOBAdultProceeds() {
        let dob = birthDate(year: 1990, month: 1, day: 1)
        let next = OnboardingScreen.afterBaselineDOB(
            birthDate: dob, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .baselineSex)
    }

    func testAfterBaselineDOBMissingBirthDateProceeds() {
        // Defensive: nil DOB falls through to .baselineSex rather than
        // .under13Block. The picker should always populate birthDate;
        // routing to the block screen on missing DOB would surface the
        // block on a state-corruption case rather than on a real
        // under-13 entry.
        let next = OnboardingScreen.afterBaselineDOB(
            birthDate: nil, asOf: asOf, calendar: calendar
        )
        XCTAssertEqual(next, .baselineSex)
    }
}
