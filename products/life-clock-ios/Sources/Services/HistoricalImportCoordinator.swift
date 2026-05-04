import Foundation
import SwiftData

/// Lazy full-history Pro import. Pulls daily snapshots from HealthKit
/// (chunked by week so cancel UX is meaningful and partial completion can
/// resume) and upserts them into SwiftData by `dayKey`. Idempotent: re-runs
/// only fetch days that don't already have a persisted row stamped within
/// the last week — earlier rows are considered final. The window is sized
/// generously (10 years) — HealthKit returns nil/empty for days before the
/// user's first sample, and idempotency makes those cheap on rerun.
///
/// Trigger: first time a Pro user opens the History tab. Run once per
/// install in the background; user can cancel via the progress banner.
///
/// Performance note: the current `LiveHealthKitService.recentSnapshots`
/// makes ~6 HK queries per day. A future optimization will collapse those
/// into a single `HKStatisticsCollectionQuery` per metric across the full
/// 90-day window — see PR description's "Deferred" section. The current
/// implementation is correct and idempotent; the optimization is purely
/// about wall-clock time on the import.
@MainActor
@Observable
final class HistoricalImportCoordinator {
    /// 10-year ceiling. HealthKit-of-record only goes back as far as the
    /// user's first device, so days before that just return empty and the
    /// idempotent skip keeps re-imports cheap. We don't auto-extend past
    /// this ceiling because the chunk loop is bounded by it.
    static let importWindowDays = 365 * 10
    static let chunkDays = 7

    enum Status: Equatable {
        case idle
        case importing(completed: Int, total: Int)
        case finished(daysImported: Int)
        case cancelled
        case failed(message: String)
    }

    private(set) var status: Status = .idle

    @ObservationIgnored private let healthService: HealthKitServiceProtocol
    @ObservationIgnored private let modelContext: ModelContext
    @ObservationIgnored private let clock: EngineClock
    @ObservationIgnored private var currentTask: Task<Void, Never>?

    init(
        healthService: HealthKitServiceProtocol,
        modelContext: ModelContext,
        clock: EngineClock
    ) {
        self.healthService = healthService
        self.modelContext = modelContext
        self.clock = clock
    }

    /// Kicks off the import in the background. No-op if the import is
    /// already running or has finished this session.
    ///
    /// Implementation note: `run()` is `@MainActor` because it touches
    /// `modelContext`. We do NOT wrap in `Task.detached` — the body would
    /// just hop back to the main actor immediately, defeating the purpose,
    /// and detached tasks don't inherit cancellation from their parent
    /// `Task`. A plain `Task { @MainActor in ... }` gives us the
    /// cancellation propagation we need from `cancel()` calling
    /// `currentTask?.cancel()`.
    func startIfNeeded() {
        switch status {
        case .idle, .failed, .cancelled:
            break
        case .importing, .finished:
            return
        }
        currentTask = Task { @MainActor [weak self] in
            await self?.run()
        }
    }

    /// Cancels an in-flight import. Already-imported chunks remain
    /// persisted (idempotent re-run will skip them).
    func cancel() {
        currentTask?.cancel()
        status = .cancelled
    }

    @MainActor
    private func run() async {
        let now = clock.now()
        let cal = clock.calendar
        guard let earliest = cal.date(byAdding: .day, value: -Self.importWindowDays, to: now) else {
            status = .failed(message: "Could not compute import window.")
            return
        }
        let total = Self.importWindowDays
        var completed = 0
        status = .importing(completed: 0, total: total)

        // Walk the window in week-sized chunks. Each chunk is independently
        // committed so cancellation leaves a coherent partial state.
        var chunkStart = cal.startOfDay(for: earliest)
        while chunkStart < now, !Task.isCancelled {
            let chunkEnd = cal.date(byAdding: .day, value: Self.chunkDays, to: chunkStart) ?? now
            let chunkUpperBound = min(chunkEnd, now)
            await importChunk(from: chunkStart, to: chunkUpperBound)
            let imported = cal.dateComponents([.day], from: chunkStart, to: chunkUpperBound).day ?? 0
            completed += imported
            status = .importing(completed: min(completed, total), total: total)
            chunkStart = chunkEnd
        }

        if Task.isCancelled {
            status = .cancelled
        } else {
            status = .finished(daysImported: completed)
        }
    }

    @MainActor
    private func importChunk(from start: Date, to end: Date) async {
        let cal = clock.calendar
        let chunkDays = cal.dateComponents([.day], from: start, to: end).day ?? 0
        guard chunkDays > 0 else { return }

        // Optimized path: ONE HKStatisticsCollectionQuery per quantity
        // metric across the chunk window (3 queries) + per-day sleep
        // sample queries within the chunk (~7 queries). The per-day
        // fan-out used to issue ~6 queries × 7 days = ~42 per chunk.
        // For the protocol's default fallback, this calls
        // `recentSnapshots(endingAt:count:)` which preserves the
        // pre-optimization behavior.
        let snapshots = await healthService.recentSnapshotsCollection(
            endingAt: cal.date(byAdding: .day, value: -1, to: end) ?? start,
            days: chunkDays
        )
        let recomputedAt = clock.now()
        var inserted = 0
        for snapshot in snapshots {
            if Task.isCancelled { break }
            // Idempotency: skip days that already have a persisted row.
            // The foreground refresh path handles "today" specifically.
            if fetchSnapshot(for: snapshot.date) == nil {
                snapshot.lastRecomputedAt = recomputedAt
                modelContext.insert(snapshot)
                inserted += 1
            }
        }
        // Single save per chunk — keeps SwiftData's @Query observers
        // firing once per ~7 days rather than once per day.
        if inserted > 0 {
            try? modelContext.save()
        }
    }

    private func fetchSnapshot(for dayStart: Date) -> DailyHealthSnapshot? {
        let descriptor = FetchDescriptor<DailyHealthSnapshot>(
            predicate: #Predicate { $0.date == dayStart }
        )
        return try? modelContext.fetch(descriptor).first
    }
}
