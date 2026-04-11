import CoreLocation
import Foundation
import SwiftData

enum WaterbodyType: String, CaseIterable, Codable, Identifiable {
    case lake
    case river
    case coastal
    case pond
    case offshore

    var id: String { rawValue }

    var label: String {
        rawValue.capitalized
    }
}

enum TripOutcome: String, Codable {
    case active
    case caught
    case skunked
}

enum ConditionCaptureStatus: String, Codable {
    case ready
    case fallback
    case pending
}

enum ConditionSource: String, Codable {
    case deviceLocation
    case tripFallback
    case weatherDeferred
    case weatherKit
}

@Model
final class Waterbody {
    @Attribute(.unique) var id: UUID
    var name: String
    var typeRawValue: String
    var latitude: Double?
    var longitude: Double?
    var isPrivate: Bool
    var createdAt: Date

    init(
        name: String,
        type: WaterbodyType,
        latitude: Double? = nil,
        longitude: Double? = nil,
        isPrivate: Bool = true,
        createdAt: Date = .now
    ) {
        self.id = UUID()
        self.name = name
        self.typeRawValue = type.rawValue
        self.latitude = latitude
        self.longitude = longitude
        self.isPrivate = isPrivate
        self.createdAt = createdAt
    }

    var type: WaterbodyType {
        WaterbodyType(rawValue: typeRawValue) ?? .lake
    }

    var subtitle: String {
        isPrivate ? "\(type.label) • Private" : type.label
    }
}

@Model
final class Spot {
    @Attribute(.unique) var id: UUID
    var title: String
    var latitude: Double?
    var longitude: Double?
    var notes: String
    var isPrivate: Bool
    var createdAt: Date
    var waterbody: Waterbody?

    init(
        title: String,
        waterbody: Waterbody?,
        latitude: Double? = nil,
        longitude: Double? = nil,
        notes: String = "",
        isPrivate: Bool = true,
        createdAt: Date = .now
    ) {
        self.id = UUID()
        self.title = title
        self.latitude = latitude
        self.longitude = longitude
        self.notes = notes
        self.isPrivate = isPrivate
        self.createdAt = createdAt
        self.waterbody = waterbody
    }

    var coordinateSummary: String {
        guard let latitude, let longitude else {
            return "Coordinates not captured yet"
        }
        return String(format: "%.4f, %.4f", latitude, longitude)
    }
}

@Model
final class ConditionSnapshot {
    @Attribute(.unique) var id: UUID
    var capturedAt: Date
    var latitude: Double?
    var longitude: Double?
    var placeSummary: String?
    var timeWindowSummary: String?
    var lightLevelSummary: String?
    var temperatureC: Double?
    var weatherSummary: String?
    var windSummary: String?
    var cloudCoverSummary: String?
    var precipitationSummary: String?
    var captureStatusRawValue: String
    var sourceRawValue: String

    init(
        capturedAt: Date = .now,
        latitude: Double? = nil,
        longitude: Double? = nil,
        placeSummary: String? = nil,
        timeWindowSummary: String? = nil,
        lightLevelSummary: String? = nil,
        temperatureC: Double? = nil,
        weatherSummary: String? = nil,
        windSummary: String? = nil,
        cloudCoverSummary: String? = nil,
        precipitationSummary: String? = nil,
        captureStatus: ConditionCaptureStatus = .fallback,
        source: ConditionSource = .tripFallback
    ) {
        self.id = UUID()
        self.capturedAt = capturedAt
        self.latitude = latitude
        self.longitude = longitude
        self.placeSummary = placeSummary
        self.timeWindowSummary = timeWindowSummary
        self.lightLevelSummary = lightLevelSummary
        self.temperatureC = temperatureC
        self.weatherSummary = weatherSummary
        self.windSummary = windSummary
        self.cloudCoverSummary = cloudCoverSummary
        self.precipitationSummary = precipitationSummary
        self.captureStatusRawValue = captureStatus.rawValue
        self.sourceRawValue = source.rawValue
    }

    var captureStatus: ConditionCaptureStatus {
        ConditionCaptureStatus(rawValue: captureStatusRawValue) ?? .fallback
    }

    var source: ConditionSource {
        ConditionSource(rawValue: sourceRawValue) ?? .tripFallback
    }

    var coordinateSummary: String? {
        guard let latitude, let longitude else { return nil }
        return String(format: "%.4f, %.4f", latitude, longitude)
    }

    var statusLine: String {
        switch captureStatus {
        case .ready:
            return "Conditions captured"
        case .fallback:
            return "Using local fallback conditions"
        case .pending:
            return "Conditions pending"
        }
    }

    var weatherLine: String {
        var parts: [String] = []

        if let celsius = temperatureC {
            // Unit-aware formatting — MeasurementFormatter localizes the unit
            // (°F in US, °C elsewhere) and respects the user's region setting.
            let measurement = Measurement<UnitTemperature>(value: celsius, unit: .celsius)
            let formatter = MeasurementFormatter()
            formatter.unitOptions = [.naturalScale, .providedUnit]
            formatter.numberFormatter.maximumFractionDigits = 0
            parts.append(formatter.string(from: measurement))
        }
        if let weatherSummary, !weatherSummary.isEmpty {
            parts.append(weatherSummary)
        }
        if let windSummary, !windSummary.isEmpty {
            parts.append(windSummary)
        }
        if let cloudCoverSummary, !cloudCoverSummary.isEmpty {
            parts.append(cloudCoverSummary)
        }
        if let precipitationSummary, !precipitationSummary.isEmpty {
            parts.append(precipitationSummary)
        }

        if parts.isEmpty {
            return "Weather data unavailable"
        }

        return parts.joined(separator: " • ")
    }

    var similarityDescription: String {
        let parts = [timeWindowSummary, lightLevelSummary, windSummary, precipitationSummary]
            .compactMap { value -> String? in
                guard let value, !value.isEmpty else { return nil }
                return value
            }

        if parts.isEmpty {
            return "recent trip context"
        }

        return parts.joined(separator: " • ")
    }

    var displaySummary: String {
        var parts: [String] = []

        if let placeSummary, !placeSummary.isEmpty {
            parts.append(placeSummary)
        }
        if let timeWindowSummary, !timeWindowSummary.isEmpty {
            parts.append(timeWindowSummary)
        }
        if let lightLevelSummary, !lightLevelSummary.isEmpty {
            parts.append(lightLevelSummary)
        }
        if let coordinateSummary {
            parts.append(coordinateSummary)
        }
        parts.append(weatherLine)
        return parts.joined(separator: " • ")
    }
}

@Model
final class Trip {
    @Attribute(.unique) var id: UUID
    var startAt: Date
    var endAt: Date?
    var targetSpecies: String
    var notes: String
    var outcomeRawValue: String
    var waterbody: Waterbody?
    var spot: Spot?
    var conditionSnapshot: ConditionSnapshot?

    init(
        waterbody: Waterbody?,
        spot: Spot? = nil,
        conditionSnapshot: ConditionSnapshot? = nil,
        targetSpecies: String = "",
        notes: String = "",
        startAt: Date = .now
    ) {
        self.id = UUID()
        self.startAt = startAt
        self.endAt = nil
        self.targetSpecies = targetSpecies
        self.notes = notes
        self.outcomeRawValue = TripOutcome.active.rawValue
        self.waterbody = waterbody
        self.spot = spot
        self.conditionSnapshot = conditionSnapshot
    }

    var outcome: TripOutcome {
        TripOutcome(rawValue: outcomeRawValue) ?? .active
    }

    var isActive: Bool {
        endAt == nil
    }

    var title: String {
        spot?.title ?? waterbody?.name ?? "Untitled trip"
    }

    var targetSpeciesList: [String] {
        normalizedSpeciesTokens(from: targetSpecies)
    }
}

@Model
final class CatchRecord {
    @Attribute(.unique) var id: UUID
    var species: String
    var caughtAt: Date
    var lureOrBait: String
    var method: String
    var weightKg: Double?
    var lengthCm: Double?
    var note: String
    var photoReference: String?
    @Attribute(.externalStorage) var photoData: Data?
    var photoContentType: String?
    var trip: Trip?

    init(
        species: String,
        trip: Trip?,
        caughtAt: Date = .now,
        lureOrBait: String = "",
        method: String = "",
        weightKg: Double? = nil,
        lengthCm: Double? = nil,
        note: String = "",
        photoReference: String? = nil,
        photoData: Data? = nil,
        photoContentType: String? = nil
    ) {
        self.id = UUID()
        self.species = species
        self.caughtAt = caughtAt
        self.lureOrBait = lureOrBait
        self.method = method
        self.weightKg = weightKg
        self.lengthCm = lengthCm
        self.note = note
        self.photoReference = photoReference
        self.photoData = photoData
        self.photoContentType = photoContentType
        self.trip = trip
    }

    var hasPhoto: Bool {
        photoData != nil
    }

    var speciesDisplayName: String {
        let trimmed = species.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "Species not logged" : trimmed
    }
}

@Model
final class PersonalBest {
    @Attribute(.unique) var id: UUID
    var species: String
    var longestLengthCm: Double?
    var heaviestWeightKg: Double?
    var longestCatchID: UUID?
    var heaviestCatchID: UUID?
    var updatedAt: Date

    init(
        species: String,
        longestLengthCm: Double? = nil,
        heaviestWeightKg: Double? = nil,
        longestCatchID: UUID? = nil,
        heaviestCatchID: UUID? = nil,
        updatedAt: Date = .now
    ) {
        self.id = UUID()
        self.species = species
        self.longestLengthCm = longestLengthCm
        self.heaviestWeightKg = heaviestWeightKg
        self.longestCatchID = longestCatchID
        self.heaviestCatchID = heaviestCatchID
        self.updatedAt = updatedAt
    }
}

func timeWindowLabel(for date: Date, calendar: Calendar = .current) -> String {
    let hour = calendar.component(.hour, from: date)
    switch hour {
    case 5..<9:
        return "6-9 AM"
    case 9..<12:
        return "9 AM-Noon"
    case 12..<15:
        return "Noon-3 PM"
    case 15..<19:
        return "3-7 PM"
    default:
        return "Evening"
    }
}

func lightLevelLabel(for date: Date, calendar: Calendar = .current) -> String {
    let hour = calendar.component(.hour, from: date)
    switch hour {
    case 4..<6:
        return "First light"
    case 6..<11:
        return "Morning light"
    case 11..<16:
        return "Midday light"
    case 16..<20:
        return "Evening light"
    default:
        return "Low light"
    }
}

func bestAvailableCoordinate(
    location: CLLocation?,
    spot: Spot?,
    waterbody: Waterbody?
) -> CLLocationCoordinate2D? {
    if let coordinate = location?.coordinate {
        return coordinate
    }
    if let latitude = spot?.latitude, let longitude = spot?.longitude {
        return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
    if let latitude = waterbody?.latitude, let longitude = waterbody?.longitude {
        return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
    return nil
}

func normalizedSpeciesTokens(from rawValue: String) -> [String] {
    var seen: Set<String> = []

    return rawValue
        .split(whereSeparator: { character in
            character == "," || character == "\n" || character == ";"
        })
        .compactMap { part -> String? in
            let value = part.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !value.isEmpty else { return nil }

            let normalizedKey = value.lowercased()
            guard !seen.contains(normalizedKey) else { return nil }
            seen.insert(normalizedKey)
            return value
        }
}
