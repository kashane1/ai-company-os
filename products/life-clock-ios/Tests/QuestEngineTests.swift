import XCTest
@testable import LifeClock

/// Phase 5b (V1.6.0+): legacy inlined-Quest pool retired. The post-5b
/// invariants are pool-driven and intentionally narrower than the
/// pre-5b suite. The detailed selection-algorithm assertions live in
/// `QuestSelectorTests` + `QuestPoolToneParityTests`; pre-pool
/// behavioral pins (heavy-alcohol reorder, step-goal skip, p50 target,
/// rotating nutrition pool) are removed because the underlying code
/// paths no longer exist.
final class QuestEngineTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    private func makeEngine() -> QuestEngine {
        QuestEngine(clock: .fixed(fixedDate))
    }

    private func makeProfile() -> UserProfile {
        UserProfile(birthDate: birthDate, biologicalSex: "female")
    }

    private func loadProductionPool() throws -> QuestPool {
        try QuestPool.loadFromBundle(Bundle.main)
    }

    // MARK: - Quest count invariant

    func testReturnsBetweenOneAndThreeQuests() throws {
        let engine = makeEngine()
        let profile = makeProfile()
        let pool = try loadProductionPool()
        let quests = engine.generateDailyQuests(
            profile: profile,
            snapshot: nil,
            habits: nil,
            pool: pool
        )
        XCTAssertGreaterThanOrEqual(quests.count, 1)
        XCTAssertLessThanOrEqual(quests.count, 3)
    }

    // MARK: - Determinism

    func testSameInputsProduceSameQuests() throws {
        let engine = makeEngine()
        let profile = makeProfile()
        let pool = try loadProductionPool()
        let a = engine.generateDailyQuests(
            profile: profile, snapshot: nil, habits: nil, pool: pool
        )
        let b = engine.generateDailyQuests(
            profile: profile, snapshot: nil, habits: nil, pool: pool
        )
        XCTAssertEqual(a.map(\.slug), b.map(\.slug))
    }

    // MARK: - Empty/missing pool fallback

    func testNilPoolFallsBackToConsistencyFallback() {
        let engine = makeEngine()
        let profile = makeProfile()
        let quests = engine.generateDailyQuests(
            profile: profile, snapshot: nil, habits: nil, pool: nil
        )
        // Missing pool is a build defect in production; emit the deadlock
        // fallback so the user sees something rather than a blank slate.
        XCTAssertEqual(quests.count, 1)
        XCTAssertEqual(quests.first?.slug, "consistency.open-app-tomorrow.v1")
    }

    func testEmptyPoolFallsBackToConsistencyFallback() {
        let engine = makeEngine()
        let profile = makeProfile()
        let emptyPool = QuestPool(quests: [])
        let quests = engine.generateDailyQuests(
            profile: profile, snapshot: nil, habits: nil, pool: emptyPool
        )
        XCTAssertEqual(quests.count, 1)
        XCTAssertEqual(quests.first?.slug, "consistency.open-app-tomorrow.v1")
    }

    // MARK: - Pool slugs only

    func testProductionRunEmitsPoolSlugsOnly() throws {
        let engine = makeEngine()
        let profile = makeProfile()
        let pool = try loadProductionPool()
        let quests = engine.generateDailyQuests(
            profile: profile, snapshot: nil, habits: nil, pool: pool
        )
        let validPrefixes = ["activity.", "diet.", "sleep.", "consistency.open-app-tomorrow"]
        for quest in quests {
            XCTAssertTrue(
                validPrefixes.contains(where: { quest.slug.hasPrefix($0) }),
                "Quest slug \"\(quest.slug)\" is not from the production pool"
            )
        }
    }

    // MARK: - availableQuests (plan editor alternates)

    func testAvailableQuestsReturnsPoolAlternatesPerCategory() throws {
        let engine = makeEngine()
        let profile = makeProfile()
        let pool = try loadProductionPool()
        for category in QuestEngine.Category.allCases {
            let variants = engine.availableQuests(
                for: category,
                profile: profile,
                pool: pool
            )
            XCTAssertFalse(variants.isEmpty, "\(category) returned no variants")
            XCTAssertLessThanOrEqual(variants.count, 3)
            XCTAssertEqual(
                Set(variants.map(\.slug)).count, variants.count,
                "\(category) variants should not contain duplicates"
            )
            for variant in variants {
                XCTAssertEqual(
                    variant.category, category.genre.rawValue,
                    "\(category) variant \(variant.slug) has category \(variant.category)"
                )
            }
        }
    }

    // MARK: - Copy hygiene

    func testNoQuestRecommendsMedicationOrSupplements() throws {
        let engine = makeEngine()
        let profile = makeProfile()
        let pool = try loadProductionPool()
        let quests = engine.generateDailyQuests(
            profile: profile, snapshot: nil, habits: nil, pool: pool
        )
        let blacklist = ["medication", "supplement", "prescribe", "diagnose", "cure"]
        for quest in quests {
            let combined = (quest.title + " " + quest.detail).lowercased()
            for term in blacklist {
                XCTAssertFalse(
                    combined.contains(term),
                    "Quest copy must never mention '\(term)': \(combined)"
                )
            }
        }
    }
}
