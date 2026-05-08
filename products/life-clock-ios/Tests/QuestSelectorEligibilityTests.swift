import XCTest
@testable import LifeClock

/// Phase 4a tests for the EligibilityFilter restored on `PoolQuest` and
/// wired into `QuestSelector.select(...)` as a hard-filter step before
/// scoring. Field semantics live on `EligibilityFilter`'s doc-comment;
/// these tests exercise each field independently against a synthetic
/// profile.
///
/// The selector is pure, so these tests can construct minimal pools
/// inline rather than loading from disk.
final class QuestSelectorEligibilityTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)
    private let birthDate = Date(timeIntervalSince1970: 631_152_000)

    private func makeProfile(
        smokingStatus: String = "none",
        alcoholFrequency: String = "rare",
        strengthFrequencyPerWeek: Int = 0,
        distinctOpenDays: Int = 30
    ) -> UserProfile {
        let p = UserProfile(birthDate: birthDate, biologicalSex: "female")
        p.smokingStatus = smokingStatus
        p.alcoholFrequency = alcoholFrequency
        p.strengthFrequencyPerWeek = strengthFrequencyPerWeek
        p.distinctOpenDays = distinctOpenDays
        return p
    }

    private func makeQuest(
        slug: String,
        eligibility: EligibilityFilter?
    ) -> PoolQuest {
        PoolQuest(
            slug: slug,
            genre: .activity,
            intent: "test",
            target: nil,
            copy: [
                .gentle:     ToneCopy(title: "g\(slug)",  detail: "g detail"),
                .coach:      ToneCopy(title: "c\(slug)",  detail: "c detail"),
                .firmDirect: ToneCopy(title: "fd\(slug)", detail: "fd detail"),
            ],
            exclusionGroups: [],
            eligibility: eligibility
        )
    }

    // MARK: - isEligible(_:profile:)

    func testNilEligibilityIsAlwaysReachable() {
        let quest = makeQuest(slug: "activity.no-filter.v1", eligibility: nil)
        let p = makeProfile()
        XCTAssertTrue(QuestSelector.isEligible(quest, profile: p))
    }

    func testRequiresSmokerExcludesNonSmokers() {
        let quest = makeQuest(
            slug: "activity.smoker-only.v1",
            eligibility: EligibilityFilter(requiresSmoker: true)
        )
        XCTAssertFalse(QuestSelector.isEligible(
            quest,
            profile: makeProfile(smokingStatus: "none")
        ))
        XCTAssertTrue(QuestSelector.isEligible(
            quest,
            profile: makeProfile(smokingStatus: "daily")
        ))
    }

    func testRequiresSmokerFalseExcludesSmokers() {
        let quest = makeQuest(
            slug: "activity.non-smoker-only.v1",
            eligibility: EligibilityFilter(requiresSmoker: false)
        )
        XCTAssertTrue(QuestSelector.isEligible(
            quest,
            profile: makeProfile(smokingStatus: "none")
        ))
        XCTAssertFalse(QuestSelector.isEligible(
            quest,
            profile: makeProfile(smokingStatus: "social")
        ))
    }

    func testRequiresDrinkerHandlesRareAndNoneAsLightDrinker() {
        let quest = makeQuest(
            slug: "activity.drinker-only.v1",
            eligibility: EligibilityFilter(requiresDrinker: true)
        )
        // "none" and "rare" are both light → quest excluded
        XCTAssertFalse(QuestSelector.isEligible(
            quest,
            profile: makeProfile(alcoholFrequency: "none")
        ))
        XCTAssertFalse(QuestSelector.isEligible(
            quest,
            profile: makeProfile(alcoholFrequency: "rare")
        ))
        // "weekly" / "daily" → drinker → included
        XCTAssertTrue(QuestSelector.isEligible(
            quest,
            profile: makeProfile(alcoholFrequency: "weekly")
        ))
        XCTAssertTrue(QuestSelector.isEligible(
            quest,
            profile: makeProfile(alcoholFrequency: "daily")
        ))
    }

    func testRequiresStrengthRoutineGatesByFrequency() {
        let quest = makeQuest(
            slug: "activity.has-strength-routine.v1",
            eligibility: EligibilityFilter(requiresStrengthRoutine: true)
        )
        XCTAssertFalse(QuestSelector.isEligible(
            quest,
            profile: makeProfile(strengthFrequencyPerWeek: 0)
        ))
        XCTAssertTrue(QuestSelector.isEligible(
            quest,
            profile: makeProfile(strengthFrequencyPerWeek: 2)
        ))
    }

    func testColdStartReachableFalseExcludesEarlyDays() {
        let quest = makeQuest(
            slug: "activity.cold-start-blocked.v1",
            eligibility: EligibilityFilter(coldStartReachable: false)
        )
        // Day 0–6: blocked
        XCTAssertFalse(QuestSelector.isEligible(
            quest,
            profile: makeProfile(distinctOpenDays: 0)
        ))
        XCTAssertFalse(QuestSelector.isEligible(
            quest,
            profile: makeProfile(distinctOpenDays: 6)
        ))
        // Day 7+: unblocked (matches discoveryDamp saturation point)
        XCTAssertTrue(QuestSelector.isEligible(
            quest,
            profile: makeProfile(distinctOpenDays: 7)
        ))
        XCTAssertTrue(QuestSelector.isEligible(
            quest,
            profile: makeProfile(distinctOpenDays: 30)
        ))
    }

    func testColdStartReachableTrueIsAlwaysOK() {
        // Default. Records intent without gating selection.
        let quest = makeQuest(
            slug: "activity.cold-start-fine.v1",
            eligibility: EligibilityFilter(coldStartReachable: true)
        )
        XCTAssertTrue(QuestSelector.isEligible(
            quest,
            profile: makeProfile(distinctOpenDays: 0)
        ))
    }

    // MARK: - select() integration: filter takes effect end-to-end

    func testSelectExcludesFilteredSlugsBeforeScoring() {
        let p = makeProfile(strengthFrequencyPerWeek: 0, distinctOpenDays: 30)
        let strength = makeQuest(
            slug: "activity.gated-strength.v1",
            eligibility: EligibilityFilter(requiresStrengthRoutine: true)
        )
        let walk = makeQuest(slug: "activity.unrestricted-walk.v1", eligibility: nil)
        let pool = QuestPool(quests: [strength, walk])
        let picks = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.8],
            needWeight: [.activity: 1.0],
            profile: p,
            today: fixedDate,
            events: []
        )
        // Only the unrestricted slug should survive into the picks.
        XCTAssertEqual(picks.map(\.slug), ["activity.unrestricted-walk.v1"])
    }

    func testSelectSkipsGenreEntirelyWhenAllFiltered() {
        let p = makeProfile(strengthFrequencyPerWeek: 0)
        let strength = makeQuest(
            slug: "activity.only-gated.v1",
            eligibility: EligibilityFilter(requiresStrengthRoutine: true)
        )
        let pool = QuestPool(quests: [strength])
        let picks = QuestSelector.select(
            pool: pool,
            affinity: [.activity: 0.5],
            needWeight: [.activity: 1.0],
            profile: p,
            today: fixedDate,
            events: []
        )
        // Genre with no eligible candidates contributes nothing — caller
        // (LifeClockStore) layers in the consistency fallback.
        XCTAssertTrue(picks.isEmpty)
    }
}
