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
    case spotFallback
    case waterbodyFallback
    case tripFallback
    case weatherDeferred
    case weatherKit
}

enum TripCoordinateSource: Equatable {
    case observed
    case spotFallback
    case waterbodyFallback
    case unresolved

    var confidenceLabel: String? {
        switch self {
        case .observed:
            return "At"
        case .spotFallback, .waterbodyFallback:
            return "Near"
        case .unresolved:
            return nil
        }
    }
}

enum WaterClarity: String, CaseIterable, Codable, Identifiable {
    case notRecorded
    case clear
    case stained
    case muddy

    var id: String { rawValue }

    var label: String {
        switch self {
        case .notRecorded:
            return "Not recorded"
        case .clear:
            return "Clear"
        case .stained:
            return "Stained"
        case .muddy:
            return "Muddy"
        }
    }
}

enum TideState: String, CaseIterable, Codable, Identifiable {
    case notRecorded
    case incoming
    case outgoing
    case high
    case low
    case slack

    var id: String { rawValue }

    var label: String {
        switch self {
        case .notRecorded:
            return "Not recorded"
        case .incoming:
            return "Incoming"
        case .outgoing:
            return "Outgoing"
        case .high:
            return "High"
        case .low:
            return "Low"
        case .slack:
            return "Slack"
        }
    }
}

enum MoonPhase: String, CaseIterable, Codable, Identifiable {
    case newMoon
    case waxingCrescent
    case firstQuarter
    case waxingGibbous
    case fullMoon
    case waningGibbous
    case lastQuarter
    case waningCrescent

    var id: String { rawValue }

    var label: String {
        switch self {
        case .newMoon:
            return "New moon"
        case .waxingCrescent:
            return "Waxing crescent"
        case .firstQuarter:
            return "First quarter"
        case .waxingGibbous:
            return "Waxing gibbous"
        case .fullMoon:
            return "Full moon"
        case .waningGibbous:
            return "Waning gibbous"
        case .lastQuarter:
            return "Last quarter"
        case .waningCrescent:
            return "Waning crescent"
        }
    }
}

enum SpotPinColor: String, CaseIterable, Codable, Identifiable {
    case blue
    case green
    case amber
    case red
    case purple
    case teal

    var id: String { rawValue }

    var label: String {
        switch self {
        case .blue: return "Blue"
        case .green: return "Green"
        case .amber: return "Amber"
        case .red: return "Red"
        case .purple: return "Purple"
        case .teal: return "Teal"
        }
    }
}

enum CatchDisposition: String, CaseIterable, Codable, Identifiable {
    case notRecorded
    case released
    case kept

    var id: String { rawValue }

    var label: String {
        switch self {
        case .notRecorded:
            return "Not recorded"
        case .released:
            return "Released"
        case .kept:
            return "Kept"
        }
    }
}

@Model
final class Waterbody {
    @Attribute(.unique) var id: UUID
    // Property-level defaults are required for SwiftData lightweight
    // migration; see commit af263a1 and the ConditionSnapshot fix.
    var name: String = ""
    var typeRawValue: String = WaterbodyType.lake.rawValue
    var latitude: Double?
    var longitude: Double?
    var isPrivate: Bool = true
    var createdAt: Date = Date.distantPast

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
    var title: String = ""
    var latitude: Double?
    var longitude: Double?
    var notes: String = ""
    var isPrivate: Bool = true
    var createdAt: Date = Date.distantPast
    // Property-level default required for SwiftData lightweight migration —
    // legacy rows backfill to the default pin color.
    var pinColorRawValue: String = SpotPinColor.blue.rawValue
    var waterbody: Waterbody?

    init(
        title: String,
        waterbody: Waterbody?,
        latitude: Double? = nil,
        longitude: Double? = nil,
        notes: String = "",
        isPrivate: Bool = true,
        pinColor: SpotPinColor = .blue,
        createdAt: Date = .now
    ) {
        self.id = UUID()
        self.title = title
        self.latitude = latitude
        self.longitude = longitude
        self.notes = notes
        self.isPrivate = isPrivate
        self.pinColorRawValue = pinColor.rawValue
        self.createdAt = createdAt
        self.waterbody = waterbody
    }

    var pinColor: SpotPinColor {
        get { SpotPinColor(rawValue: pinColorRawValue) ?? .blue }
        set { pinColorRawValue = newValue.rawValue }
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
    var capturedAt: Date = Date.distantPast
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
    // Property-level defaults are required for SwiftData lightweight
    // migration to backfill rows created before these columns existed.
    // Init defaults only apply to new objects; see commit af263a1 for the
    // same fix on CatchRecord.gear.
    var waterClarityRawValue: String = WaterClarity.notRecorded.rawValue
    var moonPhaseRawValue: String = MoonPhase.newMoon.rawValue
    var pressureHPa: Double?
    var tideStateRawValue: String = TideState.notRecorded.rawValue
    var captureStatusRawValue: String = ConditionCaptureStatus.fallback.rawValue
    var sourceRawValue: String = ConditionSource.tripFallback.rawValue

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
        waterClarity: WaterClarity = .notRecorded,
        moonPhase: MoonPhase? = nil,
        pressureHPa: Double? = nil,
        tideState: TideState = .notRecorded,
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
        self.waterClarityRawValue = waterClarity.rawValue
        self.moonPhaseRawValue = (moonPhase ?? moonPhaseValue(for: capturedAt)).rawValue
        self.pressureHPa = pressureHPa
        self.tideStateRawValue = tideState.rawValue
        self.captureStatusRawValue = captureStatus.rawValue
        self.sourceRawValue = source.rawValue
    }

    var captureStatus: ConditionCaptureStatus {
        ConditionCaptureStatus(rawValue: captureStatusRawValue) ?? .fallback
    }

    var source: ConditionSource {
        ConditionSource(rawValue: sourceRawValue) ?? .tripFallback
    }

    var waterClarity: WaterClarity {
        get { WaterClarity(rawValue: waterClarityRawValue) ?? .notRecorded }
        set { waterClarityRawValue = newValue.rawValue }
    }

    var moonPhase: MoonPhase {
        get { MoonPhase(rawValue: moonPhaseRawValue) ?? moonPhaseValue(for: capturedAt) }
        set { moonPhaseRawValue = newValue.rawValue }
    }

    var tideState: TideState {
        get { TideState(rawValue: tideStateRawValue) ?? .notRecorded }
        set { tideStateRawValue = newValue.rawValue }
    }

    var coordinateSummary: String? {
        guard let latitude, let longitude else { return nil }
        return String(format: "%.4f, %.4f", latitude, longitude)
    }

    var locationConfidenceLabel: String? {
        guard coordinateSummary != nil else { return nil }

        switch source {
        case .deviceLocation:
            return "At"
        case .spotFallback, .waterbodyFallback, .tripFallback, .weatherDeferred, .weatherKit:
            return "Near"
        }
    }

    var locationSummaryLine: String? {
        let parts = [placeSummary, coordinateSummary].compactMap { value -> String? in
            guard let value, !value.isEmpty else { return nil }
            return value
        }

        guard !parts.isEmpty else { return nil }

        let summary = parts.joined(separator: " · ")
        guard let locationConfidenceLabel else { return summary }
        return "\(locationConfidenceLabel) \(summary)"
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
        if let pressureSummary {
            parts.append(pressureSummary)
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

    var pressureSummary: String? {
        guard let pressureHPa else { return nil }
        let measurement = Measurement(value: pressureHPa, unit: UnitPressure.hectopascals)
        let formatter = MeasurementFormatter()
        formatter.unitOptions = [.providedUnit]
        formatter.numberFormatter.maximumFractionDigits = 0
        return formatter.string(from: measurement)
    }

    var claritySummary: String? {
        waterClarity == .notRecorded ? nil : waterClarity.label
    }

    var tideSummary: String? {
        tideState == .notRecorded ? nil : tideState.label
    }
}

@Model
final class Trip {
    @Attribute(.unique) var id: UUID
    var startAt: Date = Date.distantPast
    var endAt: Date?
    var targetSpecies: String = ""
    var notes: String = ""
    var outcomeRawValue: String = TripOutcome.active.rawValue
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

    var coordinateSource: TripCoordinateSource {
        if coordinateIfPresent(latitude: conditionSnapshot?.latitude, longitude: conditionSnapshot?.longitude) != nil {
            return .observed
        }
        if coordinateIfPresent(latitude: spot?.latitude, longitude: spot?.longitude) != nil {
            return .spotFallback
        }
        if coordinateIfPresent(latitude: waterbody?.latitude, longitude: waterbody?.longitude) != nil {
            return .waterbodyFallback
        }
        return .unresolved
    }

    var resolvedCoordinate: CLLocationCoordinate2D? {
        switch coordinateSource {
        case .observed:
            return coordinateIfPresent(latitude: conditionSnapshot?.latitude, longitude: conditionSnapshot?.longitude)
        case .spotFallback:
            return coordinateIfPresent(latitude: spot?.latitude, longitude: spot?.longitude)
        case .waterbodyFallback:
            return coordinateIfPresent(latitude: waterbody?.latitude, longitude: waterbody?.longitude)
        case .unresolved:
            return nil
        }
    }

    var locationConfidenceLabel: String? {
        coordinateSource.confidenceLabel
    }

    var durationInterval: TimeInterval? {
        guard let endAt else { return nil }
        let duration = endAt.timeIntervalSince(startAt)
        return duration > 0 ? duration : nil
    }
}

@Model
final class CatchRecord {
    @Attribute(.unique) var id: UUID
    var species: String = ""
    var caughtAt: Date = Date.distantPast
    var lureOrBait: String = ""
    var method: String = ""
    var gear: String = ""
    var weightKg: Double?
    var lengthCm: Double?
    var waterDepthM: Double?
    var note: String = ""
    var dispositionRawValue: String = CatchDisposition.notRecorded.rawValue
    var photoReference: String?
    @Attribute(.externalStorage) var photoData: Data?
    var photoContentType: String?
    @Relationship(deleteRule: .cascade, inverse: \CatchPhoto.catchRecord) var photos: [CatchPhoto]
    var trip: Trip?

    init(
        species: String,
        trip: Trip?,
        caughtAt: Date = .now,
        lureOrBait: String = "",
        method: String = "",
        gear: String = "",
        weightKg: Double? = nil,
        lengthCm: Double? = nil,
        waterDepthM: Double? = nil,
        note: String = "",
        disposition: CatchDisposition = .notRecorded,
        photoReference: String? = nil,
        photoData: Data? = nil,
        photoContentType: String? = nil
    ) {
        self.id = UUID()
        self.species = species
        self.caughtAt = caughtAt
        self.lureOrBait = lureOrBait
        self.method = method
        self.gear = gear
        self.weightKg = weightKg
        self.lengthCm = lengthCm
        self.waterDepthM = waterDepthM
        self.note = note
        self.dispositionRawValue = disposition.rawValue
        self.photoReference = photoReference
        self.photoData = photoData
        self.photoContentType = photoContentType
        self.photos = []
        self.trip = trip
    }

    var disposition: CatchDisposition {
        get { CatchDisposition(rawValue: dispositionRawValue) ?? .notRecorded }
        set { dispositionRawValue = newValue.rawValue }
    }

    var hasPhoto: Bool {
        primaryPhotoData != nil
    }

    var speciesDisplayName: String {
        let trimmed = species.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "Species not logged" : trimmed
    }

    var sortedPhotos: [CatchPhoto] {
        photos.sorted {
            if $0.sortOrder != $1.sortOrder {
                return $0.sortOrder < $1.sortOrder
            }
            return $0.createdAt < $1.createdAt
        }
    }

    var primaryPhotoData: Data? {
        sortedPhotos.first?.photoData ?? photoData
    }

    var primaryPhotoContentType: String? {
        sortedPhotos.first?.photoContentType ?? photoContentType
    }

    var photoCount: Int {
        if !sortedPhotos.isEmpty {
            return sortedPhotos.count
        }
        return photoData == nil ? 0 : 1
    }
}

@Model
final class CatchPhoto {
    @Attribute(.unique) var id: UUID
    var createdAt: Date = Date.distantPast
    var sortOrder: Int = 0
    var photoReference: String?
    var photoContentType: String?
    @Attribute(.externalStorage) var photoData: Data?
    var catchRecord: CatchRecord?

    init(
        catchRecord: CatchRecord? = nil,
        createdAt: Date = .now,
        sortOrder: Int = 0,
        photoReference: String? = nil,
        photoContentType: String? = nil,
        photoData: Data? = nil
    ) {
        self.id = UUID()
        self.createdAt = createdAt
        self.sortOrder = sortOrder
        self.photoReference = photoReference
        self.photoContentType = photoContentType
        self.photoData = photoData
        self.catchRecord = catchRecord
    }
}

@Model
final class PersonalBest {
    @Attribute(.unique) var id: UUID
    var species: String = ""
    var longestLengthCm: Double?
    var heaviestWeightKg: Double?
    var longestCatchID: UUID?
    var heaviestCatchID: UUID?
    var updatedAt: Date = Date.distantPast

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

// MARK: - Saved Lure

@Model
final class SavedLure {
    @Attribute(.unique) var id: UUID
    var name: String = ""
    var color: String = ""
    var notes: String = ""
    var createdAt: Date = Date.distantPast

    init(name: String, color: String = "", notes: String = "") {
        self.id = UUID()
        self.name = name
        self.color = color
        self.notes = notes
        self.createdAt = .now
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

func moonPhaseValue(for date: Date, calendar: Calendar = .current) -> MoonPhase {
    let referenceComponents = DateComponents(
        calendar: calendar,
        timeZone: TimeZone(secondsFromGMT: 0),
        year: 2000,
        month: 1,
        day: 6,
        hour: 18,
        minute: 14
    )
    let synodicMonth = 29.53058867
    guard let referenceDate = referenceComponents.date else { return .newMoon }

    let daysSinceReference = date.timeIntervalSince(referenceDate) / 86_400
    let normalized = daysSinceReference.truncatingRemainder(dividingBy: synodicMonth)
    let phaseAge = normalized >= 0 ? normalized : normalized + synodicMonth
    let index = Int(((phaseAge / synodicMonth) * 8).rounded()) % 8

    switch index {
    case 0: return .newMoon
    case 1: return .waxingCrescent
    case 2: return .firstQuarter
    case 3: return .waxingGibbous
    case 4: return .fullMoon
    case 5: return .waningGibbous
    case 6: return .lastQuarter
    default: return .waningCrescent
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

func bestAvailableConditionSource(
    location: CLLocation?,
    spot: Spot?,
    waterbody: Waterbody?
) -> ConditionSource {
    if location?.coordinate != nil {
        return .deviceLocation
    }
    if coordinateIfPresent(latitude: spot?.latitude, longitude: spot?.longitude) != nil {
        return .spotFallback
    }
    if coordinateIfPresent(latitude: waterbody?.latitude, longitude: waterbody?.longitude) != nil {
        return .waterbodyFallback
    }
    return .tripFallback
}

func coordinateIfPresent(latitude: Double?, longitude: Double?) -> CLLocationCoordinate2D? {
    guard let latitude, let longitude else { return nil }
    return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
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
