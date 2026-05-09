import Foundation

/// Per-genre preference computation from quest-event history.
///
/// Phase 3 of the quest-pool affinity engine
/// (docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md).
///
/// Affinity ∈ [0, 1]: 0.5 starting prior, EMA-updated by each terminal
/// quest event. Higher = user has actively engaged with this genre.
/// Lower = user has actively rejected slugs in this genre.
///
/// Math (per master plan D6):
///   new = (1 - α·w) × old + α·w × target,  where α = 0.2
///
/// Half-life ≈ 3 events (formula `t½ = -ln(2)/ln(1-α)`). At a 1–3
/// event/day cadence this means a week of engagement reshapes
/// affinity. Defensible default; `alpha` is pinned as a `static let`
/// so retuning is a one-line change with no archaeology required.
///
/// Signal weights asymmetrically penalize active reject vs passive
/// non-engagement (per Hu/Koren/Volinsky 2008 confidence-weight
/// ordering): replaced > picked-not-completed > shown-not-picked.
///
/// **Phase 3 ships non-cached** — linear pass over `[QuestEvent]` per
/// invocation. The deepened plan considered an incremental cache
/// (`UserProfile.affinityState: Data`) but deferred it because
/// `useQuestPoolEngine` defaults to `false` in this PR — production
/// users accumulate zero events. When the flag flips (Phase 5a), the
/// caching pass is the first follow-up.
enum AffinityEngine {
    /// EMA learning rate. Pinned for retunability. See file header for
    /// the half-life math + rationale.
    static let alpha: Double = 0.2

    /// Initial affinity when no events exist for a genre. Neutral prior;
    /// the 7-day discovery damp in QuestSelector dampens this so cold
    /// starts don't lock in based on the first 1–2 events.
    static let initialAffinity: Double = 0.5

    /// Per-event signal contribution: `target` is what the EMA pulls
    /// toward, `weight` multiplies α to scale the pull. Returns `nil`
    /// when the event isn't yet resolved (e.g., a `picked` row that
    /// the EOD resolver hasn't reached).
    static func signal(for kind: QuestEventKind, resolvedKind: QuestResolvedKind?) -> (target: Double, weight: Double)? {
        switch (kind, resolvedKind) {
        case (.completed, _):
            return (target: 1.0, weight: 1.0)
        case (.replaced, _):
            return (target: 0.0, weight: 1.5)
        case (.picked, .abandoned):
            return (target: 0.0, weight: 1.0)
        case (.picked, _):
            return nil  // picked but not yet resolved (still might complete)
        case (.shown, .passedOver):
            return (target: 0.3, weight: 0.5)
        case (.shown, _):
            return nil  // shown but not yet resolved
        }
    }

    /// Compute current per-genre affinity from a quest-event history.
    /// Events are sorted ascending by date before folding — caller does
    /// not need to pre-sort. Unrecognized `genre` strings (e.g., the
    /// out-of-pool `consistency.open-app-tomorrow.v1` fallback which
    /// carries `genre = ""`) are ignored.
    static func computeAffinities(events: [QuestEvent]) -> [Genre: Double] {
        var ema: [Genre: Double] = [:]
        for genre in Genre.allCases {
            ema[genre] = initialAffinity
        }

        let sorted = events.sorted { $0.date < $1.date }
        for event in sorted {
            guard
                let kind = QuestEventKind(rawValue: event.kind),
                let genre = Genre(rawValue: event.genre)
            else { continue }
            let resolved = event.resolvedKind.flatMap(QuestResolvedKind.init(rawValue:))
            guard let signal = signal(for: kind, resolvedKind: resolved) else { continue }
            let effectiveAlpha = alpha * signal.weight
            let prev = ema[genre] ?? initialAffinity
            ema[genre] = (1.0 - effectiveAlpha) * prev + effectiveAlpha * signal.target
        }
        return ema
    }
}
