import XCTest
@testable import LifeClock

/// Narrow unit coverage for V1.2.0 additions: `todayRescueBody()` and the
/// `RescueLine.shouldShow` predicate. Exhaustive-switch / literal-string
/// tautologies (every mode returns non-empty, all three are distinct)
/// are skipped — Swift's exhaustive switch makes them framework tests
/// that can't fail silently. Code review catches paste-twice mistakes.
final class ToneModeTests: XCTestCase {

    // MARK: - todayRescueBody

    /// Pin the gentle-mode copy. Catches accidental rewrites of the
    /// "log it and move on" line that's the highest-leverage retention
    /// nudge in the rescue family.
    func testTodayRescueBody_GentleReturnsLogItAndMoveOn() {
        XCTAssertEqual(
            ToneMode.gentle.todayRescueBody(),
            "Rough day? Log it and move on. Tomorrow still counts."
        )
    }

    // MARK: - RescueLine.shouldShow

    private func makeLine(
        netDelta: Int,
        dietQuality: String = "",
        rhythm: String = "",
        anchor: String = ""
    ) -> TodayView.RescueLine {
        TodayView.RescueLine(
            netDelta: netDelta,
            dietQuality: dietQuality,
            rhythm: rhythm,
            anchor: anchor,
            tone: .coach
        )
    }

    func testRescueLine_NegativeDeltaPlusRoughDietShows() {
        XCTAssertTrue(makeLine(netDelta: -5, dietQuality: "rough").shouldShow)
    }

    func testRescueLine_NegativeDeltaPlusSkipBingeShows() {
        XCTAssertTrue(makeLine(netDelta: -5, rhythm: "skipBinge").shouldShow)
    }

    func testRescueLine_NegativeDeltaPlusAnchorNoShows() {
        XCTAssertTrue(makeLine(netDelta: -5, anchor: "no").shouldShow)
    }

    /// Net positive delta suppresses the rescue line even when the user
    /// logged a rough diet — HK steps may have driven a big positive day.
    func testRescueLine_PositiveDeltaSuppresses() {
        XCTAssertFalse(makeLine(netDelta: 30, dietQuality: "rough").shouldShow)
    }

    /// Boundary: delta == 0 is not net-negative, so no rescue line.
    func testRescueLine_DeltaZeroSuppresses() {
        XCTAssertFalse(makeLine(netDelta: 0, dietQuality: "rough").shouldShow)
    }

    /// Negative delta without any of the three diet triggers — no rescue
    /// line. (E.g. negative day from poor sleep alone.)
    func testRescueLine_NegativeDeltaWithNoDietTriggersDoesNotShow() {
        XCTAssertFalse(makeLine(netDelta: -15).shouldShow)
        XCTAssertFalse(makeLine(netDelta: -15, dietQuality: "okay", rhythm: "right", anchor: "yes").shouldShow)
    }

    // MARK: - Interpretation movement-qualifier strip (V2 from
    // 2026-05-07 vision-bad-day-three-tones audit)

    /// "<n> steps — sedentary day" must lose the qualifier when piped into
    /// the negative interpretation slot for any tone — otherwise the
    /// sentence stacks two em-dashes (gentle) or reads cruel-adjacent
    /// (firmDirect "...is the cost.").
    func testInterpretationStripsSedentaryDayQualifier() {
        let raw = "1874 steps — sedentary day"
        for tone in ToneMode.allCases {
            let line = tone.todayInterpretationNegative(driverTitle: raw)
            XCTAssertFalse(
                line.contains("— sedentary day"),
                "\(tone.rawValue) interpretation kept the qualifier: \(line)"
            )
            XCTAssertTrue(
                line.contains("1874 steps"),
                "\(tone.rawValue) interpretation dropped the steps count: \(line)"
            )
        }
    }

    /// Same rule for the lighter cousin used at 2.5k–5k steps.
    func testInterpretationStripsLightDayQualifier() {
        let raw = "3200 steps — light day"
        for tone in ToneMode.allCases {
            let line = tone.todayInterpretationNegative(driverTitle: raw)
            XCTAssertFalse(line.contains("— light day"), "\(tone.rawValue): \(line)")
            XCTAssertTrue(line.contains("3200 steps"), "\(tone.rawValue): \(line)")
        }
    }

    /// Driver titles that legitimately contain " — " for non-movement
    /// drivers (e.g. "4.7h sleep — too short") must pass through
    /// untouched — the strip only targets the two movement qualifiers.
    func testInterpretationLeavesNonMovementTitlesUntouched() {
        let raw = "4.7h sleep — too short"
        let line = ToneMode.firmDirect.todayInterpretationNegative(driverTitle: raw)
        XCTAssertTrue(line.contains("4.7h sleep — too short"))
    }

    /// Heavy-alcohol-style titles (no qualifier suffix) round-trip exact.
    func testInterpretationLeavesPlainTitlesExact() {
        let raw = "Heavy alcohol logged"
        let line = ToneMode.coach.todayInterpretationNegative(driverTitle: raw)
        XCTAssertTrue(line.contains("Heavy alcohol logged"))
    }

    // MARK: - questCompletionPayoff (vision Q14)

    /// Pin Gentle. Catches accidental rewrites of the today-focused
    /// tone-keyed payoff line under persist-banked.
    func testQuestCompletionPayoff_GentleEighteenMinutes() {
        XCTAssertEqual(
            ToneMode.gentle.questCompletionPayoff(minutes: 18),
            "Your clock just moved +18 min."
        )
    }

    /// Pin Coach.
    func testQuestCompletionPayoff_CoachEighteenMinutes() {
        XCTAssertEqual(
            ToneMode.coach.questCompletionPayoff(minutes: 18),
            "+18 min on the clock."
        )
    }

    /// Pin Firm/Direct.
    func testQuestCompletionPayoff_FirmDirectEighteenMinutes() {
        XCTAssertEqual(
            ToneMode.firmDirect.questCompletionPayoff(minutes: 18),
            "+18 min. On the clock."
        )
    }

    /// Negative reward shouldn't crash and should pass the formatter
    /// through unchanged. Rare but possible (a deload-day quest).
    func testQuestCompletionPayoff_NegativeMinutesUsesFormatter() {
        for tone in ToneMode.allCases {
            let line = tone.questCompletionPayoff(minutes: -5)
            XCTAssertTrue(line.contains("-5 min"), "\(tone.rawValue): \(line)")
        }
    }
}
