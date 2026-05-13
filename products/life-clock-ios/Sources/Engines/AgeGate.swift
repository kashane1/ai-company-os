import Foundation

/// Age-gating helpers used to hide content from users who report being
/// under 18. Pure functions — take a birthDate + calendar + as-of date,
/// return a Bool. No `Date()` calls.
///
/// Implementation rationale: Apple's age rating is a *floor* (the minimum
/// download age). The App Store rating is **13+** (Apple deprecated the
/// 12+ tier in July 2025 and auto-mapped Life Clock to 13+; see
/// `docs/products/life-clock/AGE_COMPLIANCE.md`). We hide alcohol /
/// smoking pickers from users who report a DOB making them under 18.
/// Users 18+ see the full picker set. Users reporting under 13 are hard-
/// blocked at the `BaselineDOB` onboarding step (`Under13Block`).
///
/// Surfaces consulting this gate:
/// - `OnboardingScreen.afterBodyComp` — minors skip the smoking +
///   alcohol screens entirely during onboarding.
/// - `LifeClockStore.isAdultUser` → `QuickLogSheet` — minors don't see
///   the smoking/vaping or alcohol pickers in the daily check-in.
/// - `OnboardingCoordinator.shouldShowPenaltyScreen` — minors skip the
///   `bigNumberPenalty` mortality-framing reveal screen.
enum AgeGate {
    static func ageInYears(birthDate: Date, asOf: Date, calendar: Calendar) -> Int {
        calendar.dateComponents([.year], from: birthDate, to: asOf).year ?? 0
    }

    /// True iff the user is at least 18 years old as of the given date.
    static func isAdult(birthDate: Date, asOf: Date, calendar: Calendar) -> Bool {
        ageInYears(birthDate: birthDate, asOf: asOf, calendar: calendar) >= 18
    }
}
