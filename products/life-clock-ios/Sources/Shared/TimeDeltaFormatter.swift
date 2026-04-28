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
}
