import Foundation

// MARK: - Pool value types
//
// Phase 2 of the quest-pool affinity engine
// (docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md).
//
// These types describe the on-disk shape of `Resources/QuestPool/*.json` and
// the in-memory `QuestPool`. They are pure value types — no SwiftData, no
// engine state — because the pool is loaded once at app start from the
// bundle and treated as immutable thereafter.
//
// Phase 3 will add an `EligibilityFilter` field on `PoolQuest`. Authoring the
// 90-quest production pool happens in Phase 4. This phase ships the schema +
// loader + a 6-slug fixture pool that the test suite locks against.

/// The three top-level quest genres. Values match the JSON `genre` field.
enum Genre: String, Codable, CaseIterable, Identifiable, Sendable {
    case activity
    case diet
    case sleep

var id: String { rawValue }
}

/// Optional structured target for a slug. Activity and sleep slugs typically
/// carry a target; diet slugs often don't (qualitative goals like "swap soda
/// for water" — `intent` alone is the parity anchor in that case).
struct QuestTarget: Codable, Equatable, Hashable, Sendable {
let metric: String   // "steps", "minutes", "hours-sleep", "servings", "instances"
let value: Double
let unit: String

init(metric: String, value: Double, unit: String) {
        self.metric = metric
        self.value = value
        self.unit = unit
    }
}

/// One tone variant's rendered copy for a slug.
struct ToneCopy: Codable, Equatable, Hashable, Sendable {
let title: String
let detail: String

init(title: String, detail: String) {
        self.title = title
        self.detail = detail
    }
}

/// One pre-authored quest. Loaded from JSON; immutable in memory.
///
/// Tone parity (D3): for a given `slug`, all three tone variants reference
/// the same `intent` and the same `target`. The lock test
/// (`QuestPoolToneParityTests`) asserts this. The custom Codable below
/// further enforces presence of all three tones at decode time — a missing
/// tone is a load failure, not a render-time nil access.
struct PoolQuest: Equatable, Hashable, Sendable {
let slug: String                  // "<genre>.<intent-shortname>.v<n>"
let genre: Genre
let intent: String                // parity anchor
let target: QuestTarget?          // parity anchor when present
let copy: [ToneMode: ToneCopy]    // type-safe; all three tones required
let exclusionGroups: [String]     // for daily-set conflict avoidance

init(
        slug: String,
        genre: Genre,
        intent: String,
        target: QuestTarget?,
        copy: [ToneMode: ToneCopy],
        exclusionGroups: [String]
    ) {
        self.slug = slug
        self.genre = genre
        self.intent = intent
        self.target = target
        self.copy = copy
        self.exclusionGroups = exclusionGroups
    }
}

extension PoolQuest: Codable {
    private enum CodingKeys: String, CodingKey {
        case slug, genre, intent, target, copy, exclusionGroups
    }

init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let slug = try c.decode(String.self, forKey: .slug)
        let genre = try c.decode(Genre.self, forKey: .genre)
        let intent = try c.decode(String.self, forKey: .intent)
        let target = try c.decodeIfPresent(QuestTarget.self, forKey: .target)
        let raw = try c.decode([String: ToneCopy].self, forKey: .copy)
        let exclusionGroups = try c.decodeIfPresent([String].self, forKey: .exclusionGroups) ?? []

        // Slug format: <genre>.<intent-shortname>.v<digits>
        // Validated at decode so authoring mistakes surface at load time.
        let slugPattern = #"^[a-z]+\.[a-z0-9-]+\.v\d+$"#
        guard slug.range(of: slugPattern, options: .regularExpression) != nil else {
            throw DecodingError.dataCorruptedError(
                forKey: .slug,
                in: c,
                debugDescription: "PoolQuest slug \"\(slug)\" does not match \(slugPattern)"
            )
        }

        // Tone parity at decode: every slug must have all three tone variants.
        // Surfaces missing-tone bugs as a load-time failure, not a nil at
        // render time. JSON keys are strings; the in-memory dict is typed.
        var typed: [ToneMode: ToneCopy] = [:]
        for tone in ToneMode.allCases {
            guard let entry = raw[tone.rawValue] else {
                throw DecodingError.dataCorruptedError(
                    forKey: .copy,
                    in: c,
                    debugDescription: "PoolQuest \(slug) is missing tone \(tone.rawValue)"
                )
            }
            typed[tone] = entry
        }

        self.init(
            slug: slug,
            genre: genre,
            intent: intent,
            target: target,
            copy: typed,
            exclusionGroups: exclusionGroups
        )
    }

func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(slug, forKey: .slug)
        try c.encode(genre, forKey: .genre)
        try c.encode(intent, forKey: .intent)
        try c.encodeIfPresent(target, forKey: .target)
        var raw: [String: ToneCopy] = [:]
        for (tone, value) in copy { raw[tone.rawValue] = value }
        try c.encode(raw, forKey: .copy)
        try c.encode(exclusionGroups, forKey: .exclusionGroups)
    }
}
