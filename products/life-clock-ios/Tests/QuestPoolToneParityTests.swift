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

    // MARK: - Reachability (Phase 4a §test plan)

    /// Every authored activity slug must be selectable for some realistic
    /// profile + event-history combo. A pool entry that the selector can
    /// never surface is wasted authoring work; this test catches that
    /// failure mode at build time.
    ///
    /// Approach: for each target slug T, build a profile that satisfies T's
    /// eligibility filter, and seed events showing every OTHER activity slug
    /// 30 days ago. T (never shown) has recency 1.0; all others have
    /// recency exp(-30/3.5) ≈ 2e-4. T must win the activity slot.
    func testEveryActivitySlugIsReachable() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle)
        let activity = pool.quests(in: .activity)
        guard !activity.isEmpty else {
            XCTFail("Activity pool empty — Phase 4a authoring expected")
            return
        }

        let today = Date(timeIntervalSince1970: 1_800_000_000)
        let calendar = Calendar.current
        let thirtyDaysAgo = calendar.date(byAdding: .day, value: -30, to: today)!
        let birthDate = Date(timeIntervalSince1970: 631_152_000)

        // Permissive profile: passes every eligibility filter Phase 4a
        // authors. Smoking/drinker booleans are set to "yes" because no
        // 4a slug uses requiresSmoker:false or requiresDrinker:false; if
        // 4b/4c add inverse filters, this profile gets per-slug-tailored.
        let profile = UserProfile(birthDate: birthDate, biologicalSex: "female")
        profile.smokingStatus = "daily"
        profile.alcoholFrequency = "weekly"
        profile.strengthFrequencyPerWeek = 3
        profile.distinctOpenDays = 30

        let activitySlugs = activity.map(\.slug)
        for target in activitySlugs {
            let others = activitySlugs.filter { $0 != target }
            let events = others.map { slug in
                QuestEvent(
                    date: thirtyDaysAgo,
                    slug: slug,
                    genre: "activity",
                    kind: QuestEventKind.shown.rawValue
                )
            }

            let picks = QuestSelector.select(
                pool: pool,
                affinity: [.activity: 0.5, .diet: 0.5, .sleep: 0.5],
                needWeight: [.activity: 1.0, .diet: 1.0, .sleep: 1.0],
                profile: profile,
                today: today,
                events: events
            )
            let activityPick = picks.first(where: { $0.genre == .activity })
            XCTAssertEqual(
                activityPick?.slug, target,
                "Activity slug \"\(target)\" is unreachable: expected to win when all peers shown 30 days ago"
            )
        }
    }

    // MARK: - Production pool (Phase 4a — load-bearing)

    /// All four gates from the Phase 4 plan §4.6 run against the production
    /// pool now that activity is authored. Was a placeholder in Phase 2;
    /// becomes the load-bearing tone-correctness lock from Phase 4a forward.
    func testProductionPoolToneInvariants() throws {
        let pool = try QuestPool.loadFromBundle(hostBundle)
        guard !pool.isEmpty else {
            XCTFail("Production pool is empty — Phase 4a authoring expected")
            return
        }
        for slug in pool.slugs {
            guard let quest = pool.quests[slug] else { continue }

            // Gate 1: every authored slug has all three tones.
            for tone in ToneMode.allCases {
                XCTAssertNotNil(quest.copy[tone], "\(slug) missing tone \(tone.rawValue)")
            }

            // Gate 2: tone strings differ pairwise. A copy-paste between
            // tones is a build failure.
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

            // Gate 3: parity anchors (intent + optional target) are
            // single fields on PoolQuest; the type system already
            // prevents per-tone divergence. Pin the shape so a future
            // refactor adding per-tone overrides fails compilation here.
            XCTAssertFalse(quest.intent.isEmpty, "\(quest.slug) has empty intent")
            if let target = quest.target {
                XCTAssertFalse(target.metric.isEmpty, "\(quest.slug) target has empty metric")
                XCTAssertFalse(target.unit.isEmpty, "\(quest.slug) target has empty unit")
            }

            // Gate 4: vocabulary smoke-test — gentle excludes firm-direct
            // vocab; firm_direct excludes gentle vocab. Catches the
            // dominant tone-drift mode.
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
                    break  // coach tolerates either register
                }
            }
        }
    }
}
