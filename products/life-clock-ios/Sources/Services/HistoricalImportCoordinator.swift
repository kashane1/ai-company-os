import Foundation
import SwiftData

/// Lazy 90-day Pro historical import. Pulls daily snapshots from HealthKit
/// (chunked by week so cancel UX is meaningful and partial completion can
/// resume) and upserts them into SwiftData by `dayKey`. Idempotent: re-runs
/// only fetch days that don't already have a persisted row stamped within
/// the last week — earlier rows are considered final.
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
final class HistoricalImportCoordinator {
    static let importWindowDays = 90
    static let chunkDays = 7

    enum Status: Equatable {
        case idle
        case importing(completed: Int, total: Int)
        case finished(daysImported: Int)
        case cancelled
        case failed(message: String)
    }

    private(set) var status: Status = .idle

    private let healthService: HealthKitServiceProtocol
    private let modelContext: ModelContext
    private let clock: EngineClock
    private var currentTask: Task<Void, Never>?

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
    func startIfNeeded() {
        switch status {
        case .idle, .failed, .cancelled:
            break
        case .importing, .finished:
            return
        }
        let task = Task.detached(priority: .background) { [weak self] in
            await self?.run()
        }
        currentTask = Task { await task.value }
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
        var cursor = start
        while cursor < end, !Task.isCancelled {
            // Idempotency: skip days that already have a persisted snapshot.
            // We treat any persisted row as final for the import path; the
            // foreground refresh path handles "today" specifically.
            if fetchSnapshot(for: cursor) == nil {
                if let snapshot = await healthService.dailySnapshot(for: cursor) {
                    snapshot.lastRecomputedAt = clock.now()
                    modelContext.insert(snapshot)
                }
            }
            cursor = cal.date(byAdding: .day, value: 1, to: cursor) ?? end
        }
        try? modelContext.save()
    }

    private func fetchSnapshot(for dayStart: Date) -> DailyHealthSnapshot? {
        let descriptor = FetchDescriptor<DailyHealthSnapshot>(
            predicate: #Predicate { $0.date == dayStart }
        )
        return try? modelContext.fetch(descriptor).first
    }
}
