import Foundation

struct StartTripDraft {
    let targetSpecies: String
    let notes: String
}

enum QuickCatchField: Equatable {
    case species
    case lureOrBait
    case disposition
    case method
    case weight
    case length
    case waterDepth
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
    let disposition: CatchDisposition
    let method: String
    let weight: String
    let length: String
    let waterDepth: String
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
        .disposition,
        .method,
        .weight,
        .length,
        .waterDepth,
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
        historySuggestions(
            query: "",
            prioritizedValues: targetSpeciesList,
            globalValues: catches.map(\.species),
            limit: limit
        )
    }

    static func recentLureSuggestions(
        catchesForSpot: [CatchRecord],
        allCatches: [CatchRecord],
        limit: Int = 4
    ) -> [String] {
        historySuggestions(
            query: "",
            spotValues: catchesForSpot.map(\.lureOrBait),
            globalValues: allCatches.map(\.lureOrBait),
            limit: limit
        )
    }

    static func historySuggestions(
        query: String,
        prioritizedValues: [String] = [],
        spotValues: [String] = [],
        waterbodyValues: [String] = [],
        globalValues: [String] = [],
        limit: Int = 4
    ) -> [String] {
        let normalizedQuery = normalizedSuggestionKey(query)
        let skipExactMatch = !normalizedQuery.isEmpty

        var seen: Set<String> = []
        var suggestions: [String] = []

        func append(values: [String]) {
            for value in values {
                let trimmed = TripEditingLogic.normalizedText(value)
                let key = normalizedSuggestionKey(trimmed)
                guard !trimmed.isEmpty, !seen.contains(key) else { continue }
                if skipExactMatch && key == normalizedQuery { continue }
                if !normalizedQuery.isEmpty && !key.contains(normalizedQuery) { continue }
                seen.insert(key)
                suggestions.append(trimmed)
                if suggestions.count == limit { return }
            }
        }

        append(values: prioritizedValues)
        if suggestions.count < limit { append(values: spotValues) }
        if suggestions.count < limit { append(values: waterbodyValues) }
        if suggestions.count < limit { append(values: globalValues) }

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
        let catchesPerHourText = catchesPerHourText(trip: trip, catchCount: catches.count)

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

        if let catchesPerHourText {
            cards.append(
                TripSummaryCardItem(
                    id: "catch-rate",
                    title: "Catches / hour",
                    value: catchesPerHourText,
                    subtitle: "Based on ended-trip duration"
                )
            )
        }

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

    static func shouldOfferCreateSpot(from trip: Trip) -> Bool {
        trip.spot == nil && trip.waterbody != nil && trip.resolvedCoordinate != nil
    }

    static func createSpotPrompt(for trip: Trip) -> String {
        let confidenceLead = trip.locationConfidenceLabel ?? "Near"
        return "\(confidenceLead) this saved trip location into a reusable spot for faster recall next time."
    }

    private static func normalizedSuggestionKey(_ value: String) -> String {
        TripEditingLogic.normalizedText(value).folding(options: [.caseInsensitive, .diacriticInsensitive], locale: .current)
    }

    static func resetQuickCatchStateAfterSave(
        lureOrBait: String,
        method: String
    ) -> QuickCatchResetState {
        QuickCatchResetState(
            species: "",
            lureOrBait: lureOrBait,
            disposition: .notRecorded,
            method: method,
            weight: "",
            length: "",
            waterDepth: "",
            note: "",
            showingOptionalFields: false,
            photoData: nil
        )
    }

    static func catchesPerHourText(trip: Trip, catchCount: Int) -> String? {
        guard let durationInterval = trip.durationInterval, catchCount > 0 else { return nil }
        let hours = durationInterval / 3_600
        guard hours > 0 else { return nil }

        let rate = Double(catchCount) / hours
        if abs(rate.rounded() - rate) < 0.05 {
            return String(format: "%.0f", rate.rounded())
        }
        return String(format: "%.1f", rate)
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
