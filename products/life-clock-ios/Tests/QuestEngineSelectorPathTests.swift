import XCTest
@testable import LifeClock

/// Phase 5b (V1.6.0+): selector-path tests for `QuestEngine.generateDailyQuests`.
/// The legacy 15-quest path was retired here; the only remaining branches
/// in `generateDailyQuests` are pool-driven select + a deadlock fallback
/// when the pool is missing or empty.
final class QuestEngineSelectorPathTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    private func makeEngine() -> QuestEngine {
        QuestEngine(clock: .fixed(fixedDate))
    }

    private func makeProfile() -> UserProfile {
        UserProfile(birthDate: birthDate, biologicalSex: "female")
    }

    private func loadFixturePool() throws -> QuestPool {
        try QuestPool.loadFromBundle(Bundle.main, basenames: ["fixture"])
    }

    // MARK: - Selector path (fixture pool)

    func testFixturePoolEmitsThreeQuestsOnePerGenre() throws {
        let engine = makeEngine()
        let profile = makeProfile()
        let pool = try loadFixturePool()
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: pool
        )
        XCTAssertEqual(quests.count, 3, "Selector path emits exactly 3 quests (one per genre, hard floor)")
        let fixturePrefixes = ["activity.fixture-", "diet.fixture-", "sleep.fixture-"]
        for quest in quests {
            XCTAssertTrue(
                fixturePrefixes.contains(where: { quest.slug.hasPrefix($0) }),
                "Selector path must emit fixture-pool slugs, got \(quest.slug)"
            )
        }
        let genres = Set(quests.map(\.genre))
        XCTAssertEqual(genres, Set(["activity", "diet", "sleep"]))
    }

    func testEmitsTitleFromPoolToneCopy() throws {
        let engine = makeEngine()
        let profile = makeProfile()
        profile.toneMode = "coach"
        let pool = try loadFixturePool()
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: pool
        )
        let activity = quests.first(where: { $0.genre == "activity" })
        XCTAssertNotNil(activity)
        XCTAssertFalse(activity?.title.isEmpty ?? true)
    }

    // MARK: - Empty / missing pool fallback

    func testEmptyPoolEmitsConsistencyFallback() {
        let engine = makeEngine()
        let profile = makeProfile()
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: QuestPool(quests: [])
        )
        XCTAssertEqual(quests.count, 1)
        XCTAssertEqual(quests.first?.slug, "consistency.open-app-tomorrow.v1")
    }

    func testNilPoolEmitsConsistencyFallback() {
        let engine = makeEngine()
        let profile = makeProfile()
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: nil
        )
        XCTAssertEqual(quests.count, 1)
        XCTAssertEqual(quests.first?.slug, "consistency.open-app-tomorrow.v1")
    }

    // MARK: - Determinism

    func testSelectorPathDeterministicOnSameInputs() throws {
        let engine = makeEngine()
        let profile = makeProfile()
        let pool = try loadFixturePool()
        let a = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil, pool: pool)
        let b = engine.generateDailyQuests(profile: profile, snapshot: nil, habits: nil, pool: pool)
        XCTAssertEqual(a.map(\.slug), b.map(\.slug))
    }
}
