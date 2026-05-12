import XCTest
@testable import LifeClock

/// V1.7.0 — Future tab plan §Phase 4 / audit follow-up.
///
/// `Date.snappedToLastSunday(calendar:)` powers the Pro long-form
/// narrative subhead ("Reflection from Sunday, May 10") and the
/// `[weekStart, weekEnd)` slicing that picks "this week" vs "prior
/// week" snapshots in `FutureView.longFormNarrativeSection`.
///
/// The audit's B2 fix flipped the slicing to anchor on `weekEnd`;
/// these tests pin the helper's behavior so future edits don't drift
/// off-by-a-day silently.
final class DateSnappedToLastSundayTests: XCTestCase {
    private let calendar = Calendar.lifeClockUTC

    private func date(_ year: Int, _ month: Int, _ day: Int, hour: Int = 12) -> Date {
        calendar.date(from: DateComponents(year: year, month: month, day: day, hour: hour))!
    }

    func testMondayReturnsPriorSundayAtStartOfDay() {
        // 2026-05-11 is a Monday. Last Sunday is 2026-05-10.
        let monday = date(2026, 5, 11)
        let snapped = monday.snappedToLastSunday(calendar: calendar)
        XCTAssertEqual(snapped, date(2026, 5, 10, hour: 0),
                       "Monday should snap to the previous day (Sunday) at start-of-day")
    }

    func testSundayReturnsSelfAtStartOfDay() {
        // 2026-05-10 is a Sunday with hour 14:00. Snap should land at
        // 2026-05-10 00:00 (start-of-day).
        let sundayAfternoon = date(2026, 5, 10, hour: 14)
        let snapped = sundayAfternoon.snappedToLastSunday(calendar: calendar)
        XCTAssertEqual(snapped, date(2026, 5, 10, hour: 0),
                       "Sunday should snap to its own start-of-day")
    }

    func testSaturdayReturnsPriorSundaySixDaysBack() {
        // 2026-05-09 is a Saturday. Last Sunday is 2026-05-03 (six days back).
        let saturday = date(2026, 5, 9)
        let snapped = saturday.snappedToLastSunday(calendar: calendar)
        XCTAssertEqual(snapped, date(2026, 5, 3, hour: 0),
                       "Saturday should snap to the prior Sunday (six days back)")
    }

    func testWednesdayReturnsPriorSundayThreeDaysBack() {
        // 2026-05-13 is a Wednesday. Last Sunday is 2026-05-10.
        let wednesday = date(2026, 5, 13)
        let snapped = wednesday.snappedToLastSunday(calendar: calendar)
        XCTAssertEqual(snapped, date(2026, 5, 10, hour: 0))
    }

    func testCrossesDSTBoundary() {
        // US DST 2026 spring-forward is 2026-03-08 (Sunday). Snapping a
        // Tuesday 2026-03-10 with a US-Eastern calendar must still land
        // on 2026-03-08 at midnight local, not 23:00 the prior day.
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "America/New_York")!
        let tuesday = cal.date(from: DateComponents(
            year: 2026, month: 3, day: 10, hour: 12
        ))!
        let expected = cal.date(from: DateComponents(
            year: 2026, month: 3, day: 8, hour: 0
        ))!
        XCTAssertEqual(tuesday.snappedToLastSunday(calendar: cal), expected,
                       "DST spring-forward must not produce a 23:00 anchor")
    }

    func testIdempotentOnSnappedValue() {
        // Snapping an already-snapped Sunday-at-midnight returns itself —
        // important when the call site re-snaps a derived value.
        let sundayMidnight = date(2026, 5, 10, hour: 0)
        let once = sundayMidnight.snappedToLastSunday(calendar: calendar)
        let twice = once.snappedToLastSunday(calendar: calendar)
        XCTAssertEqual(once, twice)
        XCTAssertEqual(once, sundayMidnight)
    }
}
