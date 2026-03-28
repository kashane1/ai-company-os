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
    var weatherSummary: String?
    var windSummary: String?
    var cloudCoverSummary: String?
    var precipitationSummary: String?

    init(
        capturedAt: Date = .now,
        latitude: Double? = nil,
        longitude: Double? = nil,
        weatherSummary: String? = nil,
        windSummary: String? = nil,
        cloudCoverSummary: String? = nil,
        precipitationSummary: String? = nil
    ) {
        self.id = UUID()
        self.capturedAt = capturedAt
        self.latitude = latitude
        self.longitude = longitude
        self.weatherSummary = weatherSummary
        self.windSummary = windSummary
        self.cloudCoverSummary = cloudCoverSummary
        self.precipitationSummary = precipitationSummary
    }

    var displaySummary: String {
        var parts: [String] = []

        if let weatherSummary, !weatherSummary.isEmpty {
            parts.append(weatherSummary)
        }
        if let windSummary, !windSummary.isEmpty {
            parts.append(windSummary)
        }
        if parts.isEmpty {
            parts.append("Weather not captured")
        }
        if let latitude, let longitude {
            parts.append(String(format: "%.4f, %.4f", latitude, longitude))
        }
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
        photoReference: String? = nil
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
        self.trip = trip
    }
}

@Model
final class PersonalBest {
    @Attribute(.unique) var id: UUID
    var species: String
    var longestLengthCm: Double?
    var heaviestWeightKg: Double?
    var updatedAt: Date

    init(
        species: String,
        longestLengthCm: Double? = nil,
        heaviestWeightKg: Double? = nil,
        updatedAt: Date = .now
    ) {
        self.id = UUID()
        self.species = species
        self.longestLengthCm = longestLengthCm
        self.heaviestWeightKg = heaviestWeightKg
        self.updatedAt = updatedAt
    }
}

func timeWindowLabel(for date: Date) -> String {
    let hour = Calendar.current.component(.hour, from: date)
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
