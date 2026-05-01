import Foundation

/// Pure decision logic for "should we present a wrap-up moment right now?"
///
/// Takes value-type DTOs (never SwiftData `@Model` instances) and an explicit
/// `now: Date` so the decision is fully a function of inputs. Tests pin the
/// clock; production callers map their `@Model` rows into the snapshot DTOs
/// before calling.
///
/// Decision priority: yesterday wrap-up wins over weekly. Weekly is queued
/// behind it; never both at once.
///
/// Wrap-up scheduling is a product decision, not a locale decision: the
/// week-start day is pinned via `Config.firstWeekday` (default Monday = 2)
/// rather than reading `Calendar.firstWeekday`. This guarantees
/// test-vs-prod parity across US (Sunday-default) and EU (Monday-default)
/// locales.
struct WrapUpCoordinator {
    let clock: EngineClock
    var config: Config = .default

    struct Config: Equatable {
        /// 1 = Sunday, 2 = Monday, ..., 7 = Saturday. Default Monday.
        var firstWeekday: Int = 2
        /// Weekly wrap-ups never fire for a week start older than this many
        /// days. Prevents stale `weekStart` values (e.g. after a long absence
        /// or restored backup) from triggering an out-of-date ceremony.
        var weeklyRecencyDays: Int = 14

        static let `default` = Config()
    }

    struct ProfileSnapshot: Equatable {
        /// Mirrors `UserProfile.onboardingCompletedAt`. Used as the "lived
        /// through one full day post-install" guard against ghost wrap-ups
        /// on reinstall.
        let onboardingCompletedAt: Date?
        let lastShownYesterdayWrapUpDay: Date?
        let lastShownWeeklyWrapUpWeek: Date?
    }

    struct DaySnapshot: Equatable {
        /// Start of the logical day this snapshot represents. Compared via
        /// `Calendar.isDate(_:inSameDayAs:)` against yesterday.
        let date: Date
        /// True iff at least one HK metric is non-zero AND HK auth was granted
        /// for that type when the snapshot was captured. Mappers compute this
        /// at snapshot ingestion time so the coordinator stays a pure
        /// predicate.
        let hasMinimumData: Bool
    }

    struct WeekSnapshot: Equatable {
        /// Start-of-week date in the configured `firstWeekday`.
        let weekStart: Date
    }

    enum PendingWrapUp: Equatable {
        case yesterday(date: Date)
        case weekly(weekStart: Date)
    }

    func pendingWrapUp(
        profile: ProfileSnapshot,
        snapshots: [DaySnapshot],
        weeks: [WeekSnapshot],
        now: Date
    ) -> PendingWrapUp? {
        if let yesterday = pendingYesterday(profile: profile, snapshots: snapshots, now: now) {
            return .yesterday(date: yesterday)
        }
        if let weekStart = pendingWeekly(profile: profile, weeks: weeks, now: now) {
            return .weekly(weekStart: weekStart)
        }
        return nil
    }

    // MARK: - Mark-shown helpers

    /// Returns a new `ProfileSnapshot` with `lastShownYesterdayWrapUpDay`
    /// advanced to today. Use after the wrap-up sheet is presented so
    /// callers don't re-implement the day-key write at each site.
    func markYesterdayShown(
        profile: ProfileSnapshot,
        now: Date
    ) -> ProfileSnapshot {
        let today = clock.calendar.startOfDay(for: now)
        return ProfileSnapshot(
            onboardingCompletedAt: profile.onboardingCompletedAt,
            lastShownYesterdayWrapUpDay: today,
            lastShownWeeklyWrapUpWeek: profile.lastShownWeeklyWrapUpWeek
        )
    }

    /// Returns a new `ProfileSnapshot` with `lastShownWeeklyWrapUpWeek`
    /// advanced to the given week start.
    func markWeeklyShown(
        profile: ProfileSnapshot,
        weekStart: Date
    ) -> ProfileSnapshot {
        let normalized = clock.calendar.startOfDay(for: weekStart)
        return ProfileSnapshot(
            onboardingCompletedAt: profile.onboardingCompletedAt,
            lastShownYesterdayWrapUpDay: profile.lastShownYesterdayWrapUpDay,
            lastShownWeeklyWrapUpWeek: normalized
        )
    }

    // MARK: - Decision branches

    private func pendingYesterday(
        profile: ProfileSnapshot,
        snapshots: [DaySnapshot],
        now: Date
    ) -> Date? {
        let cal = clock.calendar
        let today = cal.startOfDay(for: now)
        guard let yesterday = cal.date(byAdding: .day, value: -1, to: today) else {
            return nil
        }

        guard isPastReinstallGuard(profile: profile, today: today) else {
            return nil
        }

        // Single-show-per-day, monotonic. If clock moves backward we never
        // un-show a wrap-up.
        if let last = profile.lastShownYesterdayWrapUpDay {
            let lastDay = cal.startOfDay(for: last)
            if lastDay >= today {
                return nil
            }
        }

        // Suppress on long absence / partial-data days. History surfaces those
        // as "No data" rows; the wrap-up moment is reserved for days the user
        // actually lived through with the app.
        let snapshot = snapshots.first { cal.isDate($0.date, inSameDayAs: yesterday) }
        guard let snapshot, snapshot.hasMinimumData else {
            return nil
        }
        return yesterday
    }

    private func pendingWeekly(
        profile: ProfileSnapshot,
        weeks: [WeekSnapshot],
        now: Date
    ) -> Date? {
        let cal = clock.calendar
        let today = cal.startOfDay(for: now)

        // Week-start day is product-pinned via Config (not locale-driven).
        let weekday = cal.component(.weekday, from: today)
        guard weekday == config.firstWeekday else {
            return nil
        }

        // Reinstall guard mirrors the yesterday path: don't ceremony a week
        // for a user who hasn't lived through one full day with the app.
        guard isPastReinstallGuard(profile: profile, today: today) else {
            return nil
        }

        // Bound to recent + non-future. Caller may pass stale/future weeks
        // after restored backup or clock skew.
        guard let oldestAllowed = cal.date(
            byAdding: .day, value: -config.weeklyRecencyDays, to: today
        ) else {
            return nil
        }
        let candidates = weeks
            .map { cal.startOfDay(for: $0.weekStart) }
            .filter { $0 <= today && $0 >= oldestAllowed }
        guard let mostRecentWeekStart = candidates.max() else {
            return nil
        }

        if let last = profile.lastShownWeeklyWrapUpWeek {
            let lastStart = cal.startOfDay(for: last)
            if lastStart >= mostRecentWeekStart {
                return nil
            }
        }
        return mostRecentWeekStart
    }

    private func isPastReinstallGuard(
        profile: ProfileSnapshot,
        today: Date
    ) -> Bool {
        let cal = clock.calendar
        guard let onboardedAt = profile.onboardingCompletedAt else {
            return false
        }
        let onboardedDay = cal.startOfDay(for: onboardedAt)
        guard let earliestEligibleToday = cal.date(
            byAdding: .day, value: 2, to: onboardedDay
        ) else {
            return false
        }
        return today >= earliestEligibleToday
    }
}
