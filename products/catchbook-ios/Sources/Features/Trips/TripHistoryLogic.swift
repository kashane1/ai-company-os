import CoreLocation
import Foundation
import MapKit

struct TripHistorySection: Identifiable {
    let id: String
    let title: String
    let subtitle: String?
    let spot: Spot?
    let trips: [Trip]
}

struct WaterbodySummary: Identifiable {
    let waterbodyID: UUID
    let waterbodyName: String
    let waterbodyType: WaterbodyType
    let coordinate: CLLocationCoordinate2D
    let tripCount: Int
    let catchCount: Int
    let spotCount: Int
    let lastTripDate: Date?
    let spots: [Spot]

    var id: UUID { waterbodyID }
}

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
    static func waterbodySummaries(
        trips: [Trip],
        catches: [CatchRecord],
        spots: [Spot],
        waterbodies: [Waterbody]
    ) -> [WaterbodySummary] {
        guard !trips.isEmpty else { return [] }

        let explicitWaterbodies = Dictionary(uniqueKeysWithValues: waterbodies.map { ($0.id, $0) })
        let tripGroups = Dictionary(grouping: trips) { $0.waterbody?.id }
        let tripIDs = Set(trips.map(\.id))

        return tripGroups.compactMap { waterbodyID, groupedTrips in
            guard let waterbodyID else { return nil }
            guard let representativeWaterbody = explicitWaterbodies[waterbodyID] ?? groupedTrips.compactMap(\.waterbody).first else {
                return nil
            }

            let waterbodySpots = spots
                .filter { $0.waterbody?.id == waterbodyID }
                .sorted { $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending }

            let coordinate = coordinate(for: representativeWaterbody, spots: waterbodySpots)
            guard let coordinate else { return nil }

            let catchCount = catches.reduce(into: 0) { total, catchRecord in
                guard let tripID = catchRecord.trip?.id, tripIDs.contains(tripID) else { return }
                guard catchRecord.trip?.waterbody?.id == waterbodyID else { return }
                total += 1
            }

            return WaterbodySummary(
                waterbodyID: waterbodyID,
                waterbodyName: representativeWaterbody.name,
                waterbodyType: representativeWaterbody.type,
                coordinate: coordinate,
                tripCount: groupedTrips.count,
                catchCount: catchCount,
                spotCount: waterbodySpots.count,
                lastTripDate: groupedTrips.map(\.startAt).max(),
                spots: waterbodySpots
            )
        }
        .sorted { lhs, rhs in
            let lhsDate = lhs.lastTripDate ?? .distantPast
            let rhsDate = rhs.lastTripDate ?? .distantPast
            if lhsDate != rhsDate {
                return lhsDate > rhsDate
            }
            return lhs.waterbodyName.localizedCaseInsensitiveCompare(rhs.waterbodyName) == .orderedAscending
        }
    }

    static func mapRegion(for summaries: [WaterbodySummary]) -> MKCoordinateRegion {
        guard let firstSummary = summaries.first else {
            return MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: 39.8283, longitude: -98.5795),
                span: MKCoordinateSpan(latitudeDelta: 32, longitudeDelta: 44)
            )
        }

        guard summaries.count > 1 else {
            return MKCoordinateRegion(
                center: firstSummary.coordinate,
                span: MKCoordinateSpan(latitudeDelta: 0.2, longitudeDelta: 0.2)
            )
        }

        let latitudes = summaries.map(\.coordinate.latitude)
        let longitudes = summaries.map(\.coordinate.longitude)
        let minLatitude = latitudes.min() ?? firstSummary.coordinate.latitude
        let maxLatitude = latitudes.max() ?? firstSummary.coordinate.latitude
        let minLongitude = longitudes.min() ?? firstSummary.coordinate.longitude
        let maxLongitude = longitudes.max() ?? firstSummary.coordinate.longitude

        return MKCoordinateRegion(
            center: CLLocationCoordinate2D(
                latitude: (minLatitude + maxLatitude) / 2,
                longitude: (minLongitude + maxLongitude) / 2
            ),
            span: MKCoordinateSpan(
                latitudeDelta: max((maxLatitude - minLatitude) * 1.4, 0.2),
                longitudeDelta: max((maxLongitude - minLongitude) * 1.4, 0.2)
            )
        )
    }

    static func sections(
        trips: [Trip],
        catches: [CatchRecord]
    ) -> [TripHistorySection] {
        let catchesByTripID = Dictionary(grouping: catches) { $0.trip?.id }
        let groupedTrips = Dictionary(grouping: trips) { trip in
            trip.spot?.id.uuidString ?? "general-area"
        }

        return groupedTrips.compactMap { key, groupedTrips in
            let sortedTrips = groupedTrips.sorted { $0.startAt > $1.startAt }
            guard let latestTrip = sortedTrips.first else { return nil }

            let totalCatchCount = sortedTrips.reduce(into: 0) { total, trip in
                total += catchesByTripID[Optional(trip.id), default: []].count
            }

            if let spot = latestTrip.spot {
                return TripHistorySection(
                    id: key,
                    title: spot.title,
                    subtitle: sectionSubtitle(
                        tripCount: sortedTrips.count,
                        catchCount: totalCatchCount
                    ),
                    spot: spot,
                    trips: sortedTrips
                )
            }

            return TripHistorySection(
                id: key,
                title: "General Area",
                subtitle: "Trips without a saved spot still stay private and easy to revisit.",
                spot: nil,
                trips: sortedTrips
            )
        }
        .sorted { lhs, rhs in
            let lhsDate = lhs.trips.first?.startAt ?? .distantPast
            let rhsDate = rhs.trips.first?.startAt ?? .distantPast
            return lhsDate > rhsDate
        }
    }

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

    static func season(for date: Date, calendar: Calendar) -> TripSeasonFilter {
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

    private static func sectionSubtitle(tripCount: Int, catchCount: Int) -> String {
        let tripLabel = "\(tripCount) \(tripCount == 1 ? "trip" : "trips")"
        guard catchCount > 0 else {
            return "\(tripLabel) saved privately"
        }

        let catchLabel = "\(catchCount) \(catchCount == 1 ? "catch" : "catches")"
        return "\(tripLabel) · \(catchLabel)"
    }

    private static func coordinate(for waterbody: Waterbody, spots: [Spot]) -> CLLocationCoordinate2D? {
        if let latitude = waterbody.latitude, let longitude = waterbody.longitude {
            return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
        }

        return SpotPresentationLogic.waterbodyCentroid(from: spots)
    }
}
