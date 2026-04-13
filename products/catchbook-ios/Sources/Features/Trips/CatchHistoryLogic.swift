import Foundation

struct CatchHistoryFilter: Equatable {
    var query: String = ""
    var selectedWaterbodyID: UUID?
    var dateFilter: TripDateFilter = .all
    var seasonFilter: TripSeasonFilter = .all
    var selectedLure: String?
}

enum CatchHistoryLogic {
    static func filteredCatches(
        catches: [CatchRecord],
        filter: CatchHistoryFilter,
        now: Date = .now,
        calendar: Calendar = .current
    ) -> [CatchRecord] {
        let query = normalizedQuery(filter.query)
        let lureKey = normalizedLureKey(filter.selectedLure)

        return catches.filter { catchRecord in
            matchesWaterbody(catchRecord: catchRecord, selectedWaterbodyID: filter.selectedWaterbodyID)
                && matchesDate(catchRecord: catchRecord, dateFilter: filter.dateFilter, now: now, calendar: calendar)
                && matchesSeason(catchRecord: catchRecord, seasonFilter: filter.seasonFilter, calendar: calendar)
                && matchesLure(catchRecord: catchRecord, lureKey: lureKey)
                && matchesQuery(catchRecord: catchRecord, query: query)
        }
    }

    static func availableWaterbodies(catches: [CatchRecord]) -> [Waterbody] {
        var seen: Set<UUID> = []
        var results: [Waterbody] = []

        for catchRecord in catches {
            guard let waterbody = catchRecord.trip?.waterbody else { continue }
            guard seen.insert(waterbody.id).inserted else { continue }
            results.append(waterbody)
        }

        return results.sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
    }

    static func availableLures(catches: [CatchRecord], filter: CatchHistoryFilter) -> [String] {
        let lureFilterless = CatchHistoryFilter(
            query: filter.query,
            selectedWaterbodyID: filter.selectedWaterbodyID,
            dateFilter: filter.dateFilter,
            seasonFilter: filter.seasonFilter,
            selectedLure: nil
        )

        let filtered = filteredCatches(catches: catches, filter: lureFilterless)
        var seen: Set<String> = []
        var lures: [String] = []

        for catchRecord in filtered {
            let trimmed = catchRecord.lureOrBait.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { continue }
            let key = trimmed.lowercased()
            guard seen.insert(key).inserted else { continue }
            lures.append(trimmed)
        }

        return lures
    }

    static func hasActiveFilters(_ filter: CatchHistoryFilter) -> Bool {
        filter.selectedWaterbodyID != nil
            || !normalizedQuery(filter.query).isEmpty
            || filter.dateFilter != .all
            || filter.seasonFilter != .all
            || !normalizedLureKey(filter.selectedLure).isEmpty
    }

    private static func matchesWaterbody(catchRecord: CatchRecord, selectedWaterbodyID: UUID?) -> Bool {
        guard let selectedWaterbodyID else { return true }
        return catchRecord.trip?.waterbody?.id == selectedWaterbodyID
    }

    private static func matchesDate(
        catchRecord: CatchRecord,
        dateFilter: TripDateFilter,
        now: Date,
        calendar: Calendar
    ) -> Bool {
        switch dateFilter {
        case .all:
            return true
        case .last30Days:
            guard let cutoff = calendar.date(byAdding: .day, value: -30, to: now) else { return true }
            return catchRecord.caughtAt >= cutoff
        case .last90Days:
            guard let cutoff = calendar.date(byAdding: .day, value: -90, to: now) else { return true }
            return catchRecord.caughtAt >= cutoff
        case .thisYear:
            guard let interval = calendar.dateInterval(of: .year, for: now) else { return true }
            return interval.contains(catchRecord.caughtAt)
        }
    }

    private static func matchesSeason(
        catchRecord: CatchRecord,
        seasonFilter: TripSeasonFilter,
        calendar: Calendar
    ) -> Bool {
        guard seasonFilter != .all else { return true }
        return TripHistoryLogic.season(for: catchRecord.caughtAt, calendar: calendar) == seasonFilter
    }

    private static func matchesLure(catchRecord: CatchRecord, lureKey: String) -> Bool {
        guard !lureKey.isEmpty else { return true }
        return normalizedLureKey(catchRecord.lureOrBait) == lureKey
    }

    private static func matchesQuery(catchRecord: CatchRecord, query: String) -> Bool {
        guard !query.isEmpty else { return true }

        let haystacks = [
            catchRecord.species,
            catchRecord.lureOrBait,
            catchRecord.method,
            catchRecord.note,
            catchRecord.trip?.spot?.title ?? "",
            catchRecord.trip?.waterbody?.name ?? "",
        ]

        return haystacks.contains { value in
            value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased().contains(query)
        }
    }

    private static func normalizedQuery(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }

    private static func normalizedLureKey(_ value: String?) -> String {
        guard let value else { return "" }
        return value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }
}
