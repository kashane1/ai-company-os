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

    // MARK: - QuickLog narration (vision Q11, 2026-05-11)

    /// Pin the gentle intro headline. The "listen better" framing is the
    /// anti-shame variant of the surface's opening line — softer than
    /// coach's "stay honest" and far softer than firmDirect's
    /// "the clock can't read what you don't tell it."
    func testQuickLogIntroHeadline_GentlePinsListenBetter() {
        XCTAssertEqual(
            ToneMode.gentle.quickLogIntroHeadline,
            "A few quick signals help your Life Clock listen better."
        )
    }

    /// All three tones must keep the anti-shame anchor "no calorie
    /// counting" — the founder pack rejects calorie thinking categorically
    /// (see PRIVACY_COMPLIANCE.md + vision Decided constraints). Any rewrite
    /// that drops this phrase from any tone is a regression.
    func testQuickLogIntroSubheadline_AllTonesPreserveNoCalorieAnchor() {
        for tone in ToneMode.allCases {
            XCTAssertTrue(
                tone.quickLogIntroSubheadline.lowercased().contains("no calorie"),
                "\(tone.rawValue) intro subheadline dropped the no-calorie anchor"
            )
        }
    }

    /// Same anchor for the Rhythm caption (adult-only surface). The May 2
    /// commit introduced this caption; keying it now must preserve the
    /// "no calories, no judgment / no calorie math" framing across all
    /// three tones.
    func testQuickLogRhythmCaption_AllTonesPreserveNoCalorieAnchor() {
        for tone in ToneMode.allCases {
            XCTAssertTrue(
                tone.quickLogRhythmCaption.lowercased().contains("no calorie"),
                "\(tone.rawValue) rhythm caption dropped the no-calorie anchor"
            )
        }
    }

    /// The clear-footer must always explain what gets recomputed — that's
    /// the load-bearing info; the register just shifts. Pin: each tone's
    /// footer references Health / HealthKit data as the fallback source.
    func testQuickLogClearFooter_AllTonesReferenceHealth() {
        for tone in ToneMode.allCases {
            let footer = tone.quickLogClearFooter.lowercased()
            XCTAssertTrue(
                footer.contains("health"),
                "\(tone.rawValue) clear-footer didn't reference HealthKit/Apple Health"
            )
        }
    }

    /// Save CTA state-branches: first-save reads as "save / save / log it",
    /// re-save reads as "update / update / update the log." All six cells
    /// must be distinct from each other within a tone (no first-save ==
    /// re-save collision) and non-empty.
    func testQuickLogSaveCTA_StateBranchProducesDistinctLabelsPerTone() {
        for tone in ToneMode.allCases {
            let firstSave = tone.quickLogSaveCTA(hasExistingHabits: false)
            let reSave = tone.quickLogSaveCTA(hasExistingHabits: true)
            XCTAssertFalse(firstSave.isEmpty)
            XCTAssertFalse(reSave.isEmpty)
            XCTAssertNotEqual(
                firstSave, reSave,
                "\(tone.rawValue) save CTA collapses first-save and re-save into one label"
            )
        }
    }

    // MARK: - todayTrajectoryPeekA11yLabel (VoiceOver pairing for the peek)

    /// Pin the gentle a11y label. VoiceOver reads `<label>. <value>.
    /// Button.` — the label is the noun half of the visible string with
    /// number and arrow stripped, so VO doesn't say "eight seven y two m
    /// right arrow."
    func testTodayTrajectoryPeekA11yLabel_GentleReadsProjectionAhead() {
        XCTAssertEqual(
            ToneMode.gentle.todayTrajectoryPeekA11yLabel,
            "Your projection ahead"
        )
    }

    /// The label must not leak the number, units, or the arrow glyph
    /// across any tone — that's the whole point of pairing it with
    /// `formatProjectionA11y` as `accessibilityValue`.
    func testTodayTrajectoryPeekA11yLabel_NoneLeakNumberOrArrow() {
        for tone in ToneMode.allCases {
            let label = tone.todayTrajectoryPeekA11yLabel
            XCTAssertFalse(
                label.contains("→"),
                "\(tone.rawValue) a11y label contains arrow glyph"
            )
            XCTAssertFalse(
                label.contains("y") && label.range(of: "[0-9]y", options: .regularExpression) != nil,
                "\(tone.rawValue) a11y label leaks a bare-letter year unit"
            )
        }
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

    // MARK: - historyEmptyStateBody (polish-2026-05-11)

    private static let historyEmptyStateVariants: [ToneMode.HistoryEmptyHealthState] = [
        .unavailable, .awaitingAuthorization, .historicalOnly,
        .noRecentData, .availableToday,
    ]

    /// All 15 combinations (5 states × 3 tones) return non-empty copy.
    func testHistoryEmptyStateBody_AllCombosNonEmpty() {
        for tone in ToneMode.allCases {
            for variant in Self.historyEmptyStateVariants {
                let line = tone.historyEmptyStateBody(for: variant)
                XCTAssertFalse(
                    line.trimmingCharacters(in: .whitespaces).isEmpty,
                    "\(tone.rawValue)/\(variant) returned empty copy"
                )
            }
        }
    }

    /// Pairwise tone distinctness per health state — catches copy-paste
    /// drift the same way `QuestPoolToneParityTests` does for the pool.
    func testHistoryEmptyStateBody_TonesDifferPairwise() {
        let tones = ToneMode.allCases
        for variant in Self.historyEmptyStateVariants {
            for i in 0..<tones.count {
                for j in (i + 1)..<tones.count {
                    let a = tones[i].historyEmptyStateBody(for: variant)
                    let b = tones[j].historyEmptyStateBody(for: variant)
                    XCTAssertNotEqual(
                        a, b,
                        "\(variant): \(tones[i].rawValue) and \(tones[j].rawValue) returned identical copy"
                    )
                }
            }
        }
    }

    /// Register guardrail: firmDirect must not lean on the mortality /
    /// scorekeeping lexicon in this card — it's a setup state, not a
    /// scoring moment. Mirrors the gentle/coach/firmDirect vocabulary
    /// split locked by `QuestPoolToneParityTests`.
    func testHistoryEmptyStateBody_FirmDirectAvoidsMortalityLexicon() {
        let banned = ["owed", "owe ", "tally", "reckoning", "in the red", "the cost"]
        for variant in Self.historyEmptyStateVariants {
            let line = ToneMode.firmDirect.historyEmptyStateBody(for: variant).lowercased()
            for word in banned {
                XCTAssertFalse(
                    line.contains(word),
                    "firmDirect/\(variant) used banned vocab '\(word)': \(line)"
                )
            }
        }
    }

    /// Register guardrail: gentle copy avoids platitudes that read as
    /// filler ("every day counts", "small things matter"). Compact list
    /// to avoid false positives on ordinary words.
    func testHistoryEmptyStateBody_GentleAvoidsPlatitudes() {
        let banned = [
            "every day counts",
            "small things matter",
            "you've got this",
            "small steps",
            "small wins",
        ]
        for variant in Self.historyEmptyStateVariants {
            let line = ToneMode.gentle.historyEmptyStateBody(for: variant).lowercased()
            for word in banned {
                XCTAssertFalse(
                    line.contains(word),
                    "gentle/\(variant) used platitude '\(word)': \(line)"
                )
            }
        }
    }

    /// Pin Gentle day-1 (`.availableToday`) — highest-traffic combo now
    /// that the History tab correctly excludes today. Catches accidental
    /// rewrites of the line a brand-new user reads first.
    func testHistoryEmptyStateBody_GentleAvailableTodayPin() {
        XCTAssertEqual(
            ToneMode.gentle.historyEmptyStateBody(for: .availableToday),
            "History fills in after a few days. Today is the first one."
        )
    }

    /// Pin Firm/Direct day-1 — verifies the register stays terse without
    /// drifting into scorekeeping vocabulary.
    func testHistoryEmptyStateBody_FirmDirectAvailableTodayPin() {
        XCTAssertEqual(
            ToneMode.firmDirect.historyEmptyStateBody(for: .availableToday),
            "A few more days. Then History has something to say."
        )
    }

    // MARK: - OverrideSheet snapshot-missing copy (PF-P7, 2026-05-16)

    /// All three tones must return non-empty copy — mirrors the
    /// `overrideNotEntitledMessage` contract for the sibling catch branch.
    func testOverrideNoSnapshotMessage_AllTonesNonEmpty() {
        for tone in ToneMode.allCases {
            XCTAssertFalse(
                tone.overrideNoSnapshotMessage
                    .trimmingCharacters(in: .whitespaces).isEmpty,
                "\(tone.rawValue) returned empty snapshot-missing copy"
            )
        }
    }

    /// Pairwise distinctness — catches copy-paste drift across tones.
    func testOverrideNoSnapshotMessage_TonesDifferPairwise() {
        let tones = ToneMode.allCases
        for i in 0..<tones.count {
            for j in (i + 1)..<tones.count {
                XCTAssertNotEqual(
                    tones[i].overrideNoSnapshotMessage,
                    tones[j].overrideNoSnapshotMessage,
                    "\(tones[i].rawValue) and \(tones[j].rawValue) returned identical copy"
                )
            }
        }
    }

    /// Rubric guardrail: every variant must name the condition (no data
    /// for this day) AND offer a concrete next step (pick a day with
    /// data) — the anti-`empty-state-flat` requirement PF-P7 closes.
    func testOverrideNoSnapshotMessage_AllTonesNameConditionAndNextStep() {
        for tone in ToneMode.allCases {
            let line = tone.overrideNoSnapshotMessage.lowercased()
            XCTAssertTrue(
                line.contains("no data") || line.contains("nothing was logged"),
                "\(tone.rawValue) does not name the empty condition: \(line)"
            )
            XCTAssertTrue(
                line.contains("pick a day with data"),
                "\(tone.rawValue) does not offer a next step: \(line)"
            )
        }
    }

    /// The flat literal must never come back — regression pin for the
    /// exact string PF-P7 removed.
    func testOverrideNoSnapshotMessage_NoFlatLiteral() {
        for tone in ToneMode.allCases {
            XCTAssertNotEqual(
                tone.overrideNoSnapshotMessage,
                "No data for this day yet.",
                "\(tone.rawValue) regressed to the flat literal"
            )
        }
    }
}
