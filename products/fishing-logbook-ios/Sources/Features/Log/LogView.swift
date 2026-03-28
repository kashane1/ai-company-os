import SwiftData
import SwiftUI

struct LogView: View {
    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]
    @Query(sort: \Spot.createdAt) private var spots: [Spot]
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]

    private var activeTrip: Trip? {
        trips.first(where: \.isActive)
    }

    var body: some View {
        NavigationStack {
            Group {
                if let activeTrip {
                    ActiveTripView(trip: activeTrip)
                } else {
                    StartTripView(waterbodies: waterbodies, spots: spots)
                }
            }
            .navigationTitle("Log")
        }
    }
}

private struct StartTripView: View {
    @Environment(\.modelContext) private var modelContext

    @StateObject private var locationRecorder = LocationRecorder()
    @State private var selectedWaterbodyID: UUID?
    @State private var selectedSpotID: UUID?
    @State private var targetSpecies = ""
    @State private var tripNotes = ""
    @State private var showingWaterbodyForm = false
    @State private var showingSpotForm = false

    let waterbodies: [Waterbody]
    let spots: [Spot]

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Start a private trip")
                        .font(.headline)
                    Text("Capture time, place, and optional context now. Keep the rest lightweight.")
                        .foregroundStyle(.secondary)
                }
            }

            if waterbodies.isEmpty {
                Section {
                    Text("Create your first waterbody to start logging.")
                        .foregroundStyle(.secondary)
                    Button("Add waterbody") {
                        showingWaterbodyForm = true
                    }
                    .buttonStyle(.borderedProminent)
                }
            } else {
                Section("Trip Setup") {
                    Picker("Waterbody", selection: $selectedWaterbodyID) {
                        Text("Choose a waterbody").tag(Optional<UUID>.none)
                        ForEach(waterbodies, id: \.id) { waterbody in
                            Text(waterbody.name).tag(Optional(waterbody.id))
                        }
                    }

                    Picker("Spot", selection: $selectedSpotID) {
                        Text("No specific spot").tag(Optional<UUID>.none)
                        ForEach(filteredSpots, id: \.id) { spot in
                            Text(spot.title).tag(Optional(spot.id))
                        }
                    }

                    TextField("Target species (optional)", text: $targetSpecies)
                    TextField("Trip notes (optional)", text: $tripNotes, axis: .vertical)
                }

                Section {
                    Button("Add waterbody") {
                        showingWaterbodyForm = true
                    }
                    Button("Add spot") {
                        showingSpotForm = true
                    }
                }

                Section("Conditions") {
                    if let location = locationRecorder.lastLocation {
                        Label(
                            String(
                                format: "Location ready: %.4f, %.4f",
                                location.coordinate.latitude,
                                location.coordinate.longitude
                            ),
                            systemImage: "location"
                        )
                    } else {
                        Label("Trip will still start even if location is unavailable.", systemImage: "location.slash")
                            .foregroundStyle(.secondary)
                    }
                }

                Section {
                    Button("Start trip") {
                        startTrip()
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(selectedWaterbody == nil)
                }
            }
        }
        .onAppear {
            locationRecorder.requestIfNeeded()
        }
        .sheet(isPresented: $showingWaterbodyForm) {
            NewWaterbodyForm { waterbody in
                selectedWaterbodyID = waterbody.id
            }
        }
        .sheet(isPresented: $showingSpotForm) {
            NewSpotForm(preselectedWaterbodyID: selectedWaterbodyID) { spot in
                selectedSpotID = spot.id
            }
        }
    }

    private var selectedWaterbody: Waterbody? {
        waterbodies.first(where: { $0.id == selectedWaterbodyID })
    }

    private var selectedSpot: Spot? {
        spots.first(where: { $0.id == selectedSpotID })
    }

    private var filteredSpots: [Spot] {
        guard let selectedWaterbodyID else { return spots }
        return spots.filter { $0.waterbody?.id == selectedWaterbodyID }
    }

    private func startTrip() {
        let location = locationRecorder.lastLocation
        let snapshot = ConditionSnapshot(
            capturedAt: .now,
            latitude: location?.coordinate.latitude,
            longitude: location?.coordinate.longitude
        )
        let trip = Trip(
            waterbody: selectedWaterbody,
            spot: selectedSpot,
            conditionSnapshot: snapshot,
            targetSpecies: targetSpecies.trimmingCharacters(in: .whitespacesAndNewlines),
            notes: tripNotes.trimmingCharacters(in: .whitespacesAndNewlines)
        )
        modelContext.insert(snapshot)
        modelContext.insert(trip)
        try? modelContext.save()

        targetSpecies = ""
        tripNotes = ""
    }
}

private struct ActiveTripView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var trip: Trip

    @Query(sort: \Trip.startAt, order: .reverse) private var allTrips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var allCatches: [CatchRecord]

    @State private var species = ""
    @State private var lureOrBait = ""
    @State private var method = ""
    @State private var weight = ""
    @State private var length = ""
    @State private var note = ""
    @State private var showingOptionalFields = false
    @State private var didPrimeDefaults = false

    private var catchesForTrip: [CatchRecord] {
        allCatches.filter { $0.trip?.id == trip.id }
    }

    private var catchesForSpot: [CatchRecord] {
        guard let spotID = trip.spot?.id else { return [] }
        return allCatches.filter { $0.trip?.spot?.id == spotID }
    }

    private var recallSummary: SpotRecallSummary? {
        guard let spot = trip.spot else { return nil }
        return SpotRecallSummary.build(for: spot, trips: allTrips, catches: allCatches)
    }

    private var recentSpeciesSuggestions: [String] {
        var suggestions: [String] = []
        if !trip.targetSpecies.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            suggestions.append(trip.targetSpecies)
        }
        for catchRecord in allCatches {
            let value = catchRecord.species.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !value.isEmpty, !suggestions.contains(value) else { continue }
            suggestions.append(value)
            if suggestions.count == 4 { break }
        }
        return suggestions
    }

    private var recentLureSuggestions: [String] {
        var suggestions: [String] = []
        for catchRecord in catchesForSpot + allCatches {
            let value = catchRecord.lureOrBait.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !value.isEmpty, !suggestions.contains(value) else { continue }
            suggestions.append(value)
            if suggestions.count == 4 { break }
        }
        return suggestions
    }

    var body: some View {
        List {
            Section {
                ActiveTripStatusCard(
                    trip: trip,
                    catchCount: catchesForTrip.count,
                    elapsedText: elapsedText,
                    contextSummary: trip.conditionSnapshot?.displaySummary
                )
            }

            if let recallSummary, !recallSummary.cards.isEmpty {
                Section("Recall For This Spot") {
                    ForEach(recallSummary.cards.prefix(3), id: \.id) { card in
                        DeterministicInsightCardView(card: card)
                    }
                }
            }

            Section("Quick Catch") {
                TextField("Species", text: $species)
                    .textInputAutocapitalization(.words)
                    .submitLabel(.done)

                if !recentSpeciesSuggestions.isEmpty {
                    suggestionRow(title: "Species", values: recentSpeciesSuggestions) { value in
                        species = value
                    }
                }

                TextField("Lure or bait", text: $lureOrBait)
                    .textInputAutocapitalization(.words)
                if !recentLureSuggestions.isEmpty {
                    suggestionRow(title: "Lure", values: recentLureSuggestions) { value in
                        lureOrBait = value
                    }
                }

                TextField("Method", text: $method)
                    .textInputAutocapitalization(.words)

                DisclosureGroup("Optional details", isExpanded: $showingOptionalFields) {
                    TextField("Weight (kg)", text: $weight)
                        .keyboardType(.decimalPad)
                    TextField("Length (cm)", text: $length)
                        .keyboardType(.decimalPad)
                    TextField("Note", text: $note, axis: .vertical)
                }

                Button("Save catch") {
                    saveCatch()
                }
                .buttonStyle(.borderedProminent)
                .disabled(species.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                Text("Time and spot are filled from the active trip.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("This Trip") {
                if catchesForTrip.isEmpty {
                    Text("No catches logged yet. Keep it fast and log the next one here.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(catchesForTrip, id: \.id) { catchRecord in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(catchRecord.species)
                                .font(.headline)
                            Text(AppFormatters.shortTime.string(from: catchRecord.caughtAt))
                                .foregroundStyle(.secondary)
                            if !catchRecord.lureOrBait.isEmpty {
                                Text(catchRecord.lureOrBait)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }

            Section {
                Button("End trip") {
                    endTrip()
                }
                .foregroundStyle(.red)
            }
        }
        .onAppear {
            primeDefaultsIfNeeded()
        }
    }

    private func saveCatch() {
        let catchRecord = CatchRecord(
            species: species.trimmingCharacters(in: .whitespacesAndNewlines),
            trip: trip,
            caughtAt: .now,
            lureOrBait: lureOrBait.trimmingCharacters(in: .whitespacesAndNewlines),
            method: method.trimmingCharacters(in: .whitespacesAndNewlines),
            weightKg: Double(weight),
            lengthCm: Double(length),
            note: note.trimmingCharacters(in: .whitespacesAndNewlines)
        )

        modelContext.insert(catchRecord)
        try? PersonalBestService.refresh(with: catchRecord, in: modelContext)
        try? modelContext.save()

        species = ""
        weight = ""
        length = ""
        note = ""
        showingOptionalFields = false
    }

    private func endTrip() {
        trip.endAt = .now
        trip.outcomeRawValue = catchesForTrip.isEmpty ? TripOutcome.skunked.rawValue : TripOutcome.caught.rawValue
        try? modelContext.save()
    }

    private var elapsedText: String {
        AppFormatters.duration.string(from: Date().timeIntervalSince(trip.startAt)) ?? "Now"
    }

    private func primeDefaultsIfNeeded() {
        guard !didPrimeDefaults else { return }
        didPrimeDefaults = true
        guard let recentCatch = catchesForSpot.first ?? allCatches.first else { return }
        if lureOrBait.isEmpty {
            lureOrBait = recentCatch.lureOrBait
        }
        if method.isEmpty {
            method = recentCatch.method
        }
    }

    @ViewBuilder
    private func suggestionRow(title: String, values: [String], apply: @escaping (String) -> Void) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                ForEach(values, id: \.self) { value in
                    Button(value) {
                        apply(value)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
            }
            .padding(.vertical, 4)
        }
    }
}

private struct ActiveTripStatusCard: View {
    let trip: Trip
    let catchCount: Int
    let elapsedText: String
    let contextSummary: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(trip.title)
                        .font(.headline)
                    Text("In progress")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.teal)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    Text("\(catchCount)")
                        .font(.title2.bold())
                    Text(catchCount == 1 ? "catch" : "catches")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            HStack(spacing: 16) {
                Label(elapsedText, systemImage: "timer")
                if let spot = trip.spot?.title {
                    Label(spot, systemImage: "mappin")
                }
            }
            .font(.footnote)
            .foregroundStyle(.secondary)

            if let contextSummary {
                Text(contextSummary)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(14)
        .background(.teal.opacity(0.08), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}
