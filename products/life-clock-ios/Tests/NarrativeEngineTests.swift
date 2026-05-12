import XCTest
@testable import LifeClock

/// V1.7.0 — Future tab plan §Phase 4 / `docs/products/life-clock/future-tab-tone-pools-spec.md`.
///
/// The audit's punch-list flagged the absence of a tone-distinctness
/// guard on the long-form narrative. T3/T4 of the follow-up
/// (todayTrajectoryPeek strengthening + slot-filled FreeNarrativeLine)
/// explicitly leaned on the invariant; this file pins it in code so a
/// future copy edit can't quietly collapse two tones to near-identical
/// strings.
///
/// Invariants tested:
///
///   * All four paragraphs are emitted for every tone.
///   * For each paragraph slot, the Jaccard distance between any two
///     tones' token sets is ≥ 0.30. (Per the audit's "≥30% token diff"
///     threshold.)
///   * No mortality lexicon ("die", "death", "mori", "expire",
///     "ending", "lifespan-shortening") leaks into any paragraph —
///     the mortality reframe lives in support copy, never in the
///     Pro reflection.
final class NarrativeEngineTests: XCTestCase {

    // MARK: - Fixture builder

    private func compose(tone: ToneMode) -> NarrativeEngine.Narrative {
        // Both windows have data; this week trends positive (sleep up,
        // extras flat) so the dominant driver + drag selection is
        // deterministic across tones.
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let thisWeekSnaps = (0..<7).map { offset in
            snapshot(
                date: now.addingTimeInterval(Double(-offset) * 86_400),
                sleep: 7.6, steps: 9_500, exercise: 35
            )
        }
        let priorWeekSnaps = (7..<14).map { offset in
            snapshot(
                date: now.addingTimeInterval(Double(-offset) * 86_400),
                sleep: 6.8, steps: 7_500, exercise: 20
            )
        }
        let thisWeekHabits = (0..<7).map { offset -> HabitLog in
            let h = HabitLog(date: now.addingTimeInterval(Double(-offset) * 86_400))
            h.alcoholLevel = offset < 3 ? "heavy" : "light"
            h.wholeFoodMeal = "yes"
            return h
        }
        let priorWeekHabits = (7..<14).map { offset -> HabitLog in
            let h = HabitLog(date: now.addingTimeInterval(Double(-offset) * 86_400))
            h.alcoholLevel = "none"
            h.wholeFoodMeal = "yes"
            return h
        }
        return NarrativeEngine.compose(
            snapshots: thisWeekSnaps,
            priorWeekSnapshots: priorWeekSnaps,
            habits: thisWeekHabits,
            priorWeekHabits: priorWeekHabits,
            baseline: 85,
            currentAge: 35,
            tone: tone,
            weekEnd: now
        )
    }

    // MARK: - Structural

    func testAllFourParagraphsEmittedForEveryTone() {
        for tone: ToneMode in [.gentle, .coach, .firmDirect] {
            let n = compose(tone: tone)
            for paragraph in NarrativeEngine.Paragraph.allCases {
                let body = n.paragraphs[paragraph] ?? ""
                XCTAssertFalse(body.isEmpty,
                               "tone=\(tone) missing paragraph \(paragraph)")
                XCTAssertGreaterThan(body.count, 5,
                                     "tone=\(tone) paragraph \(paragraph) is suspiciously short: \(body)")
            }
            XCTAssertEqual(n.ordered.count, 4,
                           "ordered narrative must include all four paragraphs")
        }
    }

    func testSubheadIsToneConditional() {
        let g = compose(tone: .gentle).subhead
        let c = compose(tone: .coach).subhead
        let f = compose(tone: .firmDirect).subhead
        XCTAssertNotEqual(g, c)
        XCTAssertNotEqual(c, f)
        XCTAssertNotEqual(g, f)
    }

    // MARK: - Tone distinctness invariant

    func testTonesDifferEnoughPerParagraph() {
        let g = compose(tone: .gentle)
        let c = compose(tone: .coach)
        let f = compose(tone: .firmDirect)
        for paragraph in NarrativeEngine.Paragraph.allCases {
            let gentleTokens = tokens(g.paragraphs[paragraph] ?? "")
            let coachTokens = tokens(c.paragraphs[paragraph] ?? "")
            let firmTokens = tokens(f.paragraphs[paragraph] ?? "")
            assertJaccardDistance(gentleTokens, coachTokens, paragraph: paragraph, pair: "gentle/coach")
            assertJaccardDistance(coachTokens, firmTokens, paragraph: paragraph, pair: "coach/firm")
            assertJaccardDistance(gentleTokens, firmTokens, paragraph: paragraph, pair: "gentle/firm")
        }
    }

    // MARK: - Mortality lexicon

    func testNoMortalityLexiconInAnyParagraph() {
        // The Pro reflection is forward-looking. Mortality reframes
        // belong in support moments, never here.
        let banned = [
            "die", "died", "dying", "death", "deaths",
            "mori", "memento",
            "expire", "expired",
            "lifespan-shortening", "shorten",
        ]
        for tone: ToneMode in [.gentle, .coach, .firmDirect] {
            let n = compose(tone: tone)
            let blob = (n.subhead + " " + n.ordered.joined(separator: " ")).lowercased()
            for term in banned {
                XCTAssertFalse(
                    blob.contains(term),
                    "tone=\(tone) leaked mortality term \"\(term)\": \(blob)"
                )
            }
        }
    }

    // MARK: - Helpers

    private func tokens(_ s: String) -> Set<String> {
        let lowered = s.lowercased()
        // Split on whitespace + common punctuation; drop empties.
        let separators = CharacterSet.whitespacesAndNewlines
            .union(.punctuationCharacters)
            .union(.symbols)
        return Set(
            lowered
                .components(separatedBy: separators)
                .filter { !$0.isEmpty }
        )
    }

    private func assertJaccardDistance(
        _ a: Set<String>,
        _ b: Set<String>,
        paragraph: NarrativeEngine.Paragraph,
        pair: String,
        threshold: Double = 0.30,
        file: StaticString = #file,
        line: UInt = #line
    ) {
        guard !a.isEmpty || !b.isEmpty else {
            XCTFail("empty token sets for paragraph \(paragraph) pair \(pair)",
                    file: file, line: line)
            return
        }
        let intersection = a.intersection(b).count
        let union = a.union(b).count
        let similarity = union == 0 ? 1.0 : Double(intersection) / Double(union)
        let distance = 1.0 - similarity
        XCTAssertGreaterThanOrEqual(
            distance, threshold,
            "tone distinctness violated: paragraph=\(paragraph), pair=\(pair), distance=\(distance) (a=\(a.sorted()), b=\(b.sorted()))",
            file: file, line: line
        )
    }

    private func snapshot(
        date: Date,
        sleep: Double? = nil,
        steps: Int? = nil,
        exercise: Int? = nil
    ) -> DailyHealthSnapshot {
        let s = DailyHealthSnapshot(date: date)
        s.sleepHours = sleep
        s.stepCount = steps
        s.exerciseMinutes = exercise
        return s
    }
}
