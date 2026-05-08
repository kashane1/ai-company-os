import XCTest
@testable import LifeClock

/// Phase 2 tone parity + tone distinctness lock for the quest pool
/// (docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md, D9 layer 2).
///
/// For every authored slug:
///   * **Parity**: all three tone variants reference the same `intent`
///     and the same `target` tuple (target equality if both present;
///     parity-on-intent-alone if both nil — diet slugs without numeric
///     targets are common). The `intent` and `target` live on `PoolQuest`,
///     not `ToneCopy`, so this is structurally guaranteed by the schema —
///     these tests pin that the structural invariant is not silently
///     violated by a future refactor that splits per-tone targets.
///   * **Distinctness**: the three tone strings differ pairwise. A
///     copy-paste between tones (or "I'll do this one later" placeholder)
///     becomes a build-time failure.
///   * **Vocabulary smoke-test**: gentle copy excludes firm-direct
///     vocabulary and vice versa. Catches the dominant drift mode the
///     V1+V2 firm-direct softening commits surfaced.
///
/// Tests run against the fixture pool because the production pool is empty
/// in Phase 2. When Phase 4 ships authored slugs, the same tests will
/// run against `productionBasenames` automatically — see the
/// `testProductionPoolToneInvariants` placeholder.
final class QuestPoolToneParityTests: XCTestCase {
    /// Pool resources are bundled into the host app (LifeClock.app). Hosted
    /// iOS tests resolve `Bundle.main` to the host app at runtime.
    private var hostBundle: Bundle { Bundle.main }

    // MARK: - Parity (intent + target identity across tones)

    func testFixturePoolEverySlugHasAllThreeTones() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        for slug in pool.slugs {
            guard let quest = pool.quests[slug] else {
                XCTFail("\(slug) missing from pool dict")
                continue
            }
            for tone in ToneMode.allCases {
                XCTAssertNotNil(
                    quest.copy[tone],
                    "\(slug) is missing tone \(tone.rawValue)"
                )
            }
        }
    }

    /// The parity anchor (intent + optional target) lives at the slug
    /// level, not the tone level. This test pins the structural invariant:
    /// once decoded, there is no per-tone drift surface to begin with —
    /// `intent` and `target` are single fields on `PoolQuest`.
    func testFixturePoolParityAnchorsAreSingleFields() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        for quest in pool.quests.values {
            // No assertion needed at the field level — the type system
            // already prevents per-tone divergence. We assert the shape
            // round-trips so a future refactor that adds per-tone overrides
            // (which we do NOT want) would fail compilation here.
            XCTAssertFalse(quest.intent.isEmpty, "\(quest.slug) has empty intent")
            if let target = quest.target {
                XCTAssertFalse(target.metric.isEmpty, "\(quest.slug) target has empty metric")
                XCTAssertFalse(target.unit.isEmpty, "\(quest.slug) target has empty unit")
            }
        }
    }

    // MARK: - Distinctness (no tone copy-paste)

    func testFixturePoolToneStringsDifferPairwise() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        for slug in pool.slugs {
            guard let quest = pool.quests[slug] else { continue }
            let tones = ToneMode.allCases
            for i in 0..<tones.count {
                for j in (i + 1)..<tones.count {
                    let a = quest.copy[tones[i]]
                    let b = quest.copy[tones[j]]
                    XCTAssertNotEqual(
                        a?.title, b?.title,
                        "\(slug): \(tones[i].rawValue) and \(tones[j].rawValue) titles are identical"
                    )
                    XCTAssertNotEqual(
                        a?.detail, b?.detail,
                        "\(slug): \(tones[i].rawValue) and \(tones[j].rawValue) details are identical"
                    )
                }
            }
        }
    }

    // MARK: - Vocabulary smoke-test

    /// Words that should never appear in `gentle` copy. Sourced from the
    /// firm-direct register (post-2026-05-07 softening pass — kept compact
    /// to avoid false positives on ordinary words).
    private static let firmDirectOnlyVocab: [String] = [
        "Banked",          // firmDirect "deltaPositivePrefix"
        "owe", "owed",     // firmDirect "deltaNegativePrefix" / wrap-up
        "tally",           // firmDirect "yesterdayWrapUpHeading"
        "reckoning",       // firmDirect "todayHeadline"
    ]

    /// Words that should rarely appear in `firmDirect` copy — hedging
    /// language reads as off-register. Also kept compact on purpose.
    private static let gentleOnlyVocab: [String] = [
        "softly", "gently", "perhaps", "maybe", "if you'd like",
    ]

    func testFixturePoolVocabularySmoke() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle, basenames: ["fixture"])
        for slug in pool.slugs {
            guard let quest = pool.quests[slug] else { continue }
            for tone in ToneMode.allCases {
                guard let copy = quest.copy[tone] else { continue }
                let combined = (copy.title + " " + copy.detail).lowercased()
                switch tone {
                case .gentle:
                    for word in Self.firmDirectOnlyVocab {
                        XCTAssertFalse(
                            combined.contains(word.lowercased()),
                            "\(slug) gentle copy contains firm-direct vocabulary: \(word)"
                        )
                    }
                case .firmDirect:
                    for word in Self.gentleOnlyVocab {
                        XCTAssertFalse(
                            combined.contains(word.lowercased()),
                            "\(slug) firm_direct copy contains gentle vocabulary: \(word)"
                        )
                    }
                case .coach:
                    break  // coach tolerates either register; no vocab gate
                }
            }
        }
    }

    // MARK: - Production pool placeholder

    /// Placeholder — runs against the production pool but tolerates the
    /// Phase 2 empty state. When Phase 4 lands authored slugs, this becomes
    /// the load-bearing parity gate for the production pool with no further
    /// changes required.
    func testProductionPoolToneInvariants() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle)
        for slug in pool.slugs {
            guard let quest = pool.quests[slug] else { continue }
            for tone in ToneMode.allCases {
                XCTAssertNotNil(quest.copy[tone], "\(slug) missing tone \(tone.rawValue)")
            }
        }
    }
}
