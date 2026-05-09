import XCTest
import SwiftData
@testable import LifeClock

/// Phase 3 of the quest-pool affinity engine
/// (docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md).
///
/// Selector invariants pinned:
///   - Always emits one slug per genre when the pool is non-empty (hard floor).
///   - Slug-ascending tiebreak when multiple candidates tie on score.
///   - Exclusion-group conflicts resolved by dropping the lower-scored side.
///   - Recency decay reduces a recently-shown slug's score (non-zero ≠ 1).
///   - Discovery damp produces values in [0.3, 1.0] across day 0..7+.
///
/// EOD resolver invariants pinned:
///   - Fills `passed_over` on unresolved `shown` rows.
///   - Fills `abandoned` on unresolved `picked` rows.
///   - Skips when terminal kind already exists for (date, slug).
///   - G22 guard: skips `shown` resolution when `replaced` exists for same key.
///   - Idempotent on double-fire.
///   - Bounded walk caps at 30 days; older rows bulk-resolved.
final class QuestSelectorTests: XCTestCase {
    private let day1 = Date(timeIntervalSince1970: 1_800_000_000)
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    private func dayOffset(_ days: Int) -> Date {
        Calendar.current.date(byAdding: .day, value: days, to: day1)!
    }

    private func makeProfile(distinctOpenDays: Int = 7) -> UserProfile {
        let p = UserProfile(birthDate: birthDate)
        p.distinctOpenDays = distinctOpenDays
        return p
    }

    private func loadFixturePool() throws -> QuestPool {
        try QuestPool.loadFromBundle(Bundle.main, basenames: ["fixture"])
    }

    // MARK: - Discovery damp

    func testDiscoveryDampDay0Returns0_3() {
        XCTAssertEqual(QuestSelector.discoveryDamp(distinctOpenDays: 0), 0.3, accuracy: 1e-6)
    }

    func testDiscoveryDampDay7Returns1_0() {
        XCTAssertEqual(QuestSelector.discoveryDamp(distinctOpenDays: 7), 1.0, accuracy: 1e-6)
    }

    func testDiscoveryDampDay100StaysAt1_0() {
        XCTAssertEqual(QuestSelector.discoveryDamp(distinctOpenDays: 100), 1.0, accuracy: 1e-6)
    }

    func testDiscoveryDampDay3InterpolatesLinearly() {
        // 0.3 + 0.7 × 3/7 = 0.3 + 0.3 = 0.6
        XCTAssertEqual(QuestSelector.discoveryDamp(distinctOpenDays: 3), 0.6, accuracy: 1e-6)
    }

    // MARK: - latestShownBySlug precompute

    func testLatestShownBySlugReturnsLatestPerSlug() {
        let events: [QuestEvent] = [
            QuestEvent(date: dayOffset(0), slug: "activity.x.v1", genre: "activity", kind: "shown"),
            QuestEvent(date: dayOffset(2), slug: "activity.x.v1", genre: "activity", kind: "shown"),
            QuestEvent(date: dayOffset(1), slug: "activity.x.v1", genre: "activity", kind: "shown"),
            QuestEvent(date: dayOffset(0), slug: "diet.y.v1", genre: "diet", kind: "shown"),
        ]
        let result = QuestSelector.latestShownBySlug(events: events)
        XCTAssertEqual(result["activity.x.v1"], dayOffset(2))
        XCTAssertEqual(result["diet.y.v1"], dayOffset(0))
    }

    func testLatestShownBySlugIgnoresNonShownKinds() {
        let events: [QuestEvent] = [
            QuestEvent(date: dayOffset(0), slug: "activity.x.v1", genre: "activity", kind: "completed"),
            QuestEvent(date: dayOffset(0), slug: "activity.y.v1", genre: "activity", kind: "picked"),
        ]
        XCTAssertTrue(QuestSelector.latestShownBySlug(events: events).isEmpty)
    }

    // MARK: - Selector slate invariants

    func testEmitsOneSlugPerGenreOnFixturePool() throws {
        let pool = try loadFixturePool()
        let result = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.5, .diet: 0.5, .sleep: 0.5],
            needWeight: [.activity: 0.6, .diet: 0.6, .sleep: 0.6],
            profile: makeProfile(),
            today: day1,
            events: []
        )
        XCTAssertEqual(result.count, 3)
        XCTAssertEqual(Set(result.map(\.genre)), Set(Genre.allCases))
    }

    func testReturnedSlugsAreAllDistinct() throws {
        let pool = try loadFixturePool()
        let result = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.5, .diet: 0.5, .sleep: 0.5],
            needWeight: [.activity: 0.6, .diet: 0.6, .sleep: 0.6],
            profile: makeProfile(),
            today: day1,
            events: []
        )
        XCTAssertEqual(Set(result.map(\.slug)).count, result.count)
    }

    func testHardGenreFloorEnforcedEvenWhenAffinityIsZero() throws {
        let pool = try loadFixturePool()
        // Activity affinity = 0; selector still picks an activity slug
        // because of the hard floor (one per genre regardless of score).
        let result = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.0, .diet: 0.5, .sleep: 0.5],
            needWeight: [.activity: 0.6, .diet: 0.6, .sleep: 0.6],
            profile: makeProfile(),
            today: day1,
            events: []
        )
        XCTAssertTrue(result.contains { $0.genre == .activity })
    }

    func testDeterministicWithSameInputs() throws {
        let pool = try loadFixturePool()
        let a = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.5, .diet: 0.5, .sleep: 0.5],
            needWeight: [.activity: 0.6, .diet: 0.6, .sleep: 0.6],
            profile: makeProfile(),
            today: day1,
            events: []
        )
        let b = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.5, .diet: 0.5, .sleep: 0.5],
            needWeight: [.activity: 0.6, .diet: 0.6, .sleep: 0.6],
            profile: makeProfile(),
            today: day1,
            events: []
        )
        XCTAssertEqual(a.map(\.slug), b.map(\.slug))
    }

    // MARK: - Tiebreak (G20)

    func testTiebreakIsLexicalSlugOrder() throws {
        let pool = try loadFixturePool()
        // With 0 events, all activity slugs have equal recencyDecay = 1.0.
        // Identical affinity + needWeight → all activity slugs tie on score.
        // Tiebreak: slug-ascending. Activity has fixture-stairs-instead.v1 vs
        // fixture-walk-after-meal.v1 — "stairs-instead" sorts before
        // "walk-after-meal" lexically.
        let result = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.5, .diet: 0.5, .sleep: 0.5],
            needWeight: [.activity: 0.6, .diet: 0.6, .sleep: 0.6],
            profile: makeProfile(),
            today: day1,
            events: []
        )
        let activity = result.first(where: { $0.genre == .activity })
        XCTAssertEqual(activity?.slug, "activity.fixture-stairs-instead.v1")
    }

    // MARK: - Recency decay (G12 / D8)

    func testRecentlyShownSlugIsDeprioritized() throws {
        let pool = try loadFixturePool()
        // Show "stairs-instead" yesterday; selector should prefer
        // walk-after-meal even though both have equal affinity / need.
        let event = QuestEvent(
            date: dayOffset(-1),
            slug: "activity.fixture-stairs-instead.v1",
            genre: "activity",
            kind: "shown"
        )
        let result = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.5, .diet: 0.5, .sleep: 0.5],
            needWeight: [.activity: 0.6, .diet: 0.6, .sleep: 0.6],
            profile: makeProfile(),
            today: day1,
            events: [event]
        )
        let activity = result.first(where: { $0.genre == .activity })
        XCTAssertEqual(activity?.slug, "activity.fixture-walk-after-meal.v1")
    }

    // MARK: - Exclusion-group conflict resolution

    func testExclusionGroupConflictDropsLowerScoredSide() throws {
        // Build a pool where activity and diet share an exclusion group.
        // The fixture pool has activity.fixture-walk-after-meal.v1 with
        // exclusionGroup "meal-adjacent" and diet.fixture-add-protein.v1
        // also with "meal-adjacent". With identical affinity + need,
        // activity wins on slug-ascending tiebreak inside its genre,
        // then diet has to pick the OTHER diet slug (water-with-meal,
        // which has no exclusion group).
        let pool = try loadFixturePool()
        // Force the higher score onto the meal-adjacent activity slug
        // by deprioritizing fixture-stairs-instead via recencyDecay.
        let yesterdayShown = QuestEvent(
            date: dayOffset(-1),
            slug: "activity.fixture-stairs-instead.v1",
            genre: "activity",
            kind: "shown"
        )
        let result = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.5, .diet: 0.5, .sleep: 0.5],
            needWeight: [.activity: 0.6, .diet: 0.6, .sleep: 0.6],
            profile: makeProfile(),
            today: day1,
            events: [yesterdayShown]
        )
        // Activity now picks walk-after-meal (recency-decay penalty
        // on stairs-instead). Diet must pick water-with-meal (NOT
        // add-protein, which conflicts with walk-after-meal on
        // "meal-adjacent").
        let diet = result.first(where: { $0.genre == .diet })
        XCTAssertEqual(diet?.slug, "diet.fixture-water-with-meal.v1")
    }

    // MARK: - End-of-day resolver

    private func makeContainer() throws -> ModelContainer {
        let schema = Schema(versionedSchema: LifeClockSchemaV1.self)
        let config = ModelConfiguration(
            "QuestSelectorTest",
            schema: schema,
            isStoredInMemoryOnly: true,
            allowsSave: true,
            cloudKitDatabase: .none
        )
        return try ModelContainer(for: schema, migrationPlan: LifeClockMigrationPlan.self, configurations: [config])
    }

    func testResolverFillsPassedOverOnUnresolvedShownRow() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        let event = QuestEvent(
            date: dayOffset(-1),
            slug: "activity.x.v1",
            genre: "activity",
            kind: "shown"
        )
        context.insert(event)
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)

        let after = try context.fetch(FetchDescriptor<QuestEvent>())
        XCTAssertEqual(after.first?.resolvedKind, "passed_over")
        XCTAssertNotNil(after.first?.resolvedAt)
    }

    func testResolverFillsAbandonedOnUnresolvedPickedRow() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        let event = QuestEvent(
            date: dayOffset(-1),
            slug: "diet.x.v1",
            genre: "diet",
            kind: "picked"
        )
        context.insert(event)
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)

        let after = try context.fetch(FetchDescriptor<QuestEvent>())
        XCTAssertEqual(after.first?.resolvedKind, "abandoned")
    }

    func testResolverSkipsShownWhenPickedExistsForSameSlug() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        let date = dayOffset(-1)
        let shown = QuestEvent(date: date, slug: "sleep.x.v1", genre: "sleep", kind: "shown")
        let picked = QuestEvent(date: date, slug: "sleep.x.v1", genre: "sleep", kind: "picked")
        context.insert(shown)
        context.insert(picked)
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)

        // The shown row should NOT be resolved (the picked row is
        // its own lifecycle). The picked row resolves to abandoned
        // since no completed exists.
        let fetched = try context.fetch(FetchDescriptor<QuestEvent>()).sorted { $0.kind < $1.kind }
        XCTAssertEqual(fetched.count, 2)
        let pickedRow = fetched.first(where: { $0.kind == "picked" })
        let shownRow = fetched.first(where: { $0.kind == "shown" })
        XCTAssertEqual(pickedRow?.resolvedKind, "abandoned")
        XCTAssertNil(shownRow?.resolvedKind)
    }

    func testResolverSkipsShownWhenReplacedExistsG22() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        let date = dayOffset(-1)
        let shown = QuestEvent(date: date, slug: "activity.x.v1", genre: "activity", kind: "shown")
        let replaced = QuestEvent(date: date, slug: "activity.x.v1", genre: "activity", kind: "replaced")
        context.insert(shown)
        context.insert(replaced)
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)

        // G22 guard: shown row stays unresolved because replaced is
        // already a stronger negative signal — resolving as
        // passed_over would double-count.
        let fetched = try context.fetch(FetchDescriptor<QuestEvent>())
        let shownRow = fetched.first(where: { $0.kind == "shown" })
        XCTAssertNil(shownRow?.resolvedKind)
    }

    func testResolverSkipsPickedWhenCompletedExists() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        let date = dayOffset(-1)
        let picked = QuestEvent(date: date, slug: "diet.y.v1", genre: "diet", kind: "picked")
        let completed = QuestEvent(date: date, slug: "diet.y.v1", genre: "diet", kind: "completed")
        context.insert(picked)
        context.insert(completed)
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)

        let fetched = try context.fetch(FetchDescriptor<QuestEvent>())
        let pickedRow = fetched.first(where: { $0.kind == "picked" })
        XCTAssertNil(pickedRow?.resolvedKind, "Completed picked should NOT resolve to abandoned")
    }

    func testResolverIsIdempotentOnDoubleFire() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        let event = QuestEvent(
            date: dayOffset(-1),
            slug: "activity.x.v1",
            genre: "activity",
            kind: "shown"
        )
        context.insert(event)
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)
        let firstResolved = try context.fetch(FetchDescriptor<QuestEvent>()).first?.resolvedKind
        XCTAssertEqual(firstResolved, "passed_over")

        try QuestSelector.resolveEndOfDay(context: context, today: day1)
        let secondResolved = try context.fetch(FetchDescriptor<QuestEvent>()).first?.resolvedKind
        XCTAssertEqual(secondResolved, "passed_over")  // Still the same — idempotent.
    }

    func testResolverSkipsTodaysRows() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        // Event from TODAY — must not be resolved (the user could still
        // pick or complete this slug before midnight).
        let event = QuestEvent(
            date: day1,
            slug: "activity.x.v1",
            genre: "activity",
            kind: "shown"
        )
        context.insert(event)
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)

        let fetched = try context.fetch(FetchDescriptor<QuestEvent>())
        XCTAssertNil(fetched.first?.resolvedKind, "Today's rows must not be resolved")
    }

    func testResolverWalksMultiDayGap() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        // Three days of unresolved shown events.
        for offset in 1...3 {
            let event = QuestEvent(
                date: dayOffset(-offset),
                slug: "activity.day-\(offset).v1",
                genre: "activity",
                kind: "shown"
            )
            context.insert(event)
        }
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)

        let fetched = try context.fetch(FetchDescriptor<QuestEvent>())
        XCTAssertEqual(fetched.count, 3)
        for event in fetched {
            XCTAssertEqual(event.resolvedKind, "passed_over", "All 3 days should resolve")
        }
    }

    func testResolverBoundedAt30DaysBulkResolvesOlderRows() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        let veryOldEvent = QuestEvent(
            date: dayOffset(-60),    // 60 days ago — beyond the 30-day cap
            slug: "diet.ancient.v1",
            genre: "diet",
            kind: "shown"
        )
        context.insert(veryOldEvent)
        try context.save()

        try QuestSelector.resolveEndOfDay(context: context, today: day1)

        let fetched = try context.fetch(FetchDescriptor<QuestEvent>())
        XCTAssertEqual(fetched.first?.resolvedKind, "passed_over",
            "Rows older than 30 days should be bulk-resolved to passed_over")
    }
}
