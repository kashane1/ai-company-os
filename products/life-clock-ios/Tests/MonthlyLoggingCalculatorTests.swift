import XCTest
import SwiftData
@testable import LifeClock

final class MonthlyLoggingCalculatorTests: XCTestCase {
    private var calendar: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "UTC")!
        c.locale = Locale(identifier: "en_US_POSIX")
        return c
    }()

    private func calc() -> MonthlyLoggingCalculator {
        MonthlyLoggingCalculator(calendar: calendar)
    }

    private func date(_ y: Int, _ m: Int, _ d: Int) -> Date {
        calendar.date(from: DateComponents(year: y, month: m, day: d, hour: 12))!
    }

    private func log(_ y: Int, _ m: Int, _ d: Int, quality: String = "okay") -> HabitLog {
        let entry = HabitLog(date: calendar.startOfDay(for: date(y, m, d)))
        entry.dietQuality = quality
        return entry
    }

    func testEmptyHabitsZeroCount() {
        let result = calc().compute(habits: [], asOf: date(2026, 5, 10))
        XCTAssertEqual(result.daysLogged, 0)
        XCTAssertEqual(result.dayOfMonth, 10)
        XCTAssertEqual(result.daysInMonth, 31)
        XCTAssertEqual(result.monthName, "May")
    }

    func testCountsOnlyCurrentMonth() {
        let habits = [
            log(2026, 4, 28),
            log(2026, 4, 29),
            log(2026, 5, 1),
            log(2026, 5, 5),
            log(2026, 5, 8)
        ]
        let result = calc().compute(habits: habits, asOf: date(2026, 5, 10))
        XCTAssertEqual(result.daysLogged, 3)
    }

    func testMissedDaysDoNotBreakChain() {
        // Day 4 + day 8 missed scenario from vision Q7 research.
        let habits = [
            log(2026, 5, 1), log(2026, 5, 2), log(2026, 5, 3),
            // 4 missed
            log(2026, 5, 5), log(2026, 5, 6), log(2026, 5, 7),
            // 8 missed
            log(2026, 5, 9), log(2026, 5, 10)
        ]
        let result = calc().compute(habits: habits, asOf: date(2026, 5, 10))
        XCTAssertEqual(result.daysLogged, 8) // never decremented
    }

    func testDeduplicatesSameDay() {
        let habits = [log(2026, 5, 1), log(2026, 5, 1, quality: "great")]
        let result = calc().compute(habits: habits, asOf: date(2026, 5, 1))
        XCTAssertEqual(result.daysLogged, 1)
    }

    func testRoughDaysCount() {
        let habits = [log(2026, 5, 1, quality: "rough")]
        let result = calc().compute(habits: habits, asOf: date(2026, 5, 1))
        XCTAssertEqual(result.daysLogged, 1)
    }

    func testUnknownQualityDoesNotCount() {
        let habits = [log(2026, 5, 1, quality: "unknown")]
        let result = calc().compute(habits: habits, asOf: date(2026, 5, 1))
        XCTAssertEqual(result.daysLogged, 0)
    }

    // MARK: - Milestone math

    func testStartMilestoneOnDayOne() {
        let result = calc().compute(habits: [], asOf: date(2026, 5, 1))
        XCTAssertEqual(result.milestone, .start)
    }

    func testQuarterMilestoneIn31DayMonth() {
        // 31-day month: 25% threshold = ceil(7.75) = day 8
        XCTAssertNil(calc().compute(habits: [], asOf: date(2026, 5, 7)).milestone)
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 5, 8)).milestone, .quarter)
        XCTAssertNil(calc().compute(habits: [], asOf: date(2026, 5, 9)).milestone)
    }

    func testHalfMilestoneIn31DayMonth() {
        // 31-day month: 50% threshold = ceil(15.5) = day 16
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 5, 16)).milestone, .half)
        XCTAssertNil(calc().compute(habits: [], asOf: date(2026, 5, 15)).milestone)
    }

    func testThreeQuarterMilestoneIn31DayMonth() {
        // 31-day month: 75% threshold = ceil(23.25) = day 24
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 5, 24)).milestone, .threeQuarter)
        XCTAssertNil(calc().compute(habits: [], asOf: date(2026, 5, 25)).milestone)
    }

    func testMilestonesIn30DayMonth() {
        // April 2026: 30 days. 25%=8, 50%=15, 75%=23.
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 4, 1)).milestone, .start)
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 4, 8)).milestone, .quarter)
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 4, 15)).milestone, .half)
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 4, 23)).milestone, .threeQuarter)
    }

    func testMilestonesIn28DayFebruary() {
        // 2026 is non-leap. 25%=7, 50%=14, 75%=21.
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 2, 1)).milestone, .start)
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 2, 7)).milestone, .quarter)
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 2, 14)).milestone, .half)
        XCTAssertEqual(calc().compute(habits: [], asOf: date(2026, 2, 21)).milestone, .threeQuarter)
    }

    func testNonMilestoneDayIsNil() {
        XCTAssertNil(calc().compute(habits: [], asOf: date(2026, 5, 12)).milestone)
        XCTAssertNil(calc().compute(habits: [], asOf: date(2026, 5, 30)).milestone)
    }

    // MARK: - Tone copy presence

    func testEveryToneCoversEveryMilestone() {
        for tone in ToneMode.allCases {
            for milestone in [
                MonthlyLogging.Milestone.start,
                .quarter, .half, .threeQuarter
            ] {
                let copy = tone.monthlyLoggingMilestoneLine(
                    milestone, daysLogged: 6, monthName: "May"
                )
                XCTAssertFalse(copy.isEmpty, "\(tone) / \(milestone) returned empty copy")
            }
            XCTAssertFalse(tone.monthlyLoggingNeutralLine.isEmpty)
        }
    }

    /// Locks the operator brief: tone-aware milestone copy on gentle /
    /// coach / firmDirect must actually differ. Earlier passes shared
    /// copy across gentle+coach at start and half — the polish session
    /// of 2026-05-06 split them. This guard prevents quiet regression.
    func testTonesDifferAtEveryMilestone() {
        for milestone in [
            MonthlyLogging.Milestone.start,
            .quarter, .half, .threeQuarter
        ] {
            let lines = ToneMode.allCases.map {
                $0.monthlyLoggingMilestoneLine(
                    milestone, daysLogged: 6, monthName: "May"
                )
            }
            XCTAssertEqual(
                Set(lines).count, lines.count,
                "tones share copy at \(milestone): \(lines)"
            )
        }
    }
}
