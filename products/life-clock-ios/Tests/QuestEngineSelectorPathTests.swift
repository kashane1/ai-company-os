import XCTest
@testable import LifeClock

/// Phase 3c flag-branch tests for `QuestEngine.generateDailyQuests`.
/// Pinned behavior:
///   - Flag off: legacy 15-quest path runs unchanged. Existing
///     `QuestEngineTests` cover this; this file just spot-checks
///     that adding the new optional parameters didn't change
///     the legacy default.
///   - Flag on + non-empty pool: routes through QuestSelector.
///   - Flag on + empty pool (G26): falls back to legacy path
///     gracefully, no consistency-fallback spam.
final class QuestEngineSelectorPathTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    private func makeEngine() -> QuestEngine {
        QuestEngine(clock: .fixed(fixedDate))
    }

    private func makeProfile(useQuestPoolEngine: Bool = false) -> UserProfile {
        let p = UserProfile(birthDate: birthDate, biologicalSex: "female")
        p.useQuestPoolEngine = useQuestPoolEngine
        return p
    }

    private func loadFixturePool() throws -> QuestPool {
        try QuestPool.loadFromBundle(Bundle.main, basenames: ["fixture"])
    }

    // MARK: - Flag-off path (legacy preserved)

    func testFlagOffPreservesLegacyEnginePath() {
        let engine = makeEngine()
        let profile = makeProfile(useQuestPoolEngine: false)
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil
        )
        XCTAssertGreaterThanOrEqual(quests.count, 1)
        XCTAssertLessThanOrEqual(quests.count, 3)
        // Legacy slugs use category prefixes like "movement.*", "sleep.*",
        // "nutrition.*", NOT "activity.*"/"diet.*"/"sleep.*" pool format.
        let legacyPrefixes = ["movement.", "sleep.", "recovery.", "nutrition.", "consistency."]
        for quest in quests {
            XCTAssertTrue(
                legacyPrefixes.contains(where: { quest.slug.hasPrefix($0) }),
                "Flag-off path must emit legacy-prefix slugs, got \(quest.slug)"
            )
        }
    }

    func testFlagOffWithPoolInjectedStillRoutesLegacy() throws {
        let engine = makeEngine()
        let profile = makeProfile(useQuestPoolEngine: false)
        let pool = try loadFixturePool()
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: pool
        )
        // Flag off → pool is ignored → legacy path runs.
        for quest in quests {
            XCTAssertFalse(quest.slug.contains("fixture-"),
                "Flag-off path must not emit fixture-* slugs even with pool injected")
        }
    }

    // MARK: - Flag-on + fixture pool (selector path)

    func testFlagOnRoutesToSelectorPathWithFixturePool() throws {
        let engine = makeEngine()
        let profile = makeProfile(useQuestPoolEngine: true)
        let pool = try loadFixturePool()
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: pool
        )
        XCTAssertEqual(quests.count, 3, "Selector path emits exactly 3 quests (one per genre, hard floor)")
        // All slugs come from the fixture pool format.
        let fixturePrefixes = ["activity.fixture-", "diet.fixture-", "sleep.fixture-"]
        for quest in quests {
            XCTAssertTrue(
                fixturePrefixes.contains(where: { quest.slug.hasPrefix($0) }),
                "Selector path must emit fixture-pool slugs, got \(quest.slug)"
            )
        }
        // Hard floor: every genre represented exactly once.
        let genres = Set(quests.map(\.genre))
        XCTAssertEqual(genres, Set(["activity", "diet", "sleep"]))
    }

    func testFlagOnEmitsTitleFromPoolToneCopy() throws {
        let engine = makeEngine()
        let profile = makeProfile(useQuestPoolEngine: true)
        profile.toneMode = "coach"
        let pool = try loadFixturePool()
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: pool
        )
        // Spot-check: the activity pick should have a non-empty title
        // sourced from the pool's coach-tone copy.
        let activity = quests.first(where: { $0.genre == "activity" })
        XCTAssertNotNil(activity)
        XCTAssertFalse(activity?.title.isEmpty ?? true)
    }

    // MARK: - Empty-pool guard (G26)

    func testFlagOnWithEmptyPoolFallsBackToLegacyPath() throws {
        let engine = makeEngine()
        let profile = makeProfile(useQuestPoolEngine: true)
        let emptyPool = QuestPool(quests: [])
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: emptyPool
        )
        // Empty pool + flag on → graceful fallback to legacy path.
        // Verify slugs are legacy format, NOT 3× consistency-fallback.
        let legacyPrefixes = ["movement.", "sleep.", "recovery.", "nutrition."]
        let nonConsistencyCount = quests.filter { quest in
            legacyPrefixes.contains(where: { quest.slug.hasPrefix($0) })
        }.count
        XCTAssertGreaterThan(
            nonConsistencyCount, 0,
            "Empty-pool fallback must route to legacy path, not 3× consistency-fallback"
        )
    }

    // MARK: - Determinism

    func testSelectorPathDeterministicOnSameInputs() throws {
        let engine = makeEngine()
        let profile = makeProfile(useQuestPoolEngine: true)
        let pool = try loadFixturePool()
        let a = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil, pool: pool)
        let b = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil, pool: pool)
        XCTAssertEqual(a.map(\.slug), b.map(\.slug))
    }
}
