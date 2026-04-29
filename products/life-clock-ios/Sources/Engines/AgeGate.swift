import Foundation

/// Age-gating helpers used to hide content from users who report being
/// under 18. Pure functions — take a birthDate + calendar + as-of date,
/// return a Bool. No `Date()` calls.
///
/// Implementation rationale: Apple's age rating is a *floor* (the minimum
/// download age). To keep the App Store rating at 12+ we hide alcohol /
/// smoking pickers from users who report a DOB making them under 18.
/// Users 18+ see the full picker set.
enum AgeGate {
    static func ageInYears(birthDate: Date, asOf: Date, calendar: Calendar) -> Int {
        calendar.dateComponents([.year], from: birthDate, to: asOf).year ?? 0
    }

    /// True iff the user is at least 18 years old as of the given date.
    static func isAdult(birthDate: Date, asOf: Date, calendar: Calendar) -> Bool {
        ageInYears(birthDate: birthDate, asOf: asOf, calendar: calendar) >= 18
    }
}
