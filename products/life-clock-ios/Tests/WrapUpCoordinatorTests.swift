import XCTest
@testable import LifeClock

final class WrapUpCoordinatorTests: XCTestCase {
    // 2027-01-15 Friday, 12:00:00 UTC. Use a UTC-pinned EngineClock.fixed so
    // calendar math is timezone-stable across hosts.
    private let today = Date(timeIntervalSince1970: 1_768_521_600)

    private func makeCoordinator() -> WrapUpCoordinator {
        WrapUpCoordinator(clock: .fixed(today))
    }

    private func dayBefore(_ date: Date, _ days: Int) -> Date {
        date.addingTimeInterval(-Double(days) * 86_400)
    }

    private var yesterday: Date { dayBefore(today, 1) }

    private func snapshot(for date: Date, hasMinimumData: Bool = true) -> WrapUpCoordinator.DaySnapshot {
        WrapUpCoordinator.DaySnapshot(date: date, hasMinimumData: hasMinimumData)
    }

    // MARK: - Reinstall guard

    func testReturnsNilWhenOnboardingDateMissing() {
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: nil,
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: yesterday)],
            weeks: [],
            now: today
        )
        XCTAssertNil(result)
    }

    func testReturnsNilWhenOnboardedToday() {
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: today,
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: yesterday)],
            weeks: [],
            now: today
        )
        XCTAssertNil(result)
    }

    func testReturnsNilWhenOnboardedYesterday() {
        // Need to live through ≥1 full local day post-onboarding. Onboarded
        // yesterday → today is day-1 → still suppressed.
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: yesterday,
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: yesterday)],
            weeks: [],
            now: today
        )
        XCTAssertNil(result)
    }

    func testReturnsYesterdayWhenOnboardedTwoDaysAgoWithData() {
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: dayBefore(today, 2),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: yesterday)],
            weeks: [],
            now: today
        )
        guard case .yesterday(let date) = result else {
            XCTFail("expected .yesterday, got \(String(describing: result))")
            return
        }
        XCTAssertEqual(
            EngineClock.fixed(today).dayKey(date),
            EngineClock.fixed(today).dayKey(yesterday)
        )
    }

    // MARK: - Single-show / monotonic

    func testReturnsNilWhenAlreadyShownToday() {
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: today,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: yesterday)],
            weeks: [],
            now: today
        )
        XCTAssertNil(result)
    }

    func testAdvancesAcrossMissedDays() {
        // Last shown 3 days ago, yesterday has data → present yesterday.
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: dayBefore(today, 3),
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: yesterday)],
            weeks: [],
            now: today
        )
        if case .yesterday = result { return }
        XCTFail("expected .yesterday, got \(String(describing: result))")
    }

    func testIsMonotonicAgainstClockGoingBackward() {
        // Last shown is "tomorrow" relative to now (clock went backward via
        // timezone change). Coordinator must not un-show.
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: today.addingTimeInterval(86_400),
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: yesterday)],
            weeks: [],
            now: today
        )
        XCTAssertNil(result)
    }

    // MARK: - Minimum-data threshold

    func testReturnsNilWhenYesterdayHasNoData() {
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: yesterday, hasMinimumData: false)],
            weeks: [],
            now: today
        )
        XCTAssertNil(result)
    }

    func testReturnsNilWhenYesterdaySnapshotMissing() {
        let coordinator = makeCoordinator()
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 5))],
            weeks: [],
            now: today
        )
        XCTAssertNil(result)
    }

    // MARK: - Weekly

    func testWeeklyReturnsNilOnNonWeekStartDay() {
        // 2027-01-15 is a Friday. UTC calendar's firstWeekday is Sunday (1),
        // so today's weekday (6) != firstWeekday → suppress.
        let coordinator = makeCoordinator()
        let weekStart = dayBefore(today, 5)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: today,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: weekStart)],
            now: today
        )
        XCTAssertNil(result)
    }

    func testWeeklyReturnsWhenOnFirstDayOfWeek() {
        // 2027-01-17 is a Sunday (UTC). firstWeekday = 1.
        let sunday = Date(timeIntervalSince1970: 1_768_694_400)
        let coordinator = WrapUpCoordinator(clock: .fixed(sunday))
        let weekStart = sunday
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: sunday.addingTimeInterval(-30 * 86_400),
            lastShownYesterdayWrapUpDay: sunday,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: weekStart)],
            now: sunday
        )
        if case .weekly(let returned) = result {
            XCTAssertEqual(returned, weekStart)
            return
        }
        XCTFail("expected .weekly, got \(String(describing: result))")
    }

    func testYesterdayPrecedesWeekly() {
        let sunday = Date(timeIntervalSince1970: 1_768_694_400)
        let coordinator = WrapUpCoordinator(clock: .fixed(sunday))
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardedAt: sunday.addingTimeInterval(-30 * 86_400),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [WrapUpCoordinator.DaySnapshot(
                date: sunday.addingTimeInterval(-86_400),
                hasMinimumData: true
            )],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: sunday)],
            now: sunday
        )
        if case .yesterday = result { return }
        XCTFail("expected .yesterday to win, got \(String(describing: result))")
    }
}
