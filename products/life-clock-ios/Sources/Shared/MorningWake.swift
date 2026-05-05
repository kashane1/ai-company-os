import Foundation

/// First-open-of-day "wake" arbiter.
///
/// The Today screen's wake animation (clock-hand sweep + delta count-up +
/// mascot bump) plays at most once per local calendar day. This type owns
/// that gating decision so the view stays declarative.
///
/// Storage is a single `Int` `DayKey` under `UserDefaults` — no schema, no
/// migration burden. The key is namespaced so it cannot collide with
/// future per-feature defaults.
///
/// **Why not a Date?** `Calendar.startOfDay(for:)` is timezone-dependent;
/// a `DayKey` Int captured at write time stays stable across timezone
/// changes (same reasoning as `DayKey.swift`).
enum MorningWake {
    static let defaultsKey = "lifeClock.morningWake.lastDayKey"

    /// Total wall-clock budget for the wake sequence. Holds the operator
    /// constraint of "under 600ms total" (`docs/products/life-clock/`
    /// polish session). Hand sweep + count-up share this duration; the
    /// mascot scale keyframe runs concurrently and finishes inside it.
    static let totalDuration: Double = 0.50

    /// Returns true the first time this is asked on a given local day.
    /// Pure read — does not mutate storage. Caller must invoke `mark(...)`
    /// once the animation is actually scheduled, otherwise repeated
    /// `.onAppear` callbacks (scroll, sheet dismiss) would re-trigger it.
    static func shouldWake(
        now: Date,
        calendar: Calendar = .current,
        defaults: UserDefaults = .standard
    ) -> Bool {
        let today = DayKey.from(date: now, calendar: calendar)
        let last = defaults.integer(forKey: defaultsKey)   // returns 0 if absent
        return last != today
    }

    /// Records that today's wake has fired. Idempotent.
    static func mark(
        now: Date,
        calendar: Calendar = .current,
        defaults: UserDefaults = .standard
    ) {
        let today = DayKey.from(date: now, calendar: calendar)
        defaults.set(today, forKey: defaultsKey)
    }

    /// Test-only: clear the stored day key so the next `shouldWake` returns true.
    static func reset(defaults: UserDefaults = .standard) {
        defaults.removeObject(forKey: defaultsKey)
    }
}
