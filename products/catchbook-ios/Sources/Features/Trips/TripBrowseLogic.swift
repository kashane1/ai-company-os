import CoreLocation
import Foundation
import MapKit

struct TripCalendarDaySummary: Identifiable {
    let date: Date
    let tripIDs: [UUID]
    let catchIDs: [UUID]
    let tripCount: Int
    let catchCount: Int
    let photoCount: Int
    let topSpeciesText: String?

    var id: Date { date }
}

struct TripCalendarGridCell: Identifiable {
    let date: Date?
    let summary: TripCalendarDaySummary?
    let isWithinDisplayedMonth: Bool

    var id: Date { date ?? .distantPast }
}

struct CatchGalleryItem: Identifiable {
    let id: String
    let catchID: UUID
    let tripID: UUID?
    let speciesName: String
    let tripTitle: String
    let waterbodyName: String?
    let spotTitle: String?
    let caughtAt: Date
    let imageData: Data
    let photoCount: Int
    let photoIndex: Int
}

struct CatchMapMarker: Identifiable {
    let id: String
    let coordinate: CLLocationCoordinate2D
    let tripCount: Int
    let catchCount: Int
    let speciesText: String?
    let confidenceLabel: String?
}

enum TripBrowseLogic {
    static func calendarDaySummaries(
        trips: [Trip],
        catches: [CatchRecord],
        calendar: Calendar = .current
    ) -> [TripCalendarDaySummary] {
        guard !trips.isEmpty && !catches.isEmpty else {
            return []
        }

        let catchesByTripID = Dictionary(grouping: catches) { $0.trip?.id }

        return trips.reduce(into: [Date: TripCalendarDaySummary]()) { result, trip in
            let day = calendar.startOfDay(for: trip.startAt)
            let tripCatches = catchesByTripID[trip.id] ?? []
            guard !tripCatches.isEmpty else { return }

            let topSpecies = Dictionary(grouping: tripCatches, by: \.speciesDisplayName)
                .max { lhs, rhs in
                    if lhs.value.count != rhs.value.count {
                        return lhs.value.count < rhs.value.count
                    }
                    return lhs.key > rhs.key
                }?
                .key

            if let existing = result[day] {
                let mergedTopSpecies = strongestSpecies(
                    current: existing.topSpeciesText,
                    existingCatchCount: existing.catchCount,
                    incoming: topSpecies,
                    incomingCatchCount: tripCatches.count
                )

                result[day] = TripCalendarDaySummary(
                    date: day,
                    tripIDs: existing.tripIDs + [trip.id],
                    catchIDs: existing.catchIDs + tripCatches.map(\.id),
                    tripCount: existing.tripCount + 1,
                    catchCount: existing.catchCount + tripCatches.count,
                    photoCount: existing.photoCount + tripCatches.reduce(0) { $0 + $1.photoCount },
                    topSpeciesText: mergedTopSpecies
                )
            } else {
                result[day] = TripCalendarDaySummary(
                    date: day,
                    tripIDs: [trip.id],
                    catchIDs: tripCatches.map(\.id),
                    tripCount: 1,
                    catchCount: tripCatches.count,
                    photoCount: tripCatches.reduce(0) { $0 + $1.photoCount },
                    topSpeciesText: topSpecies
                )
            }
        }
        .values
        .sorted { $0.date > $1.date }
    }

    static func monthGrid(
        displayedMonth: Date,
        daySummaries: [TripCalendarDaySummary],
        calendar: Calendar = .current
    ) -> [TripCalendarGridCell] {
        guard let monthInterval = calendar.dateInterval(of: .month, for: displayedMonth),
              let firstWeek = calendar.dateInterval(of: .weekOfMonth, for: monthInterval.start)
        else {
            return []
        }

        let summaryByDay = Dictionary(uniqueKeysWithValues: daySummaries.map { (calendar.startOfDay(for: $0.date), $0) })
        let monthStart = calendar.startOfDay(for: monthInterval.start)
        let firstDayOffset = calendar.dateComponents([.day], from: firstWeek.start, to: monthStart).day ?? 0
        let dayCount = calendar.range(of: .day, in: .month, for: displayedMonth)?.count ?? 0

        var cells = Array(repeating: TripCalendarGridCell(date: nil, summary: nil, isWithinDisplayedMonth: false), count: firstDayOffset)

        for offset in 0..<dayCount {
            guard let day = calendar.date(byAdding: .day, value: offset, to: monthStart) else { continue }
            let normalizedDay = calendar.startOfDay(for: day)
            cells.append(
                TripCalendarGridCell(
                    date: normalizedDay,
                    summary: summaryByDay[normalizedDay],
                    isWithinDisplayedMonth: true
                )
            )
        }

        // Pad to a whole number of weeks, with a minimum of 5 rows so the
        // calendar height stays stable month-to-month. A 28-day February that
        // starts on a Sunday would otherwise render as 4 rows and cause the
        // surrounding layout to jump when paging between months.
        let minimumCells = 35
        let weekAligned = cells.count.isMultiple(of: 7) ? cells.count : cells.count + (7 - cells.count % 7)
        let targetCount = max(weekAligned, minimumCells)
        let trailingCount = targetCount - cells.count
        cells.append(contentsOf: Array(repeating: TripCalendarGridCell(date: nil, summary: nil, isWithinDisplayedMonth: false), count: trailingCount))
        return cells
    }

    static func catchGalleryItems(catches: [CatchRecord]) -> [CatchGalleryItem] {
        catches.flatMap { catchRecord in
            let photoPayloads = imagePayloads(for: catchRecord)
            return photoPayloads.enumerated().map { index, payload in
                CatchGalleryItem(
                    id: "\(catchRecord.id.uuidString)-\(index)",
                    catchID: catchRecord.id,
                    tripID: catchRecord.trip?.id,
                    speciesName: catchRecord.speciesDisplayName,
                    tripTitle: catchRecord.trip?.title ?? "Untitled trip",
                    waterbodyName: catchRecord.trip?.waterbody?.name,
                    spotTitle: catchRecord.trip?.spot?.title,
                    caughtAt: catchRecord.caughtAt,
                    imageData: payload,
                    photoCount: photoPayloads.count,
                    photoIndex: index
                )
            }
        }
        .sorted { lhs, rhs in
            if lhs.caughtAt != rhs.caughtAt {
                return lhs.caughtAt > rhs.caughtAt
            }
            if lhs.photoIndex != rhs.photoIndex {
                return lhs.photoIndex < rhs.photoIndex
            }
            return lhs.id < rhs.id
        }
    }

    static func catchMapMarkers(for catches: [CatchRecord]) -> [CatchMapMarker] {
        let grouped = Dictionary(grouping: catches.compactMap(markerSeed(for:))) { seed in
            "\(seed.tripID.uuidString)-\(seed.coordinate.latitude)-\(seed.coordinate.longitude)"
        }

        return grouped.values.compactMap { seeds in
            guard let first = seeds.first else { return nil }

            let groupedSpecies = Dictionary(grouping: seeds, by: \.speciesDisplayName)
            let topSpecies = groupedSpecies.max { lhs, rhs in
                if lhs.value.count != rhs.value.count {
                    return lhs.value.count < rhs.value.count
                }
                return lhs.key > rhs.key
            }?.key

            return CatchMapMarker(
                id: first.id,
                coordinate: first.coordinate,
                tripCount: Set(seeds.map(\.tripID)).count,
                catchCount: seeds.count,
                speciesText: topSpecies,
                confidenceLabel: first.confidenceLabel
            )
        }
        .sorted { lhs, rhs in
            if lhs.catchCount != rhs.catchCount {
                return lhs.catchCount > rhs.catchCount
            }
            if lhs.coordinate.latitude != rhs.coordinate.latitude {
                return lhs.coordinate.latitude > rhs.coordinate.latitude
            }
            return lhs.coordinate.longitude > rhs.coordinate.longitude
        }
    }

    static func mapRegion(
        for markers: [CatchMapMarker],
        fallbackCoordinate: CLLocationCoordinate2D? = nil
    ) -> MKCoordinateRegion {
        let coordinates = markers.map(\.coordinate) + (fallbackCoordinate.map { [$0] } ?? [])

        guard let firstCoordinate = coordinates.first else {
            return MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: 39.8283, longitude: -98.5795),
                span: MKCoordinateSpan(latitudeDelta: 32, longitudeDelta: 44)
            )
        }

        guard coordinates.count > 1 else {
            return MKCoordinateRegion(
                center: firstCoordinate,
                span: MKCoordinateSpan(latitudeDelta: 0.03, longitudeDelta: 0.03)
            )
        }

        let latitudes = coordinates.map(\.latitude)
        let longitudes = coordinates.map(\.longitude)
        let minLatitude = latitudes.min() ?? firstCoordinate.latitude
        let maxLatitude = latitudes.max() ?? firstCoordinate.latitude
        let minLongitude = longitudes.min() ?? firstCoordinate.longitude
        let maxLongitude = longitudes.max() ?? firstCoordinate.longitude

        return MKCoordinateRegion(
            center: CLLocationCoordinate2D(
                latitude: (minLatitude + maxLatitude) / 2,
                longitude: (minLongitude + maxLongitude) / 2
            ),
            span: MKCoordinateSpan(
                latitudeDelta: max((maxLatitude - minLatitude) * 1.5, 0.03),
                longitudeDelta: max((maxLongitude - minLongitude) * 1.5, 0.03)
            )
        )
    }

    static func monthTitle(for date: Date, calendar: Calendar = .current) -> String {
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.dateFormat = "LLLL yyyy"
        return formatter.string(from: date)
    }

    static func dayLabel(for date: Date, calendar: Calendar = .current) -> String {
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.dateStyle = .full
        formatter.timeStyle = .none
        return formatter.string(from: date)
    }

    private static func imagePayloads(for catchRecord: CatchRecord) -> [Data] {
        let sorted = catchRecord.sortedPhotos.compactMap(\.photoData)
        if !sorted.isEmpty {
            return sorted
        }

        return catchRecord.photoData.map { [$0] } ?? []
    }

    private static func strongestSpecies(
        current: String?,
        existingCatchCount: Int,
        incoming: String?,
        incomingCatchCount: Int
    ) -> String? {
        guard let incoming else { return current }
        guard let current else { return incoming }
        if incomingCatchCount != existingCatchCount {
            return incomingCatchCount > existingCatchCount ? incoming : current
        }
        return incoming.localizedCaseInsensitiveCompare(current) == .orderedAscending ? incoming : current
    }

    private struct CatchMapMarkerSeed {
        let id: String
        let tripID: UUID
        let speciesDisplayName: String
        let coordinate: CLLocationCoordinate2D
        let confidenceLabel: String?
    }

    private static func markerSeed(for catchRecord: CatchRecord) -> CatchMapMarkerSeed? {
        guard let trip = catchRecord.trip,
              let coordinate = trip.resolvedCoordinate
        else {
            return nil
        }

        return CatchMapMarkerSeed(
            id: "\(trip.id.uuidString)-\(coordinate.latitude)-\(coordinate.longitude)",
            tripID: trip.id,
            speciesDisplayName: catchRecord.speciesDisplayName,
            coordinate: coordinate,
            confidenceLabel: trip.locationConfidenceLabel
        )
    }
}
