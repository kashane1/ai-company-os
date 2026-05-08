import XCTest
@testable import LifeClock

/// Phase 2 schema validity tests for the quest pool
/// (docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md, D9 layer 1).
///
/// Covers:
///   * Production JSONs (`activity.json`, `diet.json`, `sleep.json`) load
///     without throwing. They ship empty in Phase 2 — the test asserts
///     emptiness so any accidental Phase 4 authoring leaks are caught here.
///   * Fixture pool (`fixture.json`) loads, contains the expected slugs,
///     and round-trips through the dictionary lookup.
///   * Slug uniqueness across all production files.
///   * Custom Codable surfaces a missing-tone authoring mistake as a load
///     failure (decode-time guarantee, not render-time nil access).
final class QuestPoolTests: XCTestCase {
    /// Pool resources are bundled into the host app (LifeClock.app), not
    /// the test bundle — see project.yml. Hosted iOS tests resolve
    /// `Bundle.main` to the host app at runtime, so this is the right
    /// reference even inside an XCTest class.
    private var hostBundle: Bundle { Bundle.main }

    // MARK: - Production pool

    func testProductionPoolLoadsAndIsEmptyInPhase2() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle)
        XCTAssertTrue(
            pool.isEmpty,
            """
            Production pool is expected to be empty in Phase 2. \
            Found \(pool.quests.count) entries — Phase 4 authoring landed \
            ahead of schedule, or the basenames list is misconfigured.
            """
        )
    }

    func testProductionPoolHasNoSlugCollisions() throws {
        // loadFromBundle throws .duplicateSlug if collision detected; this
        // test pins that contract so authoring can't introduce a silent
        // collision.
        XCTAssertNoThrow(try QuestPool.loadFromBundle(hostBundle))
    }

    // MARK: - Fixture pool

    func testFixturePoolLoadsAllSixSlugs() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        XCTAssertEqual(pool.quests.count, 6)
        XCTAssertEqual(
            pool.slugs,
            [
                "activity.fixture-stairs-instead.v1",
                "activity.fixture-walk-after-meal.v1",
                "diet.fixture-add-protein.v1",
                "diet.fixture-water-with-meal.v1",
                "sleep.fixture-consistency.v1",
                "sleep.fixture-wind-down.v1",
            ]
        )
    }

    func testFixturePoolHasTwoSlugsPerGenre() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        for genre in Genre.allCases {
            XCTAssertEqual(
                pool.quests(in: genre).count,
                2,
                "Fixture pool genre \(genre.rawValue) should have 2 slugs"
            )
        }
    }

    func testFixturePoolToneResolutionIsConstantTime() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        let copy = pool.copy(for: "activity.fixture-walk-after-meal.v1", tone: .coach)
        XCTAssertEqual(copy?.title, "Walk 10 minutes after dinner")
    }

    func testCopyForUnknownSlugIsNil() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        XCTAssertNil(pool.copy(for: "activity.does-not-exist.v1", tone: .coach))
    }

    // MARK: - Schema-validity decode failures

    func testDecodeFailsWhenAToneIsMissing() throws {
        let json = """
        [{
            "slug": "activity.fixture-broken.v1",
            "genre": "activity",
            "intent": "broken",
            "exclusionGroups": [],
            "copy": {
                "gentle": { "title": "g", "detail": "g" },
                "coach":  { "title": "c", "detail": "c" }
            }
        }]
        """.data(using: .utf8)!
        XCTAssertThrowsError(try JSONDecoder().decode([PoolQuest].self, from: json)) { error in
            // Custom Codable should surface this as DecodingError.dataCorrupted
            // so authoring mistakes never reach the running app.
            guard case DecodingError.dataCorrupted = error else {
                return XCTFail("Expected DecodingError.dataCorrupted, got \(error)")
            }
        }
    }

    func testDecodeFailsOnMalformedSlug() throws {
        let json = """
        [{
            "slug": "ActivityWalkAfterMeal",
            "genre": "activity",
            "intent": "walk-after-meal",
            "exclusionGroups": [],
            "copy": {
                "gentle":      { "title": "g", "detail": "g" },
                "coach":       { "title": "c", "detail": "c" },
                "firm_direct": { "title": "f", "detail": "f" }
            }
        }]
        """.data(using: .utf8)!
        XCTAssertThrowsError(try JSONDecoder().decode([PoolQuest].self, from: json))
    }

    func testDecodeFailsOnUnknownGenre() throws {
        let json = """
        [{
            "slug": "mystery.something.v1",
            "genre": "mystery",
            "intent": "something",
            "exclusionGroups": [],
            "copy": {
                "gentle":      { "title": "g", "detail": "g" },
                "coach":       { "title": "c", "detail": "c" },
                "firm_direct": { "title": "f", "detail": "f" }
            }
        }]
        """.data(using: .utf8)!
        XCTAssertThrowsError(try JSONDecoder().decode([PoolQuest].self, from: json))
    }

    // MARK: - Duplicate-slug detection across files

    func testDuplicateSlugAcrossFilesThrows() throws {
        // Pass the same basename twice — every slug will be seen twice.
        XCTAssertThrowsError(
            try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture", "fixture"])
        ) { error in
            guard case QuestPool.LoadError.duplicateSlug = error else {
                return XCTFail("Expected duplicateSlug, got \(error)")
            }
        }
    }
}
