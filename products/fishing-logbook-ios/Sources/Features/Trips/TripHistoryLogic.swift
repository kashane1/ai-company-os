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

enum TripSeasonFilter: String, CaseIterable, Identifiable {
    case all
    case spring
    case summer
    case fall
    case winter

    var id: String { rawValue }

    var label: String {
        switch self {
        case .all:
            return "Any Season"
        case .spring:
            return "Spring"
        case .summer:
            return "Summer"
        case .fall:
            return "Fall"
        case .winter:
            return "Winter"
        }
    }
}

enum TripHistoryLogic {
    static func availableWaterbodies(waterbodies: [Waterbody], trips: [Trip]) -> [Waterbody] {
        let tripWaterbodyIDs = Set(trips.compactMap(\.waterbody?.id))
        return waterbodies.filter { tripWaterbodyIDs.contains($0.id) }
    }

    static func availableLures(
        trips: [Trip],
        catches: [CatchRecord],
        selectedWaterbodyID: UUID?,
        speciesQuery: String,
        dateFilter: TripDateFilter,
        seasonFilter: TripSeasonFilter,
        now: Date = .now,
        calendar: Calendar = .current
    ) -> [String] {
        let filteredTripIDs = Set(
            filteredTrips(
                trips: trips,
                catches: catches,
                selectedWaterbodyID: selectedWaterbodyID,
                speciesQuery: speciesQuery,
                dateFilter: dateFilter,
                seasonFilter: seasonFilter,
                selectedLure: nil,
                now: now,
                calendar: calendar
            ).map(\.id)
        )
        var seenLureKeys: Set<String> = []
        var availableLures: [String] = []

        for catchRecord in catches {
            guard let tripID = catchRecord.trip?.id, filteredTripIDs.contains(tripID) else { continue }
            guard let lureDisplayValue = normalizedLureDisplayValue(catchRecord.lureOrBait) else { continue }

            let lureKey = normalizedLureKey(lureDisplayValue)
            guard !seenLureKeys.contains(lureKey) else { continue }

            seenLureKeys.insert(lureKey)
            availableLures.append(lureDisplayValue)
        }

        return availableLures
    }

    static func hasActiveFilters(
        selectedWaterbodyID: UUID?,
        speciesQuery: String,
        dateFilter: TripDateFilter,
        seasonFilter: TripSeasonFilter,
        selectedLure: String?
    ) -> Bool {
        selectedWaterbodyID != nil
            || !normalizedSpeciesQuery(speciesQuery).isEmpty
            || dateFilter != .all
            || seasonFilter != .all
            || !normalizedLureKey(selectedLure).isEmpty
    }

    static func filteredTrips(
        trips: [Trip],
        catches: [CatchRecord],
        selectedWaterbodyID: UUID?,
        speciesQuery: String,
        dateFilter: TripDateFilter,
        seasonFilter: TripSeasonFilter,
        selectedLure: String?,
        now: Date = .now,
        calendar: Calendar = .current
    ) -> [Trip] {
        let query = normalizedSpeciesQuery(speciesQuery)
        let lureKey = normalizedLureKey(selectedLure)
        let catchesByTripID = Dictionary(grouping: catches) { $0.trip?.id }

        return trips.filter { trip in
            matchesWaterbody(trip: trip, selectedWaterbodyID: selectedWaterbodyID)
                && matchesDate(trip: trip, dateFilter: dateFilter, now: now, calendar: calendar)
                && matchesSeason(trip: trip, seasonFilter: seasonFilter, calendar: calendar)
                && matchesSpecies(trip: trip, catchesByTripID: catchesByTripID, query: query)
                && matchesLure(trip: trip, catchesByTripID: catchesByTripID, lureKey: lureKey)
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

    private static func matchesSeason(
        trip: Trip,
        seasonFilter: TripSeasonFilter,
        calendar: Calendar
    ) -> Bool {
        guard seasonFilter != .all else { return true }
        return season(for: trip.startAt, calendar: calendar) == seasonFilter
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

    private static func matchesLure(
        trip: Trip,
        catchesByTripID: [UUID?: [CatchRecord]],
        lureKey: String
    ) -> Bool {
        guard !lureKey.isEmpty else { return true }

        return catchesByTripID[Optional(trip.id), default: []].contains { catchRecord in
            normalizedLureKey(catchRecord.lureOrBait) == lureKey
        }
    }

    private static func season(for date: Date, calendar: Calendar) -> TripSeasonFilter {
        switch calendar.component(.month, from: date) {
        case 3 ... 5:
            return .spring
        case 6 ... 8:
            return .summer
        case 9 ... 11:
            return .fall
        default:
            return .winter
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

    private static func normalizedLureDisplayValue(_ value: String) -> String? {
        let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmedValue.isEmpty ? nil : trimmedValue
    }

    private static func normalizedLureKey(_ value: String?) -> String {
        guard let value else { return "" }
        return value
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
    }
}
