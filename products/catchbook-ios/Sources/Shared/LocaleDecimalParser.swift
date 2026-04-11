import Foundation

/// Parses user-entered decimal strings in a locale-aware way so that users in
/// locales that use a comma as the decimal separator (de_DE, fr_FR, etc.) can
/// type "1,5" and get 1.5 — `Double(_:)` alone would reject that.
///
/// The parser accepts both the current locale's decimal separator AND the
/// POSIX "." so users typing on a hardware keyboard with a period still work.
enum LocaleDecimalParser {
    /// Parse a user-entered numeric string. Returns nil for empty input or
    /// unparseable content.
    static func parse(_ value: String, locale: Locale = .current) -> Double? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        let formatter = NumberFormatter()
        formatter.locale = locale
        formatter.numberStyle = .decimal
        formatter.isLenient = true
        if let number = formatter.number(from: trimmed) {
            return number.doubleValue
        }

        // Fallback: if the locale uses a comma separator but the user typed a
        // period (or vice versa), swap and retry with POSIX parsing.
        let posix = NumberFormatter()
        posix.locale = Locale(identifier: "en_US_POSIX")
        posix.numberStyle = .decimal
        if let number = posix.number(from: trimmed) {
            return number.doubleValue
        }

        // Last-chance swap: replace comma with period.
        let swapped = trimmed.replacingOccurrences(of: ",", with: ".")
        return Double(swapped)
    }
}
