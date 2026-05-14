import Foundation

/// Single source of truth for the Pro feature list.
///
/// Both [PaywallSheet.header](../Features/Paywall/PaywallSheet.swift)
/// (pitch surface for Free users) and
/// [ProfileView.proPerksRecap](../Features/Profile/ProfileView.swift)
/// (quiet always-on recap for active Pro users) consume this list so
/// the two surfaces never drift. Editing the list here is the SAME
/// motion as editing MONETIZATION.md's § Pro Annual section — the
/// strings must match verbatim because App Review's value-claim guard
/// holds the app to what its marketing copy promises.
///
/// Cross-references:
///   * `docs/products/life-clock/MONETIZATION.md` § Pro Annual unlocks
///   * `docs/products/life-clock/pro-value-rule.md` § Justification
///   * `docs/products/life-clock/pro-value-backlog-2026-05-13-standard.md` § P8
enum ProPerks {
    struct Perk {
        let title: String
        let detail: String
    }

    /// Five perks, sourced verbatim from MONETIZATION.md § Pro Annual
    /// "Unlocks (v1, shipped)". Order matches the file. Do not insert
    /// post-v1 features (advanced HealthKit metrics / widgets / AI
    /// summaries) without updating MONETIZATION.md AND the value-claim
    /// audit log in lockstep.
    static let perks: [Perk] = [
        Perk(title: "Full daily history",
             detail: "every past day, drillable"),
        Perk(title: "Weekly drivers + next-best lever",
             detail: "the deeper breakdown in History"),
        Perk(title: "Correction power",
             detail: "override imported Apple Health values you know are wrong"),
        Perk(title: "Custom Today's Plan",
             detail: "pick the daily-plan actions that fit your life"),
        Perk(title: "Deeper trend breakdown",
             detail: "the Future-tab What-If Simulator"),
    ]
}
