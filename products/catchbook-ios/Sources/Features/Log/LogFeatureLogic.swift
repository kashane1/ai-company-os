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

enum QuickCatchSaveAction {
    case save
    case saveAndAddAnother
}

struct QuickCatchContextSummary {
    let timeText: String
    let spotText: String
    let privacyText: String
}

struct TripSummaryCardItem: Identifiable {
    let id: String
    let title: String
    let value: String
    let subtitle: String?
}

enum LogFeatureLogic {
    static let startTripOptionalDetailsInitiallyExpanded = false
    static let startTripOptionalDetailsLabel = "Optional details"
    static let startTripOptionalDetailsHint = "Add target species or trip notes"

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

    static func quickCatchContextSummary(
        trip: Trip,
        now: Date = .now,
        formatTime: (Date) -> String = { AppFormatters.shortTime.string(from: $0) }
    ) -> QuickCatchContextSummary {
        QuickCatchContextSummary(
            timeText: formatTime(now),
            spotText: trip.spot?.title ?? trip.waterbody?.name ?? "General area",
            privacyText: "Saved privately"
        )
    }

    static func tripSummaryCards(
        trip: Trip,
        catches: [CatchRecord],
        durationFormatter: DateComponentsFormatter = AppFormatters.duration
    ) -> [TripSummaryCardItem] {
        let durationText = trip.endAt.flatMap { endAt in
            durationFormatter.string(from: endAt.timeIntervalSince(trip.startAt))
        } ?? "In progress"

        var cards: [TripSummaryCardItem] = [
            TripSummaryCardItem(
                id: "total-catches",
                title: "Total catches",
                value: "\(catches.count)",
                subtitle: catches.isEmpty ? "Skunked trips still stay in your history." : nil
            ),
            TripSummaryCardItem(
                id: "duration",
                title: "Trip duration",
                value: durationText,
                subtitle: nil
            ),
        ]

        if let topSpecies = topSpeciesSummary(from: catches) {
            cards.append(
                TripSummaryCardItem(
                    id: "top-species",
                    title: "Top species",
                    value: topSpecies.value,
                    subtitle: topSpecies.subtitle
                )
            )
        }

        if let bestCatch = bestCatchSummary(from: catches) {
            cards.append(
                TripSummaryCardItem(
                    id: "best-catch",
                    title: "Best catch",
                    value: bestCatch.value,
                    subtitle: bestCatch.subtitle
                )
            )
        }

        if let topLure = topLureSummary(from: catches) {
            cards.append(
                TripSummaryCardItem(
                    id: "top-lure",
                    title: "Top lure",
                    value: topLure.value,
                    subtitle: topLure.subtitle
                )
            )
        }

        return cards
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

    private static func topSpeciesSummary(from catches: [CatchRecord]) -> (value: String, subtitle: String)? {
        let counts = Dictionary(grouping: catches) {
            TripEditingLogic.normalizedText($0.speciesDisplayName)
        }.mapValues(\.count)

        guard let winner = counts.max(by: { lhs, rhs in
            if lhs.value != rhs.value {
                return lhs.value < rhs.value
            }
            return lhs.key > rhs.key
        }) else {
            return nil
        }

        return (
            value: winner.key,
            subtitle: "\(winner.value) \(winner.value == 1 ? "catch" : "catches") this trip"
        )
    }

    private static func topLureSummary(from catches: [CatchRecord]) -> (value: String, subtitle: String)? {
        let eligible = catches.compactMap { catchRecord -> String? in
            TripEditingLogic.normalizedOptionalText(catchRecord.lureOrBait)
        }
        let counts = Dictionary(grouping: eligible, by: { $0 }).mapValues(\.count)

        guard let winner = counts.max(by: { lhs, rhs in
            if lhs.value != rhs.value {
                return lhs.value < rhs.value
            }
            return lhs.key > rhs.key
        }) else {
            return nil
        }

        return (
            value: winner.key,
            subtitle: "Used on \(winner.value) \(winner.value == 1 ? "catch" : "catches")"
        )
    }

    private static func bestCatchSummary(from catches: [CatchRecord]) -> (value: String, subtitle: String)? {
        guard let bestCatch = catches.max(by: { lhs, rhs in
            bestCatchScore(for: lhs) < bestCatchScore(for: rhs)
        }) else {
            return nil
        }

        let metrics = [
            bestCatch.lengthCm.map { "\($0.formatted()) cm" },
            bestCatch.weightKg.map { "\($0.formatted()) kg" },
        ].compactMap { $0 }

        return (
            value: bestCatch.speciesDisplayName,
            subtitle: metrics.isEmpty ? AppFormatters.shortTime.string(from: bestCatch.caughtAt) : metrics.joined(separator: " • ")
        )
    }

    private static func bestCatchScore(for catchRecord: CatchRecord) -> Double {
        let lengthScore = catchRecord.lengthCm ?? 0
        let weightScore = (catchRecord.weightKg ?? 0) * 10
        return max(lengthScore, weightScore)
    }
}
