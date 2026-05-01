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
struct WrapUpCoordinator {
    let clock: EngineClock

    struct ProfileSnapshot: Equatable {
        /// Set when onboarding completes. Used as the "lived through one
        /// full day post-install" guard against ghost wrap-ups on reinstall.
        let onboardedAt: Date?
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
        /// Start-of-week date (locale's `firstWeekday`).
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

        // Reinstall guard: require user has lived through ≥1 full local day
        // post-onboarding before any wrap-up presents. Stricter than wallclock
        // 24h, immune to time-travel.
        guard let onboardedAt = profile.onboardedAt else {
            return nil
        }
        let onboardedDay = cal.startOfDay(for: onboardedAt)
        guard let earliestEligibleToday = cal.date(
            byAdding: .day, value: 2, to: onboardedDay
        ) else {
            return nil
        }
        if today < earliestEligibleToday {
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

        // Locale-driven week start (cal.firstWeekday).
        let weekday = cal.component(.weekday, from: today)
        guard weekday == cal.firstWeekday else {
            return nil
        }

        guard let mostRecentWeekStart = weeks.map({ cal.startOfDay(for: $0.weekStart) }).max() else {
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
}
