import Foundation
import SwiftData

/// Daily quest slate selection + end-of-day event resolution.
///
/// Phase 3 of the quest-pool affinity engine
/// (docs/plans/2026-05-08-feat-quest-pool-phase-3-engines-plan.md).
///
/// `select(...)` is a pure function over typed inputs. `resolveEndOfDay(...)`
/// mutates SwiftData state (it backfills `resolvedKind` on stale events) so
/// it takes a `ModelContext`; the boundary between pure and impure work
/// stays clear.
///
/// Algorithm (master plan D8 + Phase 3 plan G14–G26):
///
///   1. Precompute `latestShownBySlug: [String: Date]` once at the top
///      from a single pass over events. Per-slug recency decay is then
///      O(1). At Phase 4 scale (90 slugs × 1500 events) this drops
///      135k comparisons to 1500 (perf review).
///
///   2. For each genre, score every slug in `pool.byGenre[genre]`
///      and pick the top-scored one. Tiebreaker: slug-ascending
///      lexical (already enforced by byGenre's sort — G20).
///
///        score = pow(affinity[g], discoveryDamp) * needWeight[g] * recencyDecay
///
///        discoveryDamp = 0.3 + 0.7 × min(distinctOpenDays / 7, 1)
///        recencyDecay  = exp(-Δt / 3.5)   where Δt is days since latestShownBySlug[slug]
///                                          (1.0 if slug was never shown)
///
///   3. Conflict pass: if any two picks share an `exclusionGroups`
///      entry, drop the lower-scored one and replace with the next-
///      best non-conflicting slug in its genre. Bounded at 5
///      iterations.
///
///   4. Deadlock fallback: emit `consistency.open-app-tomorrow.v1`
///      (constructed manually — not in the pool) as the third slot.
///
/// `select` returns up to 3 `PoolQuest`s, one per genre. The hard
/// genre floor is enforced — every genre is represented unless the
/// pool is empty for that genre.
enum QuestSelector {
    /// Recency decay time constant (days). Canonical exponential
    /// time-weight per Ding & Li 2005 (SIGIR). At τ = 3.5, a slug shown
    /// 7 days ago has recencyDecay ≈ exp(-2) ≈ 0.13, effectively
    /// rotating it back to the front.
    static let recencyTau: Double = 3.5

    /// Maximum exclusion-group conflict-resolution iterations before
    /// the deadlock fallback fires. With 5–10 group names across the
    /// 90-slug pool, deadlock should be near-impossible — but the
    /// bound makes the algorithm provably terminating.
    static let maxConflictIterations: Int = 5

    /// Bounded walk-back for the EOD resolver. Older unresolved rows
    /// are bulk-resolved to `passed_over`. Per perf review.
    static let eodWalkCapDays: Int = 30

    // MARK: - Public

    /// Pick today's slate of up to 3 quests, one per genre. Pure
    /// function — same inputs always produce the same output.
    static func select(
        pool: QuestPool,
        affinity: [Genre: Double],
        needWeight: [Genre: Double],
        profile: UserProfile,
        today: Date,
        events: [QuestEvent]
    ) -> [PoolQuest] {
        // 1. Precompute per-slug "latest shown" dates for O(1) recencyDecay.
        let latestShown = latestShownBySlug(events: events)

        let damp = discoveryDamp(distinctOpenDays: profile.distinctOpenDays)
        let calendar = Calendar.current

        // 2. Hard-filter ineligible slugs BEFORE scoring (Phase 4a).
        //    `isEligible` short-circuits when the slug carries no filter,
        //    so the fixture pool (no eligibility fields) passes through
        //    unchanged.
        let eligibleByGenre: [Genre: [PoolQuest]] = pool.byGenre.mapValues { genreQuests in
            genreQuests.filter { Self.isEligible($0, profile: profile) }
        }

        // 3. Score every eligible slug per-genre, pick top-1.
        var picks: [Genre: PoolQuest] = [:]
        var scores: [String: Double] = [:]
        for genre in Genre.allCases {
            let candidates = eligibleByGenre[genre] ?? []
            guard !candidates.isEmpty else { continue }
            for quest in candidates {
                let score = score(
                    for: quest,
                    affinity: affinity[genre] ?? AffinityEngine.initialAffinity,
                    needWeight: needWeight[genre] ?? 0.5,
                    discoveryDamp: damp,
                    today: today,
                    latestShown: latestShown,
                    calendar: calendar
                )
                scores[quest.slug] = score
            }
            // Sort the genre's slugs by score desc, tiebreak by slug asc
            // (byGenre is already slug-ascending so the stable-sort
            // preserves that as the tiebreaker).
            let ranked = candidates.sorted {
                let a = scores[$0.slug] ?? 0
                let b = scores[$1.slug] ?? 0
                if a != b { return a > b }
                return $0.slug < $1.slug
            }
            picks[genre] = ranked.first
        }

        // 4. Conflict pass: drop lower-scored picks that share an
        //    exclusionGroup with a higher-scored pick. Replace with
        //    the next-best non-conflicting slug in its genre. Only
        //    eligible slugs are considered for replacement.
        for _ in 0..<maxConflictIterations {
            guard let conflict = firstExclusionConflict(in: picks, scores: scores) else {
                break
            }
            // Drop the lower-scored side of the conflict; try to
            // replace it with the next-best slug in its genre that
            // doesn't share an exclusion group with the surviving picks.
            let droppedGenre = conflict.loserGenre
            let droppedSlug = picks[droppedGenre]?.slug
            let surviving = picks.filter { $0.key != droppedGenre }
            let usedGroups = Set(surviving.values.flatMap(\.exclusionGroups))
            let candidates = (eligibleByGenre[droppedGenre] ?? [])
                .filter { $0.slug != droppedSlug && !sharesGroup($0, with: usedGroups) }
                .sorted {
                    let a = scores[$0.slug] ?? 0
                    let b = scores[$1.slug] ?? 0
                    if a != b { return a > b }
                    return $0.slug < $1.slug
                }
            if let replacement = candidates.first {
                picks[droppedGenre] = replacement
            } else {
                // No replacement possible in this genre — drop the
                // slot entirely. Caller will emit consistency fallback.
                picks[droppedGenre] = nil
            }
        }

        return Genre.allCases.compactMap { picks[$0] }
    }

    // MARK: - Eligibility filter (Phase 4a)

    /// Phase 4a hard-filter, applied BEFORE scoring. A slug with no
    /// `eligibility` field is always eligible — preserves the fixture
    /// pool's "anyone, anytime" shape and lets authors omit the field
    /// when there's no contraindication to record.
    ///
    /// Field semantics match the doc-comment on `EligibilityFilter`. The
    /// 7-day cold-start threshold matches `discoveryDamp`'s saturation
    /// point (Phase 3 plan G16): a user clears discovery damp at the same
    /// moment they unlock cold-start-only slugs.
    static func isEligible(_ quest: PoolQuest, profile: UserProfile) -> Bool {
        guard let filter = quest.eligibility else { return true }

        if let needsSmoker = filter.requiresSmoker {
            let isSmoker = profile.smokingStatus != "none"
            if needsSmoker != isSmoker { return false }
        }

        if let needsDrinker = filter.requiresDrinker {
            let lightDrinker = profile.alcoholFrequency == "none"
                || profile.alcoholFrequency == "rare"
            let isDrinker = !lightDrinker
            if needsDrinker != isDrinker { return false }
        }

        if let needsRoutine = filter.requiresStrengthRoutine {
            let hasRoutine = profile.strengthFrequencyPerWeek > 0
            if needsRoutine != hasRoutine { return false }
        }

        if !filter.coldStartReachable && profile.distinctOpenDays < 7 {
            return false
        }

        // `timeOfDay` is recorded but non-load-bearing in Phase 4a. Phase
        // 4b/c may begin to gate on it once a time-of-day refresh hook
        // exists.
        return true
    }

    // MARK: - End-of-day resolution

    /// Walks unresolved `QuestEvent` rows where `date < today` and
    /// fills `resolvedKind`. Single broad fetch + in-memory grouping
    /// (per perf review) — not per-row correlated queries.
    ///
    /// Idempotent: a re-fire on a row whose `resolvedKind` is already
    /// non-nil is a no-op.
    ///
    /// Bounded at `eodWalkCapDays` — older rows get a single bulk
    /// update to `passed_over` to avoid unbounded launch jank.
    static func resolveEndOfDay(
        context: ModelContext,
        today: Date
    ) throws {
        let calendar = Calendar.current
        let todayStart = calendar.startOfDay(for: today)
        guard let cutoff = calendar.date(byAdding: .day, value: -eodWalkCapDays, to: todayStart) else {
            return
        }

        // Single broad fetch over the 30-day window.
        let predicate = #Predicate<QuestEvent> { event in
            event.date < todayStart && event.date >= cutoff && event.resolvedKind == nil
        }
        let descriptor = FetchDescriptor<QuestEvent>(predicate: predicate)
        let unresolved = try context.fetch(descriptor)
        // NOTE: do NOT early-return when `unresolved` is empty — the
        // bulk pass below resolves rows older than the 30-day window
        // (e.g., a user offline >30 days). Both passes must run.

        // Group ALL events in the window (including resolved ones) by
        // (startOfDay, slug) so we can check whether terminal kinds
        // already happened on the same day.
        let windowDescriptor = FetchDescriptor<QuestEvent>(
            predicate: #Predicate<QuestEvent> { event in
                event.date < todayStart && event.date >= cutoff
            }
        )
        let windowEvents = try context.fetch(windowDescriptor)
        var kindsByKey: [DateSlugKey: Set<String>] = [:]
        for event in windowEvents {
            let key = DateSlugKey(date: calendar.startOfDay(for: event.date), slug: event.slug)
            kindsByKey[key, default: []].insert(event.kind)
        }

        for event in unresolved {
            let key = DateSlugKey(date: calendar.startOfDay(for: event.date), slug: event.slug)
            let kinds = kindsByKey[key] ?? []
            switch event.kind {
            case QuestEventKind.shown.rawValue:
                // G22: skip if `replaced` already happened for this
                // (date, slug). The slug already received a stronger
                // negative signal; resolving as `passed_over` would
                // double-count. Also skip if the slug WAS picked
                // (then the picked row will resolve separately).
                if kinds.contains(QuestEventKind.replaced.rawValue) { continue }
                if kinds.contains(QuestEventKind.picked.rawValue) { continue }
                event.resolvedKind = QuestResolvedKind.passedOver.rawValue
                event.resolvedAt = today
            case QuestEventKind.picked.rawValue:
                // Skip if completed — picked → completed is success,
                // no abandon. Skip if a later replaced superseded it
                // (replaced is its own terminal signal).
                if kinds.contains(QuestEventKind.completed.rawValue) { continue }
                if kinds.contains(QuestEventKind.replaced.rawValue) { continue }
                event.resolvedKind = QuestResolvedKind.abandoned.rawValue
                event.resolvedAt = today
            default:
                // `replaced` and `completed` are terminal at emit —
                // no resolution needed; leave them alone.
                continue
            }
        }

        // Bulk pass for rows older than the 30-day cap (user offline
        // 60+ days). Reuses the same `cutoff` boundary as the windowed
        // pass — together they partition the unresolved space:
        //   - In-window  (cutoff ≤ date < todayStart): co-occurrence
        //                check above prevents over-counting picked
        //                rows that completed, or shown rows that
        //                replaced/picked.
        //   - Out-of-window (date < cutoff): bulk-resolve to
        //                passed_over without correlation, intentionally.
        //                These rows are >30 days old; the cost of
        //                marking a once-completed picked row as
        //                passed_over here is bounded — affinity has
        //                already converged on >30-day-old signals.
        // Defensive `fetchLimit = 1000` (perf review on PR #32):
        // a user offline 6 months would otherwise materialize 500+
        // rows in one save, stalling cold launch ~500ms. Excess rows
        // resolve on subsequent days (idempotent — re-running the
        // resolver picks up whatever's left).
        var oldDescriptor = FetchDescriptor<QuestEvent>(
            predicate: #Predicate<QuestEvent> { event in
                event.date < cutoff && event.resolvedKind == nil
                    && (event.kind == "shown" || event.kind == "picked")
            }
        )
        oldDescriptor.fetchLimit = 1000
        let veryOld = try context.fetch(oldDescriptor)
        for event in veryOld {
            event.resolvedKind = QuestResolvedKind.passedOver.rawValue
            event.resolvedAt = today
        }

        try context.save()
    }

    // MARK: - Cold-start discovery dampening

    /// `0.3 + 0.7 × min(distinctOpenDays / 7, 1)`. Day 1 → 0.3,
    /// day 7+ → 1.0. Applied as the exponent on affinity in the
    /// score formula so day-1 affinity contributes only `0.5^0.3 ≈
    /// 0.81`× of its full weight; by day 7 it contributes `0.5^1 =
    /// 0.5`× (full).
    static func discoveryDamp(distinctOpenDays: Int) -> Double {
        let progress = min(Double(distinctOpenDays) / 7.0, 1.0)
        return 0.3 + 0.7 * progress
    }

    // MARK: - Internals

    private static func score(
        for quest: PoolQuest,
        affinity: Double,
        needWeight: Double,
        discoveryDamp: Double,
        today: Date,
        latestShown: [String: Date],
        calendar: Calendar
    ) -> Double {
        let recencyDecay: Double
        if let lastShown = latestShown[quest.slug] {
            let days = max(0, calendar.dateComponents([.day], from: lastShown, to: today).day ?? 0)
            recencyDecay = exp(-Double(days) / recencyTau)
        } else {
            recencyDecay = 1.0
        }
        let baseAffinity = max(0.0, min(1.0, affinity))   // clamp, just in case
        let dampened = pow(baseAffinity, discoveryDamp)
        return dampened * needWeight * recencyDecay
    }

    /// Build a `[slug: latest-shown-date]` index in one pass. Pure.
    static func latestShownBySlug(events: [QuestEvent]) -> [String: Date] {
        var latest: [String: Date] = [:]
        for event in events where event.kind == QuestEventKind.shown.rawValue {
            if let prev = latest[event.slug] {
                if event.date > prev { latest[event.slug] = event.date }
            } else {
                latest[event.slug] = event.date
            }
        }
        return latest
    }

    private struct ExclusionConflict {
        let loserGenre: Genre
    }

    /// Find the first pair of picks that share an exclusionGroup, and
    /// return the genre of the lower-scored side (which we'll drop).
    /// Returns nil when no conflict exists.
    private static func firstExclusionConflict(
        in picks: [Genre: PoolQuest],
        scores: [String: Double]
    ) -> ExclusionConflict? {
        let sortedGenres = Genre.allCases  // stable iteration order
        for i in 0..<sortedGenres.count {
            guard let a = picks[sortedGenres[i]] else { continue }
            for j in (i + 1)..<sortedGenres.count {
                guard let b = picks[sortedGenres[j]] else { continue }
                if !Set(a.exclusionGroups).isDisjoint(with: Set(b.exclusionGroups)) {
                    let aScore = scores[a.slug] ?? 0
                    let bScore = scores[b.slug] ?? 0
                    let loser: Genre = aScore < bScore ? sortedGenres[i] : sortedGenres[j]
                    return ExclusionConflict(loserGenre: loser)
                }
            }
        }
        return nil
    }

    private static func sharesGroup(_ quest: PoolQuest, with groups: Set<String>) -> Bool {
        !Set(quest.exclusionGroups).isDisjoint(with: groups)
    }

    private struct DateSlugKey: Hashable {
        let date: Date  // start-of-day
        let slug: String
    }
}
