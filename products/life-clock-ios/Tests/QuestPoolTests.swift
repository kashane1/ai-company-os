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

    /// Current Phase 4 sub-phase shape. Updates on each landing; pinned
    /// here so unintentional content drift is a test failure.
    /// Phase 4c state: all three genres authored (30 each = 90 slugs).
    func testProductionPoolPhase4cShape() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle)
        XCTAssertEqual(
            pool.quests(in: .activity).count,
            30,
            "Phase 4a expects 30 authored activity slugs"
        )
        XCTAssertEqual(
            pool.quests(in: .diet).count,
            30,
            "Phase 4b expects 30 authored diet slugs"
        )
        XCTAssertEqual(
            pool.quests(in: .sleep).count,
            30,
            "Phase 4c expects 30 authored sleep slugs"
        )
        XCTAssertEqual(
            pool.quests.count,
            90,
            "Production pool should hold exactly 90 authored slugs after Phase 4c"
        )
    }

    func testProductionPoolHasNoSlugCollisions() throws {
        // loadFromBundle throws .duplicateSlug if collision detected; this
        // test pins that contract so authoring can't introduce a silent
        // collision.
        XCTAssertNoThrow(try QuestPool.loadFromBundle(hostBundle))
    }

    /// Expected intents per genre (Phase 4 plan §4.1). Single source of
    /// truth for the per-genre coverage tests below; lift to a Swift
    /// constant if a future authoring tool needs to consume it.
    private static let activityIntents: Set<String> = [
        "cardio", "strength", "steps", "break-up-sitting", "outdoor",
        "mobility", "neat", "recovery-walk", "balance", "deload-walk",
    ]
    private static let dietIntents: Set<String> = [
        "macro-shift", "portion", "hydration", "processed-cut", "vice-cut",
        "timing", "quality-upgrade", "mindful-eating", "swap", "pre-meal-prep",
    ]
    private static let sleepIntents: Set<String> = [
        "wind-down", "consistency", "environment", "pre-bed-stimulant-cut",
        "screen-cut", "recovery-aid", "nap-discipline", "morning-light",
        "late-meal-cut", "hydration-timing",
    ]

    private func assertIntentGridFullyCovered(
        _ quests: [PoolQuest],
        expected: Set<String>,
        genre: String
    ) {
        let countsByIntent = Dictionary(grouping: quests, by: { $0.intent })
            .mapValues(\.count)
        XCTAssertEqual(
            Set(countsByIntent.keys), expected,
            "\(genre) intent set drifted from the §4.1 grid"
        )
        for (intent, count) in countsByIntent {
            XCTAssertEqual(
                count, 3,
                "\(genre) intent \"\(intent)\" should have 3 slugs, has \(count)"
            )
        }
    }

    func testProductionActivityIntentGridIsFullyCovered() throws {
        // Phase 4a §4.1 intent grid: 10 intents × 3 slugs each = 30.
        let pool = try QuestPool.loadFromBundle(hostBundle)
        assertIntentGridFullyCovered(
            pool.quests(in: .activity),
            expected: Self.activityIntents,
            genre: "Activity"
        )
    }

    func testProductionDietIntentGridIsFullyCovered() throws {
        // Phase 4b §4.1 intent grid.
        let pool = try QuestPool.loadFromBundle(hostBundle)
        assertIntentGridFullyCovered(
            pool.quests(in: .diet),
            expected: Self.dietIntents,
            genre: "Diet"
        )
    }

    func testProductionSleepIntentGridIsFullyCovered() throws {
        // Phase 4c §4.1 intent grid.
        let pool = try QuestPool.loadFromBundle(hostBundle)
        assertIntentGridFullyCovered(
            pool.quests(in: .sleep),
            expected: Self.sleepIntents,
            genre: "Sleep"
        )
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


    // MARK: - Vocabulary lock (exclusion-group typo gate)

    /// Phase 4a §4.2 locks 7 exclusion-group names. A typo in `activity.json`
    /// (e.g. `meal-anchor` instead of `meal-adjacent`) would silently
    /// degrade the conflict pass to a no-op without failing any other
    /// test. This gate keeps the JSON in sync with the documented vocab.
    /// New groups should land via a vocab-doc update + a one-line addition
    /// here, in the same PR.
    private static let lockedExclusionGroups: Set<String> = [
        "meal-adjacent",
        "evening-energy",
        "pre-bed-stimulant",
        "morning-cardio",
        "intense-exertion",
        "screen-time",
        "meal-timing",
    ]

    func testProductionPoolExclusionGroupsAreInLockedVocabulary() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle)
        for quest in pool.quests.values {
            for group in quest.exclusionGroups {
                XCTAssertTrue(
                    Self.lockedExclusionGroups.contains(group),
                    "\(quest.slug) uses unknown exclusion group \"\(group)\". " +
                    "Either fix the typo or extend QuestPoolTests.lockedExclusionGroups + quest-pool-vocab.md."
                )
            }
        }
    }

    // MARK: - Cold-start safety

    /// Every genre with authored content must have at least one slug
    /// reachable for a default cold-start user (no smoking, no drinking,
    /// no strength routine, day 0). Otherwise the selector skips the
    /// genre entirely on day 1 — a regression of the genre-floor invariant.
    /// Phase 4a only authors activity, so this gate is activity-scoped
    /// for now; Phase 4b/c will widen it.
    func testActivityIsReachableForDefaultColdStartProfile() throws {
        try assertGenreReachableForColdStart(.activity)
    }

    func testDietIsReachableForDefaultColdStartProfile() throws {
        try assertGenreReachableForColdStart(.diet)
    }

    func testSleepIsReachableForDefaultColdStartProfile() throws {
        try assertGenreReachableForColdStart(.sleep)
    }

    private func assertGenreReachableForColdStart(_ genre: Genre) throws {
        let pool = try QuestPool.loadFromBundle(hostBundle)
        let candidates = pool.quests(in: genre)
        guard !candidates.isEmpty else { return }

        let birthDate = Date(timeIntervalSince1970: 631_152_000)
        let coldStart = UserProfile(birthDate: birthDate, biologicalSex: "female")
        coldStart.smokingStatus = "none"
        coldStart.alcoholFrequency = "rare"
        coldStart.strengthFrequencyPerWeek = 0
        coldStart.distinctOpenDays = 0

        let eligible = candidates.filter { QuestSelector.isEligible($0, profile: coldStart) }
        XCTAssertGreaterThan(
            eligible.count, 0,
            "No \(genre.rawValue) slug is reachable for a cold-start non-strength " +
            "non-drinker non-smoker user. Genre would starve the user on day 1."
        )
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
