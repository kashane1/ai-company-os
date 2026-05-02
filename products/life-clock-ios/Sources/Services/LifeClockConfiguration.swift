import Foundation

/// Single source of truth for brand-prone copy.
///
/// All user-facing strings that include the app or product name are read
/// from here so a future brand rename is a one-file change. SwiftUI
/// `Text("...")` calls that interpolate `appName` or `proName` localize
/// automatically against this module — no separate `.strings` table is
/// needed yet.
///
/// **Future i18n:** when shipping a non-English locale, convert this file
/// to a `Localizable.xcstrings` catalog. Every constant here becomes a
/// catalog key. The view-side ergonomics don't change because all reads go
/// through this enum.
///
/// **Brand rename procedure:**
///   1. Update the constants in this file.
///   2. Update `Info.plist` `CFBundleDisplayName` (manual — `Info.plist`
///      doesn't read Swift constants).
///   3. Update `Products.storekit` `displayName` / `referenceName` /
///      Subscription Group `name` (manual — JSON, not Swift).
///   4. Update `docs/products/life-clock/legal/privacy-policy.md` and
///      `terms-of-use.md` (publish to GitHub Pages).
///   5. Update `ASC_CHECKLIST.md` and `PHASE_STATUS.md`.
///   6. App Store Connect — update app name, subtitle, IAP display names.
enum LifeClockConfiguration {
    // MARK: - Brand

    static let appName = "Life Clock"
    static let appTagline = "Habits earn time."
    static let appStoreSubtitle = "See how habits move your life"

    static let proName = "Life Clock Pro"
    static let proAnnualName = "Life Clock Pro · Annual"
    static let proMonthlyName = "Life Clock Pro · Monthly"
    static let proLifetimeName = "Life Clock Pro · Lifetime"

    // MARK: - Identifiers (must match Products.storekit + ASC)

    static let bundleId = "io.aicompanyos.products.lifeclock"

    // MARK: - Disclaimer + safety copy

    /// The non-medical disclaimer. Reused in onboarding, QuickLog, Profile,
    /// SafetyNet, Paywall, and Today (V1.2.0). Brand-prone (mentions "Life
    /// Clock") so it lives here rather than inline.
    ///
    /// Per App Review trends post-2024, lifespan-adjacent framing requires
    /// explicit "educational estimate, not a lifespan prediction" language,
    /// not just generic "not medical advice."
    static let medicalDisclaimer =
        "Life-impact minutes are educational estimates from population-level research. " +
        "\(appName) is not medical advice, diagnosis, or treatment, and does not predict your " +
        "lifespan. Talk to a qualified clinician for medical decisions."

    /// One-line caption shown immediately under the signed delta on Today.
    /// Same sentiment as `medicalDisclaimer` — abbreviated for the high-
    /// frequency surface where the number is read.
    static let lifespanShortDisclaimer =
        "Educational estimate, not a lifespan prediction."

    static let healthKitRationale =
        "\(appName) reads your steps, sleep, exercise, and resting heart rate from Apple " +
        "Health to estimate how today's habits influence your health trajectory. Your data stays " +
        "on your device."

    static let safetyNetClosing =
        "\(appName) is a habit-tracking app. It is not a substitute for professional " +
        "mental-health support. The cautionary language in onboarding and Profile is not " +
        "boilerplate; it's the product's actual stance."

    // MARK: - Legal URLs

    /// Hosted at https://github.com/kashane1/life-clock-legal via GitHub Pages.
    /// Source markdown lives at `docs/products/life-clock/legal/`.
    static let privacyPolicyURL = URL(string: "https://kashane1.github.io/life-clock-legal/privacy-policy.html")!
    /// Custom Life Clock terms (overlay on top of Apple's standard EULA).
    static let termsOfUseURL = URL(string: "https://kashane1.github.io/life-clock-legal/terms-of-use.html")!
    static let supportURL = URL(string: "https://kashane1.github.io/life-clock-legal/support.html")!
}
