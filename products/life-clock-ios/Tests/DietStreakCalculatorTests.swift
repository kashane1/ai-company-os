import XCTest
@testable import LifeClock

final class DietStreakCalculatorTests: XCTestCase {
    private let asOf = Date(timeIntervalSince1970: 1_800_000_000) // pinned, UTC
    private let calendar = Calendar.lifeClockUTC

    private func makeCalc() -> DietStreakCalculator {
        DietStreakCalculator(calendar: calendar)
    }

    private func day(offset: Int) -> Date {
        // Day-start `offset` days before `asOf`. Negative = earlier days.
        let dayStart = calendar.startOfDay(for: asOf)
        return calendar.date(byAdding: .day, value: offset, to: dayStart) ?? dayStart
    }

    private func log(at offset: Int, quality: String) -> HabitLog {
        let h = HabitLog(date: day(offset: offset))
        h.dietQuality = quality
        return h
    }

    // MARK: - Empty / sparse

    func testNoLogsProducesZeroStreaks() {
        let result = makeCalc().compute(habits: [], asOf: asOf)
        XCTAssertEqual(result, .zero)
    }

    func testOnlyAncientLogsAreOutsideTheGracePeriod() {
        // Latest log is 5 days ago — outside the 24h grace window.
        let logs = (3...5).map { log(at: -$0, quality: "great") }
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        XCTAssertEqual(result, .zero, "logs >1 day old shouldn't count toward an active streak")
    }

    // MARK: - Logging streak

    func testTodayLoggedAlone() {
        let logs = [log(at: 0, quality: "okay")]
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        XCTAssertEqual(result.loggingDays, 1)
        XCTAssertEqual(result.goodDays, 1)
    }

    func testYesterdayOnlyKeepsStreakAlive() {
        // User hasn't logged today *yet*; logged yesterday. Streak survives.
        let logs = [log(at: -1, quality: "great")]
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        XCTAssertEqual(result.loggingDays, 1, "streak should survive 24h grace, not zero out at midnight")
        XCTAssertEqual(result.goodDays, 1)
    }

    func testFiveConsecutiveLoggedDaysAllGreat() {
        let logs = (0...4).map { log(at: -$0, quality: "great") }
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        XCTAssertEqual(result.loggingDays, 5)
        XCTAssertEqual(result.goodDays, 5)
    }

    func testGapBreaksLoggingStreak() {
        // Logged today, day-1, day-2; missed day-3; logged day-4.
        let logs = [
            log(at: 0, quality: "okay"),
            log(at: -1, quality: "okay"),
            log(at: -2, quality: "okay"),
            // day -3 missing
            log(at: -4, quality: "okay"),
        ]
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        XCTAssertEqual(result.loggingDays, 3, "gap on day -3 ends the run at 3")
        XCTAssertEqual(result.goodDays, 3)
    }

    // MARK: - Good streak vs logging streak

    func testRoughDayStillExtendsLoggingStreakButBreaksGoodStreak() {
        // 5 days of logs, today is rough.
        var logs = [log(at: 0, quality: "rough")]
        logs += (1...4).map { log(at: -$0, quality: "great") }
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        XCTAssertEqual(result.loggingDays, 5, "rough day must not punish the logging habit")
        XCTAssertEqual(result.goodDays, 0, "today rough → good streak resets")
    }

    func testRoughDayInTheMiddleStopsGoodStreakAtTheGap() {
        // Today great, day-1 great, day-2 rough, day-3 great, day-4 great.
        let logs = [
            log(at: 0, quality: "great"),
            log(at: -1, quality: "great"),
            log(at: -2, quality: "rough"),
            log(at: -3, quality: "great"),
            log(at: -4, quality: "great"),
        ]
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        XCTAssertEqual(result.loggingDays, 5)
        XCTAssertEqual(result.goodDays, 2, "good streak should count back from today only until the rough day")
    }

    // MARK: - Boundaries

    func testUnknownDietQualityDoesNotCountAsLogged() {
        // The HabitLog row exists (perhaps because of alcohol logging) but
        // dietQuality wasn't selected — defaults to "unknown" / not chosen.
        let unknown = HabitLog(date: day(offset: 0))
        unknown.dietQuality = "unknown"
        let logs = [unknown, log(at: -1, quality: "great"), log(at: -2, quality: "great")]
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        // Most recent "real" log is day -1, which is within 24h, so streak still alive.
        XCTAssertEqual(result.loggingDays, 2, "unknown diet quality is not a logged day; streak runs from yesterday back")
        XCTAssertEqual(result.goodDays, 2)
    }

    func testEmptyDietQualityStringDoesNotCount() {
        let blank = HabitLog(date: day(offset: 0))
        blank.dietQuality = ""
        let logs = [blank]
        let result = makeCalc().compute(habits: logs, asOf: asOf)
        XCTAssertEqual(result, .zero)
    }
}
