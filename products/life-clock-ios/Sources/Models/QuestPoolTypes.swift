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

// MARK: - QuestEvent kind enums (Phase 3)
//
// SwiftData stores `QuestEvent.kind` and `QuestEvent.resolvedKind` as plain
// `String` (matching the existing `TimeLedgerEntry.driverType` convention).
// Every read/write site funnels through these enums, so a typo becomes a
// compile-time error rather than a silent affinity skew. Source-of-truth
// lives here in the Models layer.
//
// Phase 3 of the quest-pool affinity engine — todo 049 #3.

/// The four-event lifecycle for a quest slug on a given day.
/// Emitted by the engine + plan-editor + completion-toggle paths in
/// `LifeClockStore`. Read by `AffinityEngine.computeAffinities(events:)`.
enum QuestEventKind: String, CaseIterable, Codable, Sendable {
    /// Engine emitted this slug into today's slate (or as an alternate
    /// in the plan editor). Logged once per (date, slug) — idempotent.
    case shown
    /// User added this slug to today's plan via the editor. Idempotent at
    /// the SwiftData layer is application-level; the same (date, slug)
    /// can have one `picked` row.
    case picked
    /// User swapped this slug OUT of today's plan via the editor (slug
    /// A → slug B logs `replaced(A) + picked(B)`). Stronger negative
    /// signal than passive non-engagement — weighted 1.5× in the EMA.
    case replaced
    /// User ticked this slug as completed on Today. Strongest positive
    /// signal — target = 1.0 in the EMA.
    case completed
}

/// End-of-day resolution outcome for `shown` and `picked` rows that
/// never reached a terminal kind by the day boundary. Filled by
/// `QuestSelector.resolveEndOfDay(...)` on the next foreground past
/// midnight. `nil` for terminal-at-emit kinds (`replaced`, `completed`).
enum QuestResolvedKind: String, CaseIterable, Codable, Sendable {
    /// Was `shown`, never `picked` by EOD. Mild negative signal in the EMA.
    case passedOver = "passed_over"
    /// Was `picked`, never `completed` by EOD. Stronger negative signal.
    case abandoned
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

/// Optional time-of-day window. `anytime` and a nil filter behave the same;
/// the explicit value lets authors document intent without wiring routing.
/// Phase 4a records the field; Phase 4b/c may begin to gate on it.
enum TimeOfDayWindow: String, Codable, Sendable {
    case morning, midday, evening, anytime
}

/// Hard-filter that runs BEFORE scoring in `QuestSelector.select(...)`.
/// Restored in Phase 4a (cut from Phase 2 per simplicity-reviewer when the
/// fixture pool had no contraindicated slugs and production pool was empty).
/// Now load-bearing because authored slugs reference contraindications.
///
/// Field semantics:
///   * `requiresSmoker`: nil = any; true = `smokingStatus != "none"`;
///     false = `smokingStatus == "none"`.
///   * `requiresDrinker`: nil = any; true = `alcoholFrequency` ∉
///     `{"none","rare"}`; false = `alcoholFrequency` ∈ `{"none","rare"}`.
///   * `requiresStrengthRoutine`: nil = any; true =
///     `strengthFrequencyPerWeek > 0`; false = `strengthFrequencyPerWeek == 0`.
///   * `coldStartReachable`: when false, the slug is excluded for users
///     with `distinctOpenDays < 7`. Use for slugs that need familiarity to
///     be useful (e.g. zone-2 framing assumes the user has engaged with
///     activity tracking).
///   * `timeOfDay`: nil or `anytime` = no gating. `morning`/`midday`/`evening`
///     are recorded as authoring intent; routing is non-load-bearing in
///     Phase 4a (no time-of-day refresh trigger yet).
struct EligibilityFilter: Codable, Equatable, Hashable, Sendable {
    let requiresSmoker: Bool?
    let requiresDrinker: Bool?
    let requiresStrengthRoutine: Bool?
    let coldStartReachable: Bool
    let timeOfDay: TimeOfDayWindow?

    init(
        requiresSmoker: Bool? = nil,
        requiresDrinker: Bool? = nil,
        requiresStrengthRoutine: Bool? = nil,
        coldStartReachable: Bool = true,
        timeOfDay: TimeOfDayWindow? = nil
    ) {
        self.requiresSmoker = requiresSmoker
        self.requiresDrinker = requiresDrinker
        self.requiresStrengthRoutine = requiresStrengthRoutine
        self.coldStartReachable = coldStartReachable
        self.timeOfDay = timeOfDay
    }

    /// The "anyone, anytime" filter. Equivalent to `nil` at the call site;
    /// useful when an author wants to record the field explicitly.
    static let unrestricted = EligibilityFilter()
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
let eligibility: EligibilityFilter?  // nil = unrestricted (Phase 4a)

init(
        slug: String,
        genre: Genre,
        intent: String,
        target: QuestTarget?,
        copy: [ToneMode: ToneCopy],
        exclusionGroups: [String],
        eligibility: EligibilityFilter? = nil
    ) {
        self.slug = slug
        self.genre = genre
        self.intent = intent
        self.target = target
        self.copy = copy
        self.exclusionGroups = exclusionGroups
        self.eligibility = eligibility
    }
}

extension PoolQuest: Codable {
    private enum CodingKeys: String, CodingKey {
        case slug, genre, intent, target, copy, exclusionGroups, eligibility
    }

init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let slug = try c.decode(String.self, forKey: .slug)
        let genre = try c.decode(Genre.self, forKey: .genre)
        let intent = try c.decode(String.self, forKey: .intent)
        let target = try c.decodeIfPresent(QuestTarget.self, forKey: .target)
        let raw = try c.decode([String: ToneCopy].self, forKey: .copy)
        let exclusionGroups = try c.decodeIfPresent([String].self, forKey: .exclusionGroups) ?? []
        let eligibility = try c.decodeIfPresent(EligibilityFilter.self, forKey: .eligibility)

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

        // Intent is the parity anchor for slugs without a numeric target —
        // an empty value collapses every targetless slug onto the same
        // bucket and skews affinity in Phase 3. Require non-empty.
        // (A stricter "slug embeds intent" check was considered but
        // rejected: fixture slugs use a `fixture-` prefix in the intent
        // token to namespace from production, and production authoring
        // tooling will catch genuine slug↔intent typos.)
        guard !intent.isEmpty else {
            throw DecodingError.dataCorruptedError(
                forKey: .intent,
                in: c,
                debugDescription: "PoolQuest \(slug) has empty intent"
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
            exclusionGroups: exclusionGroups,
            eligibility: eligibility
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
        try c.encodeIfPresent(eligibility, forKey: .eligibility)
    }
}
