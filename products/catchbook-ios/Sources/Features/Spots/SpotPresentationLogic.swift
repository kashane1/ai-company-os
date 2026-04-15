import CoreLocation
import Foundation
import MapKit
import SwiftUI

struct SpotRowDetails {
    let waterbodyName: String
    let isPinned: Bool
    let notesPreview: String?
}

struct SpotStatSummary {
    let tripCountText: String
    let catchCountText: String
    let productiveTripCountText: String
}

struct SpotRecallDetailItem: Identifiable {
    let id: String
    let title: String
    let value: String
    let evidence: String?
}

struct SpotRecentTripSummary: Identifiable {
    let id: UUID
    let dateText: String
    let outcomeText: String
    let catchText: String
    let isSkunked: Bool
    let topSpeciesText: String?
    let topLureText: String?
    let conditionSummary: String?
}

struct SpotRecentCatchSummary: Identifiable {
    let id: UUID
    let species: String
    let dateText: String
    let lureOrBait: String?
    let metricSummary: String?
    let tripID: UUID?
    let tripTitle: String?
}

extension SpotPinColor {
    /// SwiftUI color used for this pin on the map and in filter buttons.
    var color: Color {
        switch self {
        case .blue: return .catchbookOcean
        case .green: return .catchbookForest
        case .amber: return .catchbookAmber
        case .red: return Color(red: 0.843, green: 0.259, blue: 0.259)
        case .purple: return Color(red: 0.545, green: 0.361, blue: 0.745)
        case .teal: return .catchbookAqua
        }
    }
}

enum SpotPresentationLogic {
    static let waterbodyColorPalette: [Color] = [
        .catchbookOcean,
        .catchbookDeep,
        .catchbookNavy,
        .catchbookAqua,
        .catchbookForest,
        .catchbookAmber,
    ]

    static func privateRecallCards(for summary: SpotRecallSummary) -> [DeterministicInsightCard] {
        summary.cards
    }

    static func rowDetails(for spot: Spot) -> SpotRowDetails {
        let notesPreview = TripEditingLogic.normalizedOptionalText(spot.notes)
        return SpotRowDetails(
            waterbodyName: spot.waterbody?.name ?? "Unknown water",
            isPinned: spot.latitude != nil,
            notesPreview: notesPreview
        )
    }

    static func spotsWithCoordinates(from spots: [Spot]) -> [Spot] {
        spots.filter { $0.latitude != nil && $0.longitude != nil }
    }

    static func mapRegion(for spots: [Spot]) -> MKCoordinateRegion {
        let coordinates = spots.compactMap(coordinate(for:))

        guard let firstCoordinate = coordinates.first else {
            return MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: 39.8283, longitude: -98.5795),
                span: MKCoordinateSpan(latitudeDelta: 32, longitudeDelta: 44)
            )
        }

        guard coordinates.count > 1 else {
            return MKCoordinateRegion(
                center: firstCoordinate,
                span: MKCoordinateSpan(latitudeDelta: 0.02, longitudeDelta: 0.02)
            )
        }

        let latitudes = coordinates.map(\.latitude)
        let longitudes = coordinates.map(\.longitude)
        let minLatitude = latitudes.min() ?? firstCoordinate.latitude
        let maxLatitude = latitudes.max() ?? firstCoordinate.latitude
        let minLongitude = longitudes.min() ?? firstCoordinate.longitude
        let maxLongitude = longitudes.max() ?? firstCoordinate.longitude

        let latitudeDelta = max((maxLatitude - minLatitude) * 1.4, 0.02)
        let longitudeDelta = max((maxLongitude - minLongitude) * 1.4, 0.02)

        return MKCoordinateRegion(
            center: CLLocationCoordinate2D(
                latitude: (minLatitude + maxLatitude) / 2,
                longitude: (minLongitude + maxLongitude) / 2
            ),
            span: MKCoordinateSpan(
                latitudeDelta: latitudeDelta,
                longitudeDelta: longitudeDelta
            )
        )
    }

    static func waterbodyCentroid(from spots: [Spot]) -> CLLocationCoordinate2D? {
        let coordinates = spots.compactMap(coordinate(for:))
        guard !coordinates.isEmpty else { return nil }

        let latitude = coordinates.map(\.latitude).reduce(0, +) / Double(coordinates.count)
        let longitude = coordinates.map(\.longitude).reduce(0, +) / Double(coordinates.count)
        return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }

    static func waterbodyColor(for waterbodyID: UUID?, palette: [Color] = waterbodyColorPalette) -> Color {
        guard let waterbodyID else {
            return palette.first ?? .catchbookOcean
        }

        let index = waterbodyColorIndex(for: waterbodyID, paletteCount: palette.count)
        return palette[index]
    }

    static func waterbodyColorIndex(for waterbodyID: UUID, paletteCount: Int) -> Int {
        guard paletteCount > 0 else { return 0 }

        let hash = waterbodyID.uuidString.unicodeScalars.reduce(5381) { partial, scalar in
            ((partial << 5) &+ partial) &+ Int(scalar.value)
        }
        return abs(hash) % paletteCount
    }

    static func catchesHere(spotID: UUID, catches: [CatchRecord]) -> [CatchRecord] {
        catches
            .filter { $0.trip?.spot?.id == spotID }
            .sorted { $0.caughtAt > $1.caughtAt }
    }

    static func statSummary(for summary: SpotRecallSummary) -> SpotStatSummary {
        SpotStatSummary(
            tripCountText: "\(summary.tripCount)",
            catchCountText: "\(summary.catchCount)",
            productiveTripCountText: "\(summary.successfulTripCount)"
        )
    }

    static func recallDetails(for summary: SpotRecallSummary) -> [SpotRecallDetailItem] {
        var items: [SpotRecallDetailItem] = []

        if let mostEffectiveLure = summary.mostEffectiveLure {
            items.append(
                SpotRecallDetailItem(
                    id: "lure",
                    title: "Most effective lure",
                    value: mostEffectiveLure,
                    evidence: evidenceLabel(
                        supportCount: summary.mostEffectiveLureSupportCount,
                        unit: "catch"
                    )
                )
            )
        }

        if let bestTimeWindow = summary.bestTimeWindow {
            items.append(
                SpotRecallDetailItem(
                    id: "time-window",
                    title: "Best time window",
                    value: bestTimeWindow,
                    evidence: evidenceLabel(
                        supportCount: summary.bestTimeWindowSupportCount,
                        unit: "catch"
                    )
                )
            )
        }

        if let simpleConditionSummary = summary.simpleConditionSummary {
            items.append(
                SpotRecallDetailItem(
                    id: "conditions",
                    title: "Simple condition summary",
                    value: simpleConditionSummary,
                    evidence: evidenceLabel(
                        supportCount: summary.simpleConditionSupportCount,
                        unit: "productive trip"
                    )
                )
            )
        }

        return items
    }

    private static func evidenceLabel(supportCount: Int, unit: String) -> String? {
        guard supportCount > 0 else { return nil }
        let pluralizedUnit: String
        if supportCount == 1 {
            pluralizedUnit = unit
        } else if unit == "catch" {
            pluralizedUnit = "catches"
        } else {
            pluralizedUnit = "\(unit)s"
        }
        return "Based on \(supportCount) \(pluralizedUnit)"
    }

    static func recentTripSummaries(
        trips: [Trip],
        catches: [CatchRecord],
        dateFormatter: DateFormatter = AppFormatters.tripDate
    ) -> [SpotRecentTripSummary] {
        trips.map { trip in
            let tripCatches = catches.filter { $0.trip?.id == trip.id }
            return SpotRecentTripSummary(
                id: trip.id,
                dateText: dateFormatter.string(from: trip.startAt),
                outcomeText: trip.outcomeRawValue.capitalized,
                catchText: catchText(for: trip, catches: tripCatches),
                isSkunked: trip.outcomeRawValue == TripOutcome.skunked.rawValue,
                topSpeciesText: topSpeciesText(from: tripCatches),
                topLureText: topLureText(from: tripCatches),
                conditionSummary: trip.conditionSnapshot?.displaySummary
            )
        }
    }

    static func recentCatchSummaries(
        catches: [CatchRecord],
        dateFormatter: DateFormatter = AppFormatters.tripDate
    ) -> [SpotRecentCatchSummary] {
        Array(catches.sorted { $0.caughtAt > $1.caughtAt }.prefix(5)).map { catchRecord in
            SpotRecentCatchSummary(
                id: catchRecord.id,
                species: catchRecord.speciesDisplayName,
                dateText: dateFormatter.string(from: catchRecord.caughtAt),
                lureOrBait: TripEditingLogic.normalizedOptionalText(catchRecord.lureOrBait),
                metricSummary: metricSummary(for: catchRecord),
                tripID: catchRecord.trip?.id,
                tripTitle: catchRecord.trip?.title
            )
        }
    }

    private static func catchText(for trip: Trip, catches: [CatchRecord]) -> String {
        let catchCount = catches.count
        if catchCount == 0 && (
            trip.outcomeRawValue == TripOutcome.skunked.rawValue ||
            !trip.isActive
        ) {
            return "Skunked"
        }
        return "\(catchCount) \(catchCount == 1 ? "catch" : "catches")"
    }

    private static func topSpeciesText(from catches: [CatchRecord]) -> String? {
        let counts = Dictionary(grouping: catches, by: \.speciesDisplayName).mapValues(\.count)
        return counts.max { lhs, rhs in
            if lhs.value != rhs.value {
                return lhs.value < rhs.value
            }
            return lhs.key > rhs.key
        }?.key
    }

    private static func topLureText(from catches: [CatchRecord]) -> String? {
        let lures = catches.compactMap { catchRecord -> String? in
            TripEditingLogic.normalizedOptionalText(catchRecord.lureOrBait)
        }
        let counts = Dictionary(grouping: lures, by: { $0 }).mapValues(\.count)
        return counts.max { lhs, rhs in
            if lhs.value != rhs.value {
                return lhs.value < rhs.value
            }
            return lhs.key > rhs.key
        }?.key
    }

    private static func metricSummary(for catchRecord: CatchRecord) -> String? {
        let metrics = [
            catchRecord.lengthCm.map { "\($0.formatted()) cm" },
            catchRecord.weightKg.map { "\($0.formatted()) kg" },
        ].compactMap { $0 }
        return metrics.isEmpty ? nil : metrics.joined(separator: " · ")
    }

    private static func coordinate(for spot: Spot) -> CLLocationCoordinate2D? {
        guard let latitude = spot.latitude, let longitude = spot.longitude else {
            return nil
        }

        return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}
