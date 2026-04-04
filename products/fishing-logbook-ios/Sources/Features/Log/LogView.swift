import PhotosUI
import SwiftData
import SwiftUI

struct LogView: View {
    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]
    @Query(sort: \Spot.createdAt) private var spots: [Spot]
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]

    var onTripEnded: ((Trip) -> Void)?

    private var activeTrip: Trip? {
        trips.first(where: \.isActive)
    }

    var body: some View {
        NavigationStack {
            Group {
                if let activeTrip {
                    ActiveTripView(trip: activeTrip, onTripEnded: onTripEnded)
                } else {
                    StartTripView(waterbodies: waterbodies, spots: spots)
                }
            }
            .navigationTitle("Log")
        }
    }
}

// MARK: - Start Trip

private struct StartTripView: View {
    @Environment(\.modelContext) private var modelContext

    @StateObject private var locationRecorder = LocationRecorder()
    @State private var selectedWaterbodyID: UUID?
    @State private var selectedSpotID: UUID?
    @State private var targetSpecies = ""
    @State private var tripNotes = ""
    @State private var showingOptionalDetails = LogFeatureLogic.startTripOptionalDetailsInitiallyExpanded
    @State private var showingWaterbodyForm = false
    @State private var showingSpotForm = false

    let waterbodies: [Waterbody]
    let spots: [Spot]

    private var conditionPreview: ConditionCapturePreview {
        ConditionCaptureService.preview(
            waterbody: selectedWaterbody,
            spot: selectedSpot,
            location: locationRecorder.lastLocation
        )
    }

    var body: some View {
        List {
            if waterbodies.isEmpty {
                Section {
                    SectionEmptyState(
                        icon: "water.waves",
                        title: "Add your first water",
                        subtitle: "Create a waterbody to start logging trips and catches."
                    )
                    Button {
                        showingWaterbodyForm = true
                    } label: {
                        Label("Add Waterbody", systemImage: "plus.circle.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.appAccent)
                    .listRowSeparator(.hidden)
                }
            } else {
                Section {
                    Picker("Waterbody", selection: $selectedWaterbodyID) {
                        Text("Select water").tag(Optional<UUID>.none)
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

                    HStack(spacing: Spacing.sm) {
                        Button {
                            showingWaterbodyForm = true
                        } label: {
                            Label("New Water", systemImage: "plus")
                                .font(.footnote)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)

                        Button {
                            showingSpotForm = true
                        } label: {
                            Label("New Spot", systemImage: "plus")
                                .font(.footnote)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                    .listRowSeparator(.hidden, edges: .bottom)
                } header: {
                    Text("Where")
                }

                Section("Conditions") {
                    ConditionPreviewRow(preview: conditionPreview)
                }

                Section {
                    DisclosureGroup(
                        isExpanded: $showingOptionalDetails,
                        content: {
                            TextField("Target species, separated by commas", text: $targetSpecies)
                                .textInputAutocapitalization(.words)
                                .accessibilityIdentifier("startTrip.targetSpeciesField")
                            Text("Optional. Enter one or more targets. We turn them into quick-catch suggestions.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                            TextField("Trip notes", text: $tripNotes, axis: .vertical)
                                .lineLimit(2...4)
                        },
                        label: {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                Text(LogFeatureLogic.startTripOptionalDetailsLabel)
                                if !showingOptionalDetails {
                                    Text(LogFeatureLogic.startTripOptionalDetailsHint)
                                        .font(.footnote)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    )

                    Button {
                        startTrip()
                    } label: {
                        PrimaryActionLabel(title: "Start Trip", systemImage: "play.fill")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.appAccent)
                    .disabled(selectedWaterbody == nil)
                    .accessibilityIdentifier("startTrip.button")
                    .listRowSeparator(.hidden)

                    if selectedWaterbody == nil {
                        Text("Select a waterbody to get started.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .listRowSeparator(.hidden)
                    }
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
        LogFeatureLogic.filteredSpots(spots: spots, selectedWaterbodyID: selectedWaterbodyID)
    }

    private func startTrip() {
        let snapshot = ConditionCaptureService.snapshot(
            waterbody: selectedWaterbody,
            spot: selectedSpot,
            location: locationRecorder.lastLocation,
            capturedAt: .now
        )

        let draft = LogFeatureLogic.startTripDraft(targetSpecies: targetSpecies, notes: tripNotes)
        let trip = Trip(
            waterbody: selectedWaterbody,
            spot: selectedSpot,
            conditionSnapshot: snapshot,
            targetSpecies: draft.targetSpecies,
            notes: draft.notes
        )

        modelContext.insert(snapshot)
        modelContext.insert(trip)
        try? modelContext.save()

        targetSpecies = ""
        tripNotes = ""
        showingOptionalDetails = LogFeatureLogic.startTripOptionalDetailsInitiallyExpanded
    }
}

// MARK: - Condition Preview Row

private struct ConditionPreviewRow: View {
    let preview: ConditionCapturePreview

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Label(preview.snapshot.statusLine, systemImage: preview.isLocationReady ? "checkmark.circle.fill" : "location.slash")
                .font(.subheadline)
                .foregroundStyle(preview.isLocationReady ? .appAccent : .secondary)

            if let placeSummary = preview.snapshot.placeSummary {
                Label(placeSummary, systemImage: "map")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let coordinateSummary = preview.snapshot.coordinateSummary {
                Label(coordinateSummary, systemImage: "location")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Text(preview.snapshot.weatherLine)
                .font(.footnote)
                .foregroundStyle(.tertiary)
        }
    }
}

// MARK: - Active Trip

private struct ActiveTripView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var trip: Trip
    let onTripEnded: ((Trip) -> Void)?

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
    @State private var showingSavedConfirmation = false
    @State private var showingEndConfirmation = false
    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var photoData: Data?
    @State private var editingCatchID: UUID?

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
        LogFeatureLogic.recentSpeciesSuggestions(
            targetSpeciesList: trip.targetSpeciesList,
            catches: allCatches
        )
    }

    private var recentLureSuggestions: [String] {
        LogFeatureLogic.recentLureSuggestions(catchesForSpot: catchesForSpot, allCatches: allCatches)
    }

    var body: some View {
        List {
            // Trip Status
            Section {
                ActiveTripStatusCard(
                    trip: trip,
                    catchCount: catchesForTrip.count,
                    elapsedText: elapsedText,
                    contextSummary: trip.conditionSnapshot?.displaySummary
                )
                .listRowInsets(EdgeInsets())
                .listRowBackground(Color.clear)
            }

            // Recall
            if let recallSummary, !recallSummary.cards.isEmpty {
                Section("Spot Recall") {
                    ForEach(recallSummary.cards.prefix(3), id: \.id) { card in
                        DeterministicInsightCardView(card: card)
                            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                    }
                }
            }

            // Quick Catch Form
            Section {
                TextField("Species (optional)", text: $species)
                    .textInputAutocapitalization(.words)
                    .submitLabel(.done)

                if !recentSpeciesSuggestions.isEmpty && species.isEmpty {
                    Text(
                        trip.targetSpeciesList.isEmpty
                            ? "Recent species appear here as quick picks."
                            : "Trip targets appear here as quick picks."
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)

                    SuggestionRow(label: "Species", values: recentSpeciesSuggestions) { value in
                        species = value
                    }
                }

                TextField("Lure or bait", text: $lureOrBait)
                    .textInputAutocapitalization(.words)

                if !recentLureSuggestions.isEmpty && lureOrBait.isEmpty {
                    SuggestionRow(label: "Lure", values: recentLureSuggestions) { value in
                        lureOrBait = value
                    }
                }

                DisclosureGroup("More details", isExpanded: $showingOptionalFields) {
                    TextField("Method", text: $method)
                        .textInputAutocapitalization(.words)
                    TextField("Weight (kg)", text: $weight)
                        .keyboardType(.decimalPad)
                    TextField("Length (cm)", text: $length)
                        .keyboardType(.decimalPad)
                    TextField("Note", text: $note, axis: .vertical)
                        .lineLimit(2...4)

                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        if let photoData {
                            HStack(spacing: Spacing.md) {
                                CatchPhotoThumbnailView(data: photoData)
                                VStack(alignment: .leading, spacing: Spacing.xs) {
                                    Text("Photo attached")
                                        .font(.footnote.weight(.semibold))
                                    Text("Optional only. Save still works without it.")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Button("Remove Photo") {
                                        self.photoData = nil
                                        selectedPhotoItem = nil
                                    }
                                    .font(.caption)
                                }
                            }
                        }

                        PhotosPicker(selection: $selectedPhotoItem, matching: .images) {
                            Label(photoData == nil ? "Choose from Library" : "Replace from Library", systemImage: "photo.on.rectangle")
                                .font(.footnote.weight(.medium))
                        }
                        .buttonStyle(.bordered)
                        .tint(.appAccent)
                        .accessibilityIdentifier("quickCatch.photoLibraryButton")
                    }
                }

                Button {
                    saveCatch()
                } label: {
                    PrimaryActionLabel(title: "Save Catch", systemImage: "checkmark.circle.fill")
                }
                .buttonStyle(.borderedProminent)
                .tint(.appAccent)
                .accessibilityIdentifier("quickCatch.saveButton")
                .listRowSeparator(.hidden)
                .sensoryFeedback(.success, trigger: showingSavedConfirmation)
            } header: {
                Text("Quick Catch")
            } footer: {
                Text("Time and place attach automatically. Photo is optional and currently comes from your library.")
            }

            // This Trip's Catches
            Section {
                if catchesForTrip.isEmpty {
                    SectionEmptyState(
                        icon: "fish",
                        title: "No catches yet",
                        subtitle: "Log your first catch above."
                    )
                } else {
                    ForEach(catchesForTrip, id: \.id) { catchRecord in
                        Button {
                            editingCatchID = catchRecord.id
                        } label: {
                            CatchHistoryRow(catchRecord: catchRecord, includeTimestamp: true)
                        }
                        .buttonStyle(.plain)
                    }
                }
            } header: {
                HStack {
                    Text("This Trip")
                    Spacer()
                    Text("\(catchesForTrip.count)")
                        .font(.footnote.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            } footer: {
                if !catchesForTrip.isEmpty {
                    Text("Tap a catch to edit or delete it before ending the trip.")
                }
            }

            // End Trip
            Section {
                Button(role: .destructive) {
                    showingEndConfirmation = true
                } label: {
                    Label("End Trip", systemImage: "stop.circle")
                        .frame(maxWidth: .infinity)
                }
                .accessibilityIdentifier("trip.endButton")
            }
        }
        .onAppear {
            primeDefaultsIfNeeded()
        }
        .alert("End this trip?", isPresented: $showingEndConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("End Trip", role: .destructive) {
                endTrip()
            }
        } message: {
            if catchesForTrip.isEmpty {
                Text("This trip will be marked as skunked.")
            } else {
                Text("This trip has \(catchesForTrip.count) \(catchesForTrip.count == 1 ? "catch" : "catches") logged.")
            }
        }
        .onChange(of: selectedPhotoItem) { _, newValue in
            guard let newValue else { return }
            Task {
                photoData = try? await newValue.loadTransferable(type: Data.self)
            }
        }
        .sheet(
            isPresented: Binding(
                get: { editingCatchID != nil },
                set: { isPresented in
                    if !isPresented {
                        editingCatchID = nil
                    }
                }
            )
        ) {
            if let editingCatchID,
               let catchRecord = catchesForTrip.first(where: { $0.id == editingCatchID }) {
                CatchEditorView(trip: trip, catchRecord: catchRecord)
            } else {
                ContentUnavailableView("Catch not found", systemImage: "exclamationmark.triangle")
            }
        }
    }

    // MARK: - Actions

    private func saveCatch() {
        let draft = TripEditingLogic.catchDraft(
            species: species,
            lureOrBait: lureOrBait,
            method: method,
            weight: weight,
            length: length,
            note: note,
            photoData: photoData
        )
        let catchRecord = CatchRecord(
            species: draft.species,
            trip: trip,
            caughtAt: .now,
            lureOrBait: draft.lureOrBait,
            method: draft.method,
            weightKg: draft.weightKg,
            lengthCm: draft.lengthCm,
            note: draft.note,
            photoReference: draft.photoReference,
            photoData: photoData,
            photoContentType: draft.photoContentType
        )

        modelContext.insert(catchRecord)
        try? PersonalBestService.refresh(with: catchRecord, in: modelContext)
        try? modelContext.save()

        let resetState = LogFeatureLogic.resetQuickCatchStateAfterSave(
            lureOrBait: lureOrBait,
            method: method
        )
        species = resetState.species
        lureOrBait = resetState.lureOrBait
        method = resetState.method
        weight = resetState.weight
        length = resetState.length
        note = resetState.note
        photoData = resetState.photoData
        selectedPhotoItem = nil
        showingOptionalFields = resetState.showingOptionalFields
        showingSavedConfirmation.toggle()
    }

    private func endTrip() {
        trip.endAt = .now
        trip.outcomeRawValue = LogFeatureLogic.endTripOutcome(catchCount: catchesForTrip.count).rawValue
        try? modelContext.save()
        onTripEnded?(trip)
    }

    private var elapsedText: String {
        AppFormatters.duration.string(from: Date().timeIntervalSince(trip.startAt)) ?? "Now"
    }

    private func primeDefaultsIfNeeded() {
        let defaults = LogFeatureLogic.primeDefaultsIfNeeded(
            didPrimeDefaults: didPrimeDefaults,
            lureOrBait: lureOrBait,
            method: method,
            catchesForSpot: catchesForSpot,
            allCatches: allCatches
        )
        didPrimeDefaults = defaults.didPrimeDefaults
        lureOrBait = defaults.lureOrBait
        method = defaults.method
    }
}

// MARK: - Active Trip Status Card

private struct ActiveTripStatusCard: View {
    let trip: Trip
    let catchCount: Int
    let elapsedText: String
    let contextSummary: String?

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            HStack {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    HStack(spacing: Spacing.sm) {
                        AppBadge(text: "Live")
                        Text(elapsedText)
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                    Text(trip.title)
                        .font(.headline)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: Spacing.xxs) {
                    Text("\(catchCount)")
                        .font(.title.weight(.bold).monospacedDigit())
                        .foregroundStyle(.appAccent)
                    Text(catchCount == 1 ? "catch" : "catches")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            HStack(spacing: Spacing.lg) {
                if let spot = trip.spot?.title {
                    Label(spot, systemImage: "mappin")
                }
            }
            .font(.footnote)
            .foregroundStyle(.secondary)

            if let contextSummary {
                Text(contextSummary)
                    .font(.footnote)
                    .foregroundStyle(.tertiary)
            }
        }
        .appCard(prominent: true)
    }
}

private struct PrimaryActionLabel: View {
    let title: String
    let systemImage: String

    var body: some View {
        HStack(spacing: Spacing.sm) {
            Image(systemName: systemImage)
            Text(title)
        }
        .font(.headline)
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.xs)
    }
}

// MARK: - Catch History Row

struct CatchHistoryRow: View {
    let catchRecord: CatchRecord
    var includeTimestamp: Bool = false

    var body: some View {
        HStack(alignment: .top, spacing: Spacing.md) {
            if let photoData = catchRecord.photoData {
                CatchPhotoThumbnailView(data: photoData)
            }

            VStack(alignment: .leading, spacing: Spacing.xs) {
                HStack {
                    Text(catchRecord.speciesDisplayName)
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    if includeTimestamp {
                        Text(AppFormatters.shortTime.string(from: catchRecord.caughtAt))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                let secondaryParts = [catchRecord.lureOrBait, catchRecord.method]
                    .filter { !$0.isEmpty }
                if !secondaryParts.isEmpty {
                    Text(secondaryParts.joined(separator: " · "))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                let metricParts: [String] = [
                    catchRecord.weightKg.map { "\($0.formatted()) kg" },
                    catchRecord.lengthCm.map { "\($0.formatted()) cm" },
                ].compactMap { $0 }

                if !metricParts.isEmpty {
                    Text(metricParts.joined(separator: " · "))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                if !catchRecord.note.isEmpty {
                    Text(catchRecord.note)
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                        .lineLimit(2)
                }
            }
        }
        .padding(.vertical, Spacing.xs)
    }
}
