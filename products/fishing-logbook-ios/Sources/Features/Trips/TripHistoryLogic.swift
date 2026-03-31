import Foundation

enum TripDateFilter: String, CaseIterable, Identifiable {
    case all
    case last30Days
    case last90Days
    case thisYear

    var id: String { rawValue }

    var label: String {
        switch self {
        case .all:
            return "Any Date"
        case .last30Days:
            return "Last 30 Days"
        case .last90Days:
            return "Last 90 Days"
        case .thisYear:
            return "This Year"
        }
    }
}

enum TripHistoryLogic {
    static func availableWaterbodies(waterbodies: [Waterbody], trips: [Trip]) -> [Waterbody] {
        let tripWaterbodyIDs = Set(trips.compactMap(\.waterbody?.id))
        return waterbodies.filter { tripWaterbodyIDs.contains($0.id) }
    }

    static func hasActiveFilters(
        selectedWaterbodyID: UUID?,
        speciesQuery: String,
        dateFilter: TripDateFilter
    ) -> Bool {
        selectedWaterbodyID != nil || !normalizedSpeciesQuery(speciesQuery).isEmpty || dateFilter != .all
    }

    static func filteredTrips(
        trips: [Trip],
        catches: [CatchRecord],
        selectedWaterbodyID: UUID?,
        speciesQuery: String,
        dateFilter: TripDateFilter,
        now: Date = .now,
        calendar: Calendar = .current
    ) -> [Trip] {
        let query = normalizedSpeciesQuery(speciesQuery)
        let catchesByTripID = Dictionary(grouping: catches) { $0.trip?.id }

        return trips.filter { trip in
            matchesWaterbody(trip: trip, selectedWaterbodyID: selectedWaterbodyID)
                && matchesDate(trip: trip, dateFilter: dateFilter, now: now, calendar: calendar)
                && matchesSpecies(trip: trip, catchesByTripID: catchesByTripID, query: query)
        }
    }

    private static func matchesWaterbody(trip: Trip, selectedWaterbodyID: UUID?) -> Bool {
        guard let selectedWaterbodyID else { return true }
        return trip.waterbody?.id == selectedWaterbodyID
    }

    private static func matchesDate(
        trip: Trip,
        dateFilter: TripDateFilter,
        now: Date,
        calendar: Calendar
    ) -> Bool {
        switch dateFilter {
        case .all:
            return true
        case .last30Days:
            guard let cutoff = calendar.date(byAdding: .day, value: -30, to: now) else { return true }
            return trip.startAt >= cutoff
        case .last90Days:
            guard let cutoff = calendar.date(byAdding: .day, value: -90, to: now) else { return true }
            return trip.startAt >= cutoff
        case .thisYear:
            guard let interval = calendar.dateInterval(of: .year, for: now) else { return true }
            return interval.contains(trip.startAt)
        }
    }

    private static func matchesSpecies(
        trip: Trip,
        catchesByTripID: [UUID?: [CatchRecord]],
        query: String
    ) -> Bool {
        guard !query.isEmpty else { return true }

        if trip.targetSpeciesList.contains(where: { normalizedSpeciesValue($0).contains(query) }) {
            return true
        }

        return catchesByTripID[Optional(trip.id), default: []].contains { catchRecord in
            normalizedSpeciesValue(catchRecord.species).contains(query)
        }
    }

    private static func normalizedSpeciesQuery(_ value: String) -> String {
        normalizedSpeciesValue(value)
    }

    private static func normalizedSpeciesValue(_ value: String) -> String {
        value
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
    }
}
