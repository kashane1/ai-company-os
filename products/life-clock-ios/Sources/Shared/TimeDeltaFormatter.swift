import Foundation

enum TimeDeltaFormatter {
    static func format(minutes: Int) -> String {
        let abs = Swift.abs(minutes)
        let sign = minutes >= 0 ? "+" : "-"
        if abs < 60 {
            return "\(sign)\(abs) min"
        }
        let hours = abs / 60
        let mins = abs % 60
        if mins == 0 {
            return "\(sign)\(hours)h"
        }
        return "\(sign)\(hours)h \(mins)m"
    }

    static func format(years: Double) -> String {
        let rounded = (years * 10).rounded() / 10
        return String(format: "%.1f years", rounded)
    }

    /// VoiceOver-friendly years+months phrasing for projection values.
    /// Matches the rounding used by TodayView.trajectoryPeek's visible
    /// "Xy Ym" string but expands units so VO reads "eighty-seven years
    /// two months" instead of "eighty-seven y two m."
    static func formatProjectionA11y(years: Double) -> String {
        let totalMonths = Int((years * 12).rounded())
        let y = totalMonths / 12
        let m = totalMonths % 12
        let yearPart = "\(y) \(y == 1 ? "year" : "years")"
        if m == 0 { return yearPart }
        let monthPart = "\(m) \(m == 1 ? "month" : "months")"
        return "\(yearPart) \(monthPart)"
    }
}
