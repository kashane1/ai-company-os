import Foundation
import OSLog

/// Per-screen telemetry contract for the new reveal-onboarding flow.
///
/// **Privacy contract (load-bearing):** keys are public, values are
/// **private**. Default `os_log` interpolation marks dynamic strings as
/// `%{public}s`, which persists in the unified log archive and is
/// retrievable via Console.app, sysdiagnose bundles, MDM log capture,
/// and `log collect`. That's a PII leak vector for sensitive choices
/// (PSS-10 / UCLA-3 / parental ages-at-death). The default impl
/// `OSLogTelemetry` uses `Logger` (OSLog 2.0) with `privacy: .private`
/// on every value parameter to keep raw data out of the public log.
///
/// **Bucketing rule:** raw integer scores MUST be bucketed at the
/// call site BEFORE calling `choiceMade(_:key:valueBucket:)`. Never
/// pass a raw PSS-10, UCLA-3, or parent age-at-death as `valueBucket`.
/// Compute the bucket (low/medium/high) at the call site. A unit
/// test asserts no raw integer ever appears in the log sink.
///
/// See `docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md`
/// Phase 1b for the full rationale.
protocol OnboardingTelemetry {
    func screenAppeared(_ screen: String)
    func screenAdvanced(_ screen: String, durationMs: Int)
    func choiceMade(_ screen: String, key: String, valueBucket: String)
    func dialAdjusted(yearsBucket: String)
    func paywallShown(stage: PaywallStage)
    func paywallDismissed(stage: PaywallStage, reason: PaywallDismissReason)
    func purchased(productID: String)
}

enum PaywallStage: String {
    case primary
}

enum PaywallDismissReason: String {
    case closed
    case ineligibleForIntro
    case purchasedSuccessfully
}

/// Production telemetry sink — writes to unified log via `Logger`.
/// Sensitive values use `privacy: .private` so they don't appear in
/// public log archives.
struct OSLogTelemetry: OnboardingTelemetry {
    private let logger: Logger

    init(subsystem: String = "com.lifeclock.app", category: String = "Onboarding") {
        self.logger = Logger(subsystem: subsystem, category: category)
    }

    func screenAppeared(_ screen: String) {
        logger.info("screenAppeared screen=\(screen, privacy: .public)")
    }

    func screenAdvanced(_ screen: String, durationMs: Int) {
        logger.info("""
            screenAdvanced \
            screen=\(screen, privacy: .public) \
            durationMs=\(durationMs, privacy: .public)
            """)
    }

    func choiceMade(_ screen: String, key: String, valueBucket: String) {
        logger.info("""
            choiceMade \
            screen=\(screen, privacy: .public) \
            key=\(key, privacy: .public) \
            valueBucket=\(valueBucket, privacy: .private)
            """)
    }

    func dialAdjusted(yearsBucket: String) {
        logger.info("""
            dialAdjusted yearsBucket=\(yearsBucket, privacy: .private)
            """)
    }

    func paywallShown(stage: PaywallStage) {
        logger.info("paywallShown stage=\(stage.rawValue, privacy: .public)")
    }

    func paywallDismissed(stage: PaywallStage, reason: PaywallDismissReason) {
        logger.info("""
            paywallDismissed \
            stage=\(stage.rawValue, privacy: .public) \
            reason=\(reason.rawValue, privacy: .public)
            """)
    }

    func purchased(productID: String) {
        // ProductID is NOT PII — it's a public Apple identifier (e.g.
        // "com.lifeclock.pro.annual"). Public-qualified.
        logger.info("purchased productID=\(productID, privacy: .public)")
    }
}

/// In-memory test sink. Records every event as a single string for
/// easy assertion. Used by `OnboardingTelemetryTests` and
/// `OnboardingFunnelTests`.
final class StubTelemetry: OnboardingTelemetry {
    private(set) var events: [String] = []

    func screenAppeared(_ screen: String) {
        events.append("screenAppeared:\(screen)")
    }

    func screenAdvanced(_ screen: String, durationMs: Int) {
        events.append("screenAdvanced:\(screen):\(durationMs)")
    }

    func choiceMade(_ screen: String, key: String, valueBucket: String) {
        events.append("choiceMade:\(screen):\(key):\(valueBucket)")
    }

    func dialAdjusted(yearsBucket: String) {
        events.append("dialAdjusted:\(yearsBucket)")
    }

    func paywallShown(stage: PaywallStage) {
        events.append("paywallShown:\(stage.rawValue)")
    }

    func paywallDismissed(stage: PaywallStage, reason: PaywallDismissReason) {
        events.append("paywallDismissed:\(stage.rawValue):\(reason.rawValue)")
    }

    func purchased(productID: String) {
        events.append("purchased:\(productID)")
    }

    func reset() { events.removeAll() }
}

// MARK: - Bucketing helpers

/// Bucket a PSS-10 score (0–40 range) into one of three labels per Cohen's
/// 1988 cutoffs. Use this at the call site before `choiceMade` to ensure
/// raw scores never enter the log sink.
enum PerceivedStressBucket {
    static func bucket(for score: Int) -> String {
        switch score {
        case 27...: return "high"
        case 14..<27: return "medium"
        default: return "low"
        }
    }
}

/// Bucket a UCLA-3 loneliness score (3–9 range) into one of two labels.
enum LonelinessBucket {
    static func bucket(for score: Int) -> String {
        score >= 6 ? "lonely" : "connected"
    }
}

/// Bucket a parent age-at-death into a coarse band. We never log the
/// actual age — only the band. The bands are wide enough that the
/// individual cannot be reidentified from the bucket alone.
enum ParentLongevityBucket {
    static func bucket(for ageAtDeath: Int) -> String {
        switch ageAtDeath {
        case 90...: return "very_long"
        case 80..<90: return "long"
        case 70..<80: return "average"
        case 60..<70: return "short"
        default: return "very_short"
        }
    }
}

/// Bucket a healthspan-dial adjustment to a coarse +/-Y band so we can
/// learn distribution shape without logging the user's exact dial value.
enum DialAdjustmentBucket {
    static func bucket(for years: Double) -> String {
        let rounded = (years * 2).rounded() / 2  // 0.5-yr granularity
        switch rounded {
        case ..<(-3.0): return "neg5_neg3"
        case (-3.0)..<(-1.0): return "neg3_neg1"
        case (-1.0)..<(-0.25): return "neg1_zero"
        case (-0.25)...0.25: return "zero"
        case 0.25..<1.0: return "zero_pos1"
        case 1.0..<3.0: return "pos1_pos3"
        default: return "pos3_pos5"
        }
    }
}
