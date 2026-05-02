import Foundation

/// Timezone-stable day identifier. Encodes a local calendar day as
/// `yyyyMMdd` Int (e.g. `20260501`).
///
/// Why an Int and not `Date(startOfDay)`? `Calendar.startOfDay(for:)` is
/// computed in the calendar's *current* timezone. A `Date`-keyed lookup
/// for "today's reflection" would surface a previously-saved row as
/// missing the moment a user crosses a timezone boundary, and could
/// allow a duplicate write when they save again. An Int day key
/// captured at write time stays stable across timezone changes.
enum DayKey {
    static func from(date: Date, calendar: Calendar) -> Int {
        let comps = calendar.dateComponents([.year, .month, .day], from: date)
        let y = comps.year ?? 1970
        let m = comps.month ?? 1
        let d = comps.day ?? 1
        return y * 10_000 + m * 100 + d
    }
}
