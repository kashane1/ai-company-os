import XCTest
@testable import LifeClock

/// Phase 3 of the quest-pool affinity engine
/// (docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md).
///
/// Tests pin the EMA math against synthetic event histories. Failure
/// here means a refactor changed the math without a deliberate retune
/// of `AffinityEngine.alpha` or the signal table — which would silently
/// shift every user's affinity. Numerical comparisons use a tight
/// tolerance (1e-6).
final class AffinityEngineTests: XCTestCase {
    private let day1 = Date(timeIntervalSince1970: 1_800_000_000)
    private func dayOffset(_ days: Int) -> Date {
        Calendar.current.date(byAdding: .day, value: days, to: day1)!
    }

    // MARK: - Initial state

    func testInitialAffinityIs0_5ForEveryGenreOnEmptyHistory() {
        let result = AffinityEngine.computeAffinities(events: [])
        XCTAssertEqual(result[.activity] ?? -1, 0.5, accuracy: 1e-6)
        XCTAssertEqual(result[.diet] ?? -1, 0.5, accuracy: 1e-6)
        XCTAssertEqual(result[.sleep] ?? -1, 0.5, accuracy: 1e-6)
    }

    // MARK: - Single-event signals

    func testCompletedEventNudgesAffinityUpAlphaTowards1() {
        let event = QuestEvent(
            date: day1,
            slug: "activity.fixture-walk-after-meal.v1",
            genre: "activity",
            kind: "completed"
        )
        let result = AffinityEngine.computeAffinities(events: [event])
        // (1 - 0.2 × 1.0) × 0.5 + 0.2 × 1.0 × 1.0 = 0.4 + 0.2 = 0.6
        XCTAssertEqual(result[.activity] ?? -1, 0.6, accuracy: 1e-6)
        // Other genres untouched
        XCTAssertEqual(result[.diet] ?? -1, 0.5, accuracy: 1e-6)
        XCTAssertEqual(result[.sleep] ?? -1, 0.5, accuracy: 1e-6)
    }

    func testReplacedEventNudgesAffinityDown1_5xWeight() {
        let event = QuestEvent(
            date: day1,
            slug: "diet.fixture-water-with-meal.v1",
            genre: "diet",
            kind: "replaced"
        )
        let result = AffinityEngine.computeAffinities(events: [event])
        // (1 - 0.2 × 1.5) × 0.5 + 0.2 × 1.5 × 0.0 = 0.7 × 0.5 + 0 = 0.35
        XCTAssertEqual(result[.diet] ?? -1, 0.35, accuracy: 1e-6)
    }

    func testPickedAbandonedNudgesAffinityDownFullWeight() {
        let event = QuestEvent(
            date: day1,
            slug: "sleep.fixture-wind-down.v1",
            genre: "sleep",
            kind: "picked"
        )
        event.resolvedKind = "abandoned"
        let result = AffinityEngine.computeAffinities(events: [event])
        // (1 - 0.2 × 1.0) × 0.5 + 0.2 × 1.0 × 0.0 = 0.4
        XCTAssertEqual(result[.sleep] ?? -1, 0.4, accuracy: 1e-6)
    }

    func testShownPassedOverNudgesAffinityMildly() {
        let event = QuestEvent(
            date: day1,
            slug: "activity.fixture-stairs-instead.v1",
            genre: "activity",
            kind: "shown"
        )
        event.resolvedKind = "passed_over"
        let result = AffinityEngine.computeAffinities(events: [event])
        // (1 - 0.2 × 0.5) × 0.5 + 0.2 × 0.5 × 0.3 = 0.9 × 0.5 + 0.1 × 0.3 = 0.45 + 0.03 = 0.48
        XCTAssertEqual(result[.activity] ?? -1, 0.48, accuracy: 1e-6)
    }

    // MARK: - Unresolved events have no signal

    func testUnresolvedShownEventDoesNotShiftAffinity() {
        let event = QuestEvent(date: day1, slug: "activity.x.v1", genre: "activity", kind: "shown")
        // resolvedKind == nil
        let result = AffinityEngine.computeAffinities(events: [event])
        XCTAssertEqual(result[.activity] ?? -1, 0.5, accuracy: 1e-6)
    }

    func testUnresolvedPickedEventDoesNotShiftAffinity() {
        let event = QuestEvent(date: day1, slug: "diet.x.v1", genre: "diet", kind: "picked")
        let result = AffinityEngine.computeAffinities(events: [event])
        XCTAssertEqual(result[.diet] ?? -1, 0.5, accuracy: 1e-6)
    }

    // MARK: - Convergence

    func testEMAConvergesToward1OnAllCompletedHistory() {
        var events: [QuestEvent] = []
        for i in 0..<50 {
            events.append(QuestEvent(
                date: dayOffset(i),
                slug: "activity.fixture-walk-after-meal.v1",
                genre: "activity",
                kind: "completed"
            ))
        }
        let result = AffinityEngine.computeAffinities(events: events)
        // After 50 completed events, EMA is very close to 1.0 (0.8^50 × 0.5 + (1 - 0.8^50) × 1)
        XCTAssertGreaterThan(result[.activity] ?? 0, 0.99)
    }

    func testEMAConvergesToward0OnAllReplacedHistory() {
        var events: [QuestEvent] = []
        for i in 0..<50 {
            events.append(QuestEvent(
                date: dayOffset(i),
                slug: "sleep.x.v1",
                genre: "sleep",
                kind: "replaced"
            ))
        }
        let result = AffinityEngine.computeAffinities(events: events)
        // Replaced is 1.5× weight → effective α = 0.3 → faster convergence to 0.
        XCTAssertLessThan(result[.sleep] ?? 1, 0.001)
    }

    // MARK: - Determinism / sort order

    func testEventsSortedByDateBeforeFolding() {
        // Same events, scrambled vs ordered, should produce identical
        // result (the engine sorts internally).
        let inOrder: [QuestEvent] = [
            QuestEvent(date: dayOffset(0), slug: "diet.x.v1", genre: "diet", kind: "completed"),
            QuestEvent(date: dayOffset(1), slug: "diet.y.v1", genre: "diet", kind: "replaced"),
            QuestEvent(date: dayOffset(2), slug: "diet.z.v1", genre: "diet", kind: "completed"),
        ]
        let scrambled: [QuestEvent] = [inOrder[2], inOrder[0], inOrder[1]]
        let resultOrdered = AffinityEngine.computeAffinities(events: inOrder)
        let resultScrambled = AffinityEngine.computeAffinities(events: scrambled)
        XCTAssertEqual(resultOrdered[.diet], resultScrambled[.diet])
    }

    // MARK: - Robustness

    func testUnknownGenreEventIsIgnored() {
        let event = QuestEvent(date: day1, slug: "consistency.foo.v1", genre: "", kind: "completed")
        let result = AffinityEngine.computeAffinities(events: [event])
        // Empty-string genre (the consistency-fallback case) doesn't
        // map to any Genre — event ignored.
        XCTAssertEqual(result[.activity] ?? -1, 0.5, accuracy: 1e-6)
        XCTAssertEqual(result[.diet] ?? -1, 0.5, accuracy: 1e-6)
        XCTAssertEqual(result[.sleep] ?? -1, 0.5, accuracy: 1e-6)
    }

    func testUnknownEventKindIsIgnored() {
        let event = QuestEvent(date: day1, slug: "activity.x.v1", genre: "activity", kind: "unknown")
        let result = AffinityEngine.computeAffinities(events: [event])
        XCTAssertEqual(result[.activity] ?? -1, 0.5, accuracy: 1e-6)
    }

    // MARK: - Signal table

    func testSignalTableMatchesPlan() {
        // Pin the (target, weight) tuples — a refactor that retunes
        // these silently shifts every user's affinity. Failing here
        // is supposed to feel disruptive.
        XCTAssertNotNil(AffinityEngine.signal(for: .completed, resolvedKind: nil))
        XCTAssertEqual(AffinityEngine.signal(for: .completed, resolvedKind: nil)?.target, 1.0)
        XCTAssertEqual(AffinityEngine.signal(for: .completed, resolvedKind: nil)?.weight, 1.0)

        XCTAssertEqual(AffinityEngine.signal(for: .replaced, resolvedKind: nil)?.target, 0.0)
        XCTAssertEqual(AffinityEngine.signal(for: .replaced, resolvedKind: nil)?.weight, 1.5)

        XCTAssertEqual(AffinityEngine.signal(for: .picked, resolvedKind: .abandoned)?.target, 0.0)
        XCTAssertEqual(AffinityEngine.signal(for: .picked, resolvedKind: .abandoned)?.weight, 1.0)
        XCTAssertNil(AffinityEngine.signal(for: .picked, resolvedKind: nil))

        XCTAssertEqual(AffinityEngine.signal(for: .shown, resolvedKind: .passedOver)?.target, 0.3)
        XCTAssertEqual(AffinityEngine.signal(for: .shown, resolvedKind: .passedOver)?.weight, 0.5)
        XCTAssertNil(AffinityEngine.signal(for: .shown, resolvedKind: nil))
    }
}
