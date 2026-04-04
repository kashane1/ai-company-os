import Foundation

struct StartTripDraft {
    let targetSpecies: String
    let notes: String
}

enum QuickCatchField: Equatable {
    case species
    case lureOrBait
    case method
    case weight
    case length
    case note
    case photo
    case save
}

struct QuickCatchDefaults {
    let lureOrBait: String
    let method: String
    let didPrimeDefaults: Bool
}

struct QuickCatchResetState {
    let species: String
    let lureOrBait: String
    let method: String
    let weight: String
    let length: String
    let note: String
    let showingOptionalFields: Bool
    let photoData: Data?
}

enum LogFeatureLogic {
    static let quickCatchPrimaryFields: [QuickCatchField] = [
        .species,
        .lureOrBait,
        .save,
    ]

    static let quickCatchOptionalFields: [QuickCatchField] = [
        .method,
        .weight,
        .length,
        .note,
        .photo,
    ]

    static func filteredSpots(spots: [Spot], selectedWaterbodyID: UUID?) -> [Spot] {
        guard let selectedWaterbodyID else { return spots }
        return spots.filter { $0.waterbody?.id == selectedWaterbodyID }
    }

    static func startTripDraft(targetSpecies: String, notes: String) -> StartTripDraft {
        StartTripDraft(
            targetSpecies: TripEditingLogic.normalizedText(targetSpecies),
            notes: TripEditingLogic.normalizedText(notes)
        )
    }

    static func recentSpeciesSuggestions(
        targetSpeciesList: [String],
        catches: [CatchRecord],
        limit: Int = 4
    ) -> [String] {
        var suggestions: [String] = []
        for target in targetSpeciesList {
            guard !suggestions.contains(target) else { continue }
            suggestions.append(target)
            if suggestions.count == limit { return suggestions }
        }
        for catchRecord in catches {
            let value = TripEditingLogic.normalizedText(catchRecord.species)
            guard !value.isEmpty, !suggestions.contains(value) else { continue }
            suggestions.append(value)
            if suggestions.count == limit { break }
        }
        return suggestions
    }

    static func recentLureSuggestions(
        catchesForSpot: [CatchRecord],
        allCatches: [CatchRecord],
        limit: Int = 4
    ) -> [String] {
        var suggestions: [String] = []
        for catchRecord in catchesForSpot + allCatches {
            let value = TripEditingLogic.normalizedText(catchRecord.lureOrBait)
            guard !value.isEmpty, !suggestions.contains(value) else { continue }
            suggestions.append(value)
            if suggestions.count == limit { break }
        }
        return suggestions
    }

    static func primeDefaultsIfNeeded(
        didPrimeDefaults: Bool,
        lureOrBait: String,
        method: String,
        catchesForSpot: [CatchRecord],
        allCatches: [CatchRecord]
    ) -> QuickCatchDefaults {
        guard !didPrimeDefaults else {
            return QuickCatchDefaults(
                lureOrBait: lureOrBait,
                method: method,
                didPrimeDefaults: didPrimeDefaults
            )
        }
        guard let recentCatch = catchesForSpot.first ?? allCatches.first else {
            return QuickCatchDefaults(
                lureOrBait: lureOrBait,
                method: method,
                didPrimeDefaults: true
            )
        }
        return QuickCatchDefaults(
            lureOrBait: lureOrBait.isEmpty ? recentCatch.lureOrBait : lureOrBait,
            method: method.isEmpty ? recentCatch.method : method,
            didPrimeDefaults: true
        )
    }

    static func endTripOutcome(catchCount: Int) -> TripOutcome {
        catchCount == 0 ? .skunked : .caught
    }

    static func resetQuickCatchStateAfterSave(
        lureOrBait: String,
        method: String
    ) -> QuickCatchResetState {
        QuickCatchResetState(
            species: "",
            lureOrBait: lureOrBait,
            method: method,
            weight: "",
            length: "",
            note: "",
            showingOptionalFields: false,
            photoData: nil
        )
    }
}
