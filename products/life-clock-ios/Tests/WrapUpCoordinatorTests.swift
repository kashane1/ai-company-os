import XCTest
@testable import LifeClock

final class WrapUpCoordinatorTests: XCTestCase {
    // 2027-01-15 Friday, 12:00:00 UTC. EngineClock.fixed pins UTC for stable
    // calendar math across hosts.
    private let today = Date(timeIntervalSince1970: 1_768_521_600)

    // 2027-01-18 Monday, 12:00:00 UTC. Used for weekly tests; matches the
    // coordinator's default Config.firstWeekday = 2.
    private let monday = Date(timeIntervalSince1970: 1_768_780_800)

    private func makeCoordinator(at date: Date) -> WrapUpCoordinator {
        WrapUpCoordinator(clock: .fixed(date))
    }

    private func dayBefore(_ date: Date, _ days: Int) -> Date {
        date.addingTimeInterval(-Double(days) * 86_400)
    }

    private func snapshot(
        for date: Date,
        hasMinimumData: Bool = true
    ) -> WrapUpCoordinator.DaySnapshot {
        WrapUpCoordinator.DaySnapshot(date: date, hasMinimumData: hasMinimumData)
    }

    // MARK: - Reinstall guard

    func testReturnsNilWhenOnboardingDateMissing() {
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: nil,
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 1))],
            weeks: [],
            now: today
        ))
    }

    func testReturnsNilWhenOnboardedYesterday() {
        // Need to live through ≥1 full local day post-onboarding. Onboarded
        // yesterday → today is day-1 → still suppressed.
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 1),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 1))],
            weeks: [],
            now: today
        ))
    }

    func testReturnsYesterdayWhenOnboardedTwoDaysAgoWithData() {
        let coordinator = makeCoordinator(at: today)
        let yesterday = dayBefore(today, 1)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 2),
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
        XCTAssertTrue(coordinator.clock.calendar.isDate(date, inSameDayAs: yesterday))
    }

    func testReturnsNilWhenOnboardedAtFutureDate() {
        // Restored backup / clock skew: onboarding date is after now. The
        // reinstall guard must hold, never fire from a negative day count.
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: today.addingTimeInterval(7 * 86_400),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 1))],
            weeks: [],
            now: today
        ))
    }

    // MARK: - Single-show / monotonic

    func testReturnsNilWhenAlreadyShownToday() {
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: today,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 1))],
            weeks: [],
            now: today
        ))
    }

    func testAdvancesAcrossMissedDays() {
        // Last shown 3 days ago, yesterday has data → present yesterday.
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: dayBefore(today, 3),
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 1))],
            weeks: [],
            now: today
        )
        if case .yesterday = result { return }
        XCTFail("expected .yesterday, got \(String(describing: result))")
    }

    func testIsMonotonicAgainstClockGoingBackward() {
        // Last shown is "tomorrow" relative to now (clock went backward via
        // timezone change). Coordinator must not un-show.
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: today.addingTimeInterval(86_400),
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 1))],
            weeks: [],
            now: today
        ))
    }

    // MARK: - Minimum-data threshold

    func testReturnsNilWhenYesterdayHasNoData() {
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 1), hasMinimumData: false)],
            weeks: [],
            now: today
        ))
    }

    func testReturnsNilWhenYesterdaySnapshotMissing() {
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(today, 5))],
            weeks: [],
            now: today
        ))
    }

    func testReturnsNilWhenSnapshotsArrayEmpty() {
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [],
            now: today
        ))
    }

    // MARK: - Weekly: gating

    func testWeeklyReturnsNilOnNonWeekStartDay() {
        // Today is Friday; default Config.firstWeekday = 2 (Monday) → suppress.
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: today,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: dayBefore(today, 5))],
            now: today
        ))
    }

    func testWeeklyReturnsOnFirstDayOfWeek() {
        // 2027-01-18 is a Monday (UTC). Default firstWeekday = 2.
        let coordinator = makeCoordinator(at: monday)
        let weekStart = dayBefore(monday, 7)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(monday, 30),
            lastShownYesterdayWrapUpDay: monday,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: weekStart)],
            now: monday
        )
        if case .weekly(let returned) = result {
            XCTAssertEqual(returned, weekStart)
            return
        }
        XCTFail("expected .weekly, got \(String(describing: result))")
    }

    func testWeeklyHonorsCustomFirstWeekday() {
        // Override Config to firstWeekday = 1 (Sunday). Today is Friday →
        // still suppress. Pin a Sunday and confirm fires.
        var coordinator = makeCoordinator(at: today)
        coordinator.config = WrapUpCoordinator.Config(firstWeekday: 1)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: today,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: dayBefore(today, 5))],
            now: today
        ))

        // 2027-01-17 is a Sunday (UTC).
        let sunday = Date(timeIntervalSince1970: 1_768_694_400)
        var sundayCoord = WrapUpCoordinator(clock: .fixed(sunday))
        sundayCoord.config = WrapUpCoordinator.Config(firstWeekday: 1)
        let sundayProfile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: sunday.addingTimeInterval(-30 * 86_400),
            lastShownYesterdayWrapUpDay: sunday,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = sundayCoord.pendingWrapUp(
            profile: sundayProfile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: sunday.addingTimeInterval(-7 * 86_400))],
            now: sunday
        )
        if case .weekly = result { return }
        XCTFail("expected .weekly with firstWeekday=1, got \(String(describing: result))")
    }

    func testWeeklyAppliesReinstallGuard() {
        // Onboarded today (Monday), weekStart == today. Reinstall guard must
        // suppress — the user has not lived through any past week with the app.
        let coordinator = makeCoordinator(at: monday)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: monday,
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: monday)],
            now: monday
        ))
    }

    func testWeeklyIgnoresFutureWeekStart() {
        // weeks contains only future-dated entries (clock skew / restored
        // backup). Coordinator must not fire .weekly for a week that hasn't
        // happened.
        let coordinator = makeCoordinator(at: monday)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(monday, 30),
            lastShownYesterdayWrapUpDay: monday,
            lastShownWeeklyWrapUpWeek: nil
        )
        let futureWeek = monday.addingTimeInterval(14 * 86_400)
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: futureWeek)],
            now: monday
        ))
    }

    func testWeeklyIgnoresStaleWeekStart() {
        // weeks most recent is older than weeklyRecencyDays. Suppress.
        let coordinator = makeCoordinator(at: monday)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(monday, 60),
            lastShownYesterdayWrapUpDay: monday,
            lastShownWeeklyWrapUpWeek: nil
        )
        let staleWeek = dayBefore(monday, 30)
        XCTAssertNil(coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: staleWeek)],
            now: monday
        ))
    }

    func testYesterdayPrecedesWeekly() {
        let coordinator = makeCoordinator(at: monday)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(monday, 30),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let result = coordinator.pendingWrapUp(
            profile: profile,
            snapshots: [snapshot(for: dayBefore(monday, 1))],
            weeks: [WrapUpCoordinator.WeekSnapshot(weekStart: dayBefore(monday, 7))],
            now: monday
        )
        if case .yesterday = result { return }
        XCTFail("expected .yesterday to win, got \(String(describing: result))")
    }

    // MARK: - markShown helpers (round-trip)

    func testMarkYesterdayShownSuppressesNextCall() {
        let coordinator = makeCoordinator(at: today)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(today, 30),
            lastShownYesterdayWrapUpDay: nil,
            lastShownWeeklyWrapUpWeek: nil
        )
        let snapshots = [snapshot(for: dayBefore(today, 1))]
        let firstCall = coordinator.pendingWrapUp(
            profile: profile, snapshots: snapshots, weeks: [], now: today
        )
        guard case .yesterday = firstCall else {
            XCTFail("setup expected .yesterday, got \(String(describing: firstCall))")
            return
        }
        let advanced = coordinator.markYesterdayShown(profile: profile, now: today)
        let secondCall = coordinator.pendingWrapUp(
            profile: advanced, snapshots: snapshots, weeks: [], now: today
        )
        XCTAssertNil(secondCall)
    }

    func testMarkWeeklyShownSuppressesNextCall() {
        let coordinator = makeCoordinator(at: monday)
        let weekStart = dayBefore(monday, 7)
        let profile = WrapUpCoordinator.ProfileSnapshot(
            onboardingCompletedAt: dayBefore(monday, 30),
            lastShownYesterdayWrapUpDay: monday,
            lastShownWeeklyWrapUpWeek: nil
        )
        let weeks = [WrapUpCoordinator.WeekSnapshot(weekStart: weekStart)]
        let firstCall = coordinator.pendingWrapUp(
            profile: profile, snapshots: [], weeks: weeks, now: monday
        )
        guard case .weekly = firstCall else {
            XCTFail("setup expected .weekly, got \(String(describing: firstCall))")
            return
        }
        let advanced = coordinator.markWeeklyShown(profile: profile, weekStart: weekStart)
        let secondCall = coordinator.pendingWrapUp(
            profile: advanced, snapshots: [], weeks: weeks, now: monday
        )
        XCTAssertNil(secondCall)
    }
}
