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

    /// Phase 4a state: activity authored (30 slugs), diet + sleep still
    /// empty. Phase 4b/4c will fill diet + sleep; this test updates with
    /// each sub-phase. The expected counts here are also the genre-floor
    /// guarantee for the selector — every genre with authored content
    /// reaches the per-genre minimum coverage.
    func testProductionPoolPhase4aShape() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle)
        XCTAssertEqual(
            pool.quests(in: .activity).count,
            30,
            "Phase 4a expects 30 authored activity slugs"
        )
        XCTAssertEqual(
            pool.quests(in: .diet).count,
            0,
            "Phase 4a leaves diet empty (Phase 4b authors it)"
        )
        XCTAssertEqual(
            pool.quests(in: .sleep).count,
            0,
            "Phase 4a leaves sleep empty (Phase 4c authors it)"
        )
    }

    func testProductionPoolHasNoSlugCollisions() throws {
        // loadFromBundle throws .duplicateSlug if collision detected; this
        // test pins that contract so authoring can't introduce a silent
        // collision.
        XCTAssertNoThrow(try QuestPool.loadFromBundle(hostBundle))
    }

    func testProductionActivityIntentGridIsFullyCovered() throws {
        // Phase 4a §4.1 intent grid: 10 intents × 3 slugs each = 30.
        // Pin the structural shape so authoring drift (one intent with 4
        // slugs, another with 2) shows up as a test failure.
        let pool = try QuestPool.loadFromBundle(hostBundle)
        let activity = pool.quests(in: .activity)
        let countsByIntent = Dictionary(grouping: activity, by: { $0.intent })
            .mapValues(\.count)
        let expectedIntents: Set<String> = [
            "cardio", "strength", "steps", "break-up-sitting", "outdoor",
            "mobility", "neat", "recovery-walk", "balance", "deload-walk",
        ]
        XCTAssertEqual(
            Set(countsByIntent.keys), expectedIntents,
            "Activity intent set drifted from the §4.1 grid"
        )
        for (intent, count) in countsByIntent {
            XCTAssertEqual(
                count, 3,
                "Activity intent \"\(intent)\" should have 3 slugs, has \(count)"
            )
        }
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

    func testDecodeFailsOnEmptyIntent() throws {
        let json = """
        [{
            "slug": "activity.something.v1",
            "genre": "activity",
            "intent": "",
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


    // MARK: - EligibilityFilter (Phase 4a)

    func testEligibilityFilterRoundTripsThroughJSON() throws {
        let json = """
        [{
            "slug": "activity.eligible-test.v1",
            "genre": "activity",
            "intent": "test",
            "exclusionGroups": [],
            "eligibility": {
                "requiresSmoker": true,
                "requiresDrinker": false,
                "requiresStrengthRoutine": null,
                "coldStartReachable": false,
                "timeOfDay": "morning"
            },
            "copy": {
                "gentle":      { "title": "g", "detail": "g detail" },
                "coach":       { "title": "c", "detail": "c detail" },
                "firm_direct": { "title": "f", "detail": "f detail" }
            }
        }]
        """.data(using: .utf8)!
        let entries = try JSONDecoder().decode([PoolQuest].self, from: json)
        let filter = try XCTUnwrap(entries.first?.eligibility)
        XCTAssertEqual(filter.requiresSmoker, true)
        XCTAssertEqual(filter.requiresDrinker, false)
        XCTAssertNil(filter.requiresStrengthRoutine)
        XCTAssertEqual(filter.coldStartReachable, false)
        XCTAssertEqual(filter.timeOfDay, .morning)
    }

    func testEligibilityFilterAbsentMeansNilOnPoolQuest() throws {
        // Fixture pool slugs ship without an eligibility field. A nil
        // value MUST be preserved end-to-end so the selector's
        // "nil = unrestricted" short-circuit holds.
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        for quest in pool.quests.values {
            XCTAssertNil(
                quest.eligibility,
                "Fixture quest \(quest.slug) should have nil eligibility"
            )
        }
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
