import Foundation

struct TripConditionDraft {
    let placeSummary: String?
    let timeWindowSummary: String?
    let lightLevelSummary: String?
    let weatherSummary: String?
    let windSummary: String?
    let cloudCoverSummary: String?
    let precipitationSummary: String?
    let waterClarity: WaterClarity
    let tideState: TideState
}

struct CatchEditorDraft {
    let species: String
    let lureOrBait: String
    let method: String
    let weightKg: Double?
    let lengthCm: Double?
    let waterDepthM: Double?
    let note: String
    let disposition: CatchDisposition
    let photoReference: String?
    let photoContentType: String?
}

struct CatchEditorSeed {
    let species: String
    let caughtAt: Date
    let lureOrBait: String
    let method: String
    let weight: String
    let length: String
    let waterDepth: String
    let note: String
    let disposition: CatchDisposition
}

enum TripEditingLogic {
    static func filteredSpots(spots: [Spot], selectedWaterbodyID: UUID?) -> [Spot] {
        guard let selectedWaterbodyID else { return spots }
        return spots.filter { $0.waterbody?.id == selectedWaterbodyID }
    }

    static func canSave(
        selectedWaterbodyID: UUID?,
        isTripActive: Bool,
        startAt: Date,
        endAt: Date
    ) -> Bool {
        selectedWaterbodyID != nil && (isTripActive || endAt >= startAt)
    }

    static func selectedSpotIDAfterWaterbodyChange(
        selectedSpotID: UUID?,
        filteredSpots: [Spot]
    ) -> UUID? {
        guard let selectedSpotID else { return nil }
        return filteredSpots.contains(where: { $0.id == selectedSpotID }) ? selectedSpotID : nil
    }

    static func normalizedText(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    static func normalizedOptionalText(_ value: String) -> String? {
        let trimmed = normalizedText(value)
        return trimmed.isEmpty ? nil : trimmed
    }

    static func normalizedDouble(_ value: String, locale: Locale = .current) -> Double? {
        LocaleDecimalParser.parse(normalizedText(value), locale: locale)
    }

    static func tripOutcome(endAt: Date?, catchCount: Int) -> TripOutcome {
        guard endAt != nil else { return .active }
        return catchCount == 0 ? .skunked : .caught
    }

    static func conditionDraft(
        placeSummary: String,
        timeWindowSummary: String,
        lightLevelSummary: String,
        weatherSummary: String,
        windSummary: String,
        cloudCoverSummary: String,
        precipitationSummary: String,
        waterClarity: WaterClarity,
        tideState: TideState
    ) -> TripConditionDraft {
        TripConditionDraft(
            placeSummary: normalizedOptionalText(placeSummary),
            timeWindowSummary: normalizedOptionalText(timeWindowSummary),
            lightLevelSummary: normalizedOptionalText(lightLevelSummary),
            weatherSummary: normalizedOptionalText(weatherSummary),
            windSummary: normalizedOptionalText(windSummary),
            cloudCoverSummary: normalizedOptionalText(cloudCoverSummary),
            precipitationSummary: normalizedOptionalText(precipitationSummary),
            waterClarity: waterClarity,
            tideState: tideState
        )
    }

    static func catchDraft(
        species: String,
        lureOrBait: String,
        method: String,
        weight: String,
        length: String,
        waterDepth: String,
        note: String,
        disposition: CatchDisposition,
        photoData: Data?
    ) -> CatchEditorDraft {
        CatchEditorDraft(
            species: normalizedText(species),
            lureOrBait: normalizedText(lureOrBait),
            method: normalizedText(method),
            weightKg: normalizedDouble(weight),
            lengthCm: normalizedDouble(length),
            waterDepthM: normalizedDouble(waterDepth),
            note: normalizedText(note),
            disposition: disposition,
            photoReference: photoData == nil ? nil : "embedded-photo",
            photoContentType: photoData == nil ? nil : "image/jpeg"
        )
    }

    static func duplicateCatchSeed(
        from catchRecord: CatchRecord,
        duplicateTimestamp: Date = .now
    ) -> CatchEditorSeed {
        CatchEditorSeed(
            species: catchRecord.species,
            caughtAt: duplicateTimestamp,
            lureOrBait: catchRecord.lureOrBait,
            method: catchRecord.method,
            weight: catchRecord.weightKg.map { "\($0)" } ?? "",
            length: catchRecord.lengthCm.map { "\($0)" } ?? "",
            waterDepth: catchRecord.waterDepthM.map { "\($0)" } ?? "",
            note: catchRecord.note,
            disposition: catchRecord.disposition
        )
    }

    static func applyMatchedSpot(_ spot: Spot, to trip: Trip) {
        trip.spot = spot
        if let waterbody = spot.waterbody {
            trip.waterbody = waterbody
        }
    }
}
