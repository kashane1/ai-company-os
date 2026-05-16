import XCTest
@testable import LifeClock

/// Pins `ProPerks.perks` — the single source of truth consumed verbatim
/// by `PaywallSheet.header`, `PaywallPrimaryView.proPerks` (the
/// onboarding-terminal paywall, PV-P1), and `ProfileView.proPerks` — to
/// the strings in MONETIZATION.md § Pro Annual "Unlocks (v1, shipped)".
///
/// App Review's value-claim guard requires marketing copy to match what
/// the app delivers; the three pitch surfaces never re-type the strings
/// (they iterate `ProPerks.perks`), so this test is the lockstep guard:
/// any edit to the single source of truth that drifts from
/// MONETIZATION.md fails here, forcing the doc + audit log to move in
/// lockstep (pro-value-backlog 2026-05-15 PV-P1).
final class ProPerksTests: XCTestCase {
    func testPerksMatchMonetizationProAnnualVerbatim() {
        let expected: [ProPerks.Perk] = [
            .init(title: "Full daily history",
                  detail: "every past day, drillable"),
            .init(title: "Weekly drivers + next-best lever",
                  detail: "the deeper breakdown in History"),
            .init(title: "Correction power",
                  detail: "override imported Apple Health values you know are wrong"),
            .init(title: "Custom Today's Plan",
                  detail: "pick the daily-plan actions that fit your life"),
            .init(title: "Deeper trend breakdown",
                  detail: "the Future-tab What-If Simulator"),
        ]

        XCTAssertEqual(
            ProPerks.perks.count, expected.count,
            "ProPerks must enumerate exactly the 5 v1-shipped Pro Annual unlocks"
        )
        for (actual, want) in zip(ProPerks.perks, expected) {
            XCTAssertEqual(actual.title, want.title,
                           "perk title drifted from MONETIZATION § Pro Annual")
            XCTAssertEqual(actual.detail, want.detail,
                           "perk detail drifted from MONETIZATION § Pro Annual")
        }
    }
}
