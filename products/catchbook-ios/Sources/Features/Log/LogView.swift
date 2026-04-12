import PhotosUI
import SwiftData
import SwiftUI

struct LogView: View {
    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]
    @Query(sort: \Spot.createdAt) private var spots: [Spot]
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @State private var endedTripSummary: EndedTripSummary?

    var onTripEnded: ((Trip) -> Void)?

    private var activeTrip: Trip? {
        trips.first(where: \.isActive)
    }

    var body: some View {
        NavigationStack {
            Group {
                if let activeTrip {
                    ActiveTripView(trip: activeTrip) { trip in
                        endedTripSummary = EndedTripSummary(trip: trip)
                    }
                } else {
                    StartTripView(waterbodies: waterbodies, spots: spots)
                }
            }
            .navigationTitle("Log")
        }
        .sheet(item: $endedTripSummary) { summary in
            TripEndedSummaryView(trip: summary.trip) {
                endedTripSummary = nil
            } viewHistory: {
                let trip = summary.trip
                endedTripSummary = nil
                onTripEnded?(trip)
            }
        }
    }
}

private struct EndedTripSummary: Identifiable {
    let trip: Trip

    var id: UUID { trip.id }
}

// MARK: - Start Trip

struct StartTripView: View {
    @Environment(\.modelContext) private var modelContext

    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]

    @StateObject private var locationRecorder = LocationRecorder()
    @State private var selectedWaterbodyID: UUID?
    @State private var selectedSpotID: UUID?
    @State private var targetSpecies = ""
    @State private var tripNotes = ""
    @State private var showingOptionalDetails = LogFeatureLogic.startTripOptionalDetailsInitiallyExpanded
    @State private var showingWaterbodyForm = false
    @State private var showingSpotForm = false
    @State private var persistenceErrorMessage: String?
    @FocusState private var isTextInputFocused: Bool

    let waterbodies: [Waterbody]
    let spots: [Spot]

    private var conditionPreview: ConditionCapturePreview {
        ConditionCaptureService.preview(
            waterbody: selectedWaterbody,
            spot: selectedSpot,
            location: locationRecorder.lastLocation
        )
    }

    private var lastTimeHereCard: HomeReplayCard? {
        Self.lastTimeHereCard(
            selectedSpotID: selectedSpotID,
            trips: trips,
            catches: catches
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

                    if let lastTimeHereCard {
                        LastTimeHereCard(card: lastTimeHereCard)
                            .listRowInsets(EdgeInsets(top: 4, leading: 0, bottom: 4, trailing: 0))
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

                Section {
                    ConditionPreviewRow(preview: conditionPreview)
                } header: {
                    Text("Conditions")
                } footer: {
                    Text("Location and weather can degrade gracefully. Trip start still works offline and your spots stay yours.")
                }

                Section {
                    DisclosureGroup(
                        isExpanded: $showingOptionalDetails,
                        content: {
                            TextField("Target species, separated by commas", text: $targetSpecies)
                                .textInputAutocapitalization(.words)
                                .focused($isTextInputFocused)
                                .accessibilityIdentifier("startTrip.targetSpeciesField")
                            Text("Optional. Enter one or more targets. We turn them into quick-catch suggestions.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                            TextField("Trip notes", text: $tripNotes, axis: .vertical)
                                .lineLimit(2...4)
                                .focused($isTextInputFocused)
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
        .scrollDismissesKeyboard(.interactively)
        .toolbar {
            KeyboardDoneToolbar { isTextInputFocused = false }
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
        .persistenceFailureAlert(message: $persistenceErrorMessage)
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

    static func lastTimeHereCard(
        selectedSpotID: UUID?,
        trips: [Trip],
        catches: [CatchRecord],
        calendar: Calendar = .current
    ) -> HomeReplayCard? {
        guard let selectedSpotID else { return nil }
        guard let trip = trips.first(where: { !$0.isActive && $0.spot?.id == selectedSpotID }) else {
            return nil
        }

        let tripCatches = catches.filter { $0.trip?.id == trip.id }
        return HomeDashboardLogic.lastTimeHereCard(
            trip: trip,
            catches: tripCatches,
            calendar: calendar
        )
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
        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                targetSpecies = ""
                tripNotes = ""
                showingOptionalDetails = LogFeatureLogic.startTripOptionalDetailsInitiallyExpanded

                // Enrich the snapshot with live weather in the background.
                // If it fails (offline, etc.) the snapshot keeps its nil weather fields
                // and the UI shows "Weather data unavailable" gracefully.
                let location = locationRecorder.lastLocation
                Task {
                    await ConditionCaptureService.enrichWithWeather(snapshot, location: location)
                    try? modelContext.save()
                }
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
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

            // Merge place + coordinate into one line: "Lake Smith · 37.78, -122.42"
            // Falls back to whichever is present if only one is available.
            if let mergedLocationLine = mergedLocationLine(for: preview.snapshot) {
                Label(mergedLocationLine, systemImage: "map")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Text(preview.snapshot.weatherLine)
                .font(.footnote)
                .foregroundStyle(.tertiary)

            if preview.snapshot.weatherSummary != nil {
                WeatherAttributionView()
            }

            if !preview.isLocationReady {
                Text("Location unavailable right now. We'll fall back to your saved water or spot when possible.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if preview.snapshot.weatherSummary == nil {
                Text("Weather loads automatically when your trip starts. Core logging always works offline.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func mergedLocationLine(for snapshot: ConditionSnapshot) -> String? {
        snapshot.locationSummaryLine
    }
}

// MARK: - Active Trip

private struct ActiveTripView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var trip: Trip
    let onTripEnded: (Trip) -> Void

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
    @State private var showingSavedBanner = false
    @State private var showingEndReview = false
    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var photoData: Data?
    @State private var editingCatchID: UUID?
    @State private var persistenceErrorMessage: String?
    @FocusState private var focusedField: QuickCatchField?

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

    private var quickCatchContext: QuickCatchContextSummary {
        LogFeatureLogic.quickCatchContextSummary(trip: trip)
    }

    var body: some View {
        List {
            // Trip Status
            Section {
                ActiveTripStatusCard(
                    trip: trip,
                    catchCount: catchesForTrip.count,
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
                VStack(alignment: .leading, spacing: Spacing.sm) {
                    HStack(spacing: Spacing.md) {
                        StatCapsule(value: quickCatchContext.timeText, label: "Time", icon: "clock")
                        StatCapsule(value: quickCatchContext.spotText, label: "Spot", icon: "mappin")
                    }
                    Text(quickCatchContext.privacyText)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, Spacing.xxs)

                TextField("Species", text: $species)
                    .textInputAutocapitalization(.words)
                    .submitLabel(.done)
                    .focused($focusedField, equals: .species)
                    .onSubmit {
                        if !species.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                            saveCatch(action: .save)
                        }
                    }

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
                    .focused($focusedField, equals: .lureOrBait)

                if !recentLureSuggestions.isEmpty && lureOrBait.isEmpty {
                    SuggestionRow(label: "Lure", values: recentLureSuggestions) { value in
                        lureOrBait = value
                    }
                }

                DisclosureGroup("More details", isExpanded: $showingOptionalFields) {
                    TextField("Method", text: $method)
                        .textInputAutocapitalization(.words)
                        .focused($focusedField, equals: .method)
                    TextField("Weight (kg)", text: $weight)
                        .keyboardType(.decimalPad)
                        .focused($focusedField, equals: .weight)
                    TextField("Length (cm)", text: $length)
                        .keyboardType(.decimalPad)
                        .focused($focusedField, equals: .length)
                    TextField("Note", text: $note, axis: .vertical)
                        .lineLimit(2...4)
                        .focused($focusedField, equals: .note)

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
                                    Button(role: .destructive) {
                                        self.photoData = nil
                                        selectedPhotoItem = nil
                                    } label: {
                                        Label("Remove Photo", systemImage: "trash")
                                    }
                                    .buttonStyle(.bordered)
                                    .controlSize(.small)
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

                        Text("If photo access is unavailable, you can still save the catch.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                if showingSavedBanner {
                    SavedConfirmationBanner(text: "Catch saved!")
                        .frame(maxWidth: .infinity)
                        .listRowSeparator(.hidden)
                }

                Button {
                    saveCatch(action: .save)
                } label: {
                    PrimaryActionLabel(title: "Save", systemImage: "checkmark.circle.fill")
                }
                .buttonStyle(.borderedProminent)
                .tint(.appAccent)
                .accessibilityIdentifier("quickCatch.saveButton")
                .listRowSeparator(.hidden)
                .sensoryFeedback(.success, trigger: showingSavedConfirmation)

                Button {
                    saveCatch(action: .saveAndAddAnother)
                } label: {
                    PrimaryActionLabel(title: "Save & Add Another", systemImage: "plus.circle.fill")
                }
                .buttonStyle(.bordered)
                .tint(.appAccent)
                .listRowSeparator(.hidden)
            } header: {
                Text("Quick Catch")
            } footer: {
                Text("Time and spot attach automatically. Optional fields stay collapsed so a basic catch can be logged fast, even offline.")
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
                Button {
                    showingEndReview = true
                } label: {
                    Label("Review & End Trip", systemImage: "stop.circle")
                        .frame(maxWidth: .infinity)
                }
                .accessibilityIdentifier("trip.endButton")
            }
        }
        .scrollDismissesKeyboard(.interactively)
        .toolbar {
            KeyboardDoneToolbar { focusedField = nil }
        }
        .onAppear {
            primeDefaultsIfNeeded()
            focusedField = .species
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
        .sheet(isPresented: $showingEndReview) {
            EndTripReviewView(trip: trip, catches: catchesForTrip) {
                showingEndReview = false
                endTrip()
            }
        }
        .persistenceFailureAlert(message: $persistenceErrorMessage)
    }

    // MARK: - Actions

    private func saveCatch(action: QuickCatchSaveAction) {
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
        PersistenceWriteCoordinator.perform(
            commit: {
                try PersonalBestService.refresh(with: catchRecord, in: modelContext)
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
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
                if action == .saveAndAddAnother {
                    focusedField = .species
                } else {
                    focusedField = nil
                }
                showingSavedConfirmation.toggle()
                withAnimation(.easeOut(duration: 0.3)) {
                    showingSavedBanner = true
                }
                Task {
                    try? await Task.sleep(for: .seconds(2))
                    withAnimation(.easeOut(duration: 0.3)) {
                        showingSavedBanner = false
                    }
                }
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }

    private func endTrip() {
        trip.endAt = .now
        trip.outcomeRawValue = LogFeatureLogic.endTripOutcome(catchCount: catchesForTrip.count).rawValue
        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                onTripEnded(trip)
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
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
    let contextSummary: String?

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            HStack {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    HStack(spacing: Spacing.sm) {
                        AppBadge(text: "Live")
                        TimelineView(.periodic(from: trip.startAt, by: 60)) { context in
                            Text(HomeDashboardLogic.elapsedText(startAt: trip.startAt, now: context.date))
                                .font(.caption.monospacedDigit())
                                .foregroundStyle(.secondary)
                        }
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

            if let spot = trip.spot?.title {
                Label(spot, systemImage: "mappin")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let contextSummary {
                Text(contextSummary)
                    .font(.footnote)
                    .foregroundStyle(.tertiary)
            }
        }
        .appCard(prominent: true)
    }
}

private struct EndTripReviewView: View {
    @Environment(\.dismiss) private var dismiss

    let trip: Trip
    let catches: [CatchRecord]
    let onConfirm: () -> Void

    private var summaryCards: [TripSummaryCardItem] {
        LogFeatureLogic.tripSummaryCards(trip: trip, catches: catches)
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    if catches.isEmpty {
                        SectionEmptyState(
                            icon: "moon.zzz",
                            title: "No catches logged this trip",
                            subtitle: "You can still save the trip. Skunked days stay part of your private memory."
                        )
                    } else {
                        Text("Wrap up this trip with a quick factual recap before it moves into history.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }

                Section("Trip recap") {
                    ForEach(summaryCards) { card in
                        VStack(alignment: .leading, spacing: Spacing.xxs) {
                            Text(card.title)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)
                            Text(card.value)
                                .font(.body.weight(.medium))
                            if let subtitle = card.subtitle {
                                Text(subtitle)
                                    .font(.caption)
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .padding(.vertical, Spacing.xxs)
                    }
                }

                Section {
                    Button(role: .destructive) {
                        dismiss()
                        onConfirm()
                    } label: {
                        PrimaryActionLabel(title: "End Trip", systemImage: "stop.fill")
                    }
                }
            }
            .navigationTitle("End Trip")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Keep Logging") {
                        dismiss()
                    }
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}

private struct TripEndedSummaryView: View {
    let trip: Trip
    let onDone: () -> Void
    let viewHistory: () -> Void

    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var allCatches: [CatchRecord]
    @State private var showingSpotForm = false

    private var catches: [CatchRecord] {
        allCatches.filter { $0.trip?.id == trip.id }
    }

    private var summaryCards: [TripSummaryCardItem] {
        LogFeatureLogic.tripSummaryCards(trip: trip, catches: catches)
    }

    private var shouldOfferCreateSpot: Bool {
        LogFeatureLogic.shouldOfferCreateSpot(from: trip)
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        AppBadge(
                            text: trip.outcome == .skunked ? "Saved privately" : "Trip saved",
                            color: trip.outcome == .skunked ? .secondary : .appAccent
                        )
                        Text(trip.outcome == .skunked ? "That trip is part of the memory too." : "Trip saved to your private history.")
                            .font(.headline)
                        Text("Your spots stay yours. Everything here is drawn from your own logbook.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, Spacing.xs)
                }

                Section("Trip summary") {
                    ForEach(summaryCards) { card in
                        VStack(alignment: .leading, spacing: Spacing.xxs) {
                            Text(card.title)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)
                            Text(card.value)
                                .font(.body.weight(.medium))
                            if let subtitle = card.subtitle {
                                Text(subtitle)
                                    .font(.caption)
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .padding(.vertical, Spacing.xxs)
                    }
                }

                if shouldOfferCreateSpot {
                    Section {
                        Button {
                            showingSpotForm = true
                        } label: {
                            PrimaryActionLabel(title: "Create Spot from This Trip", systemImage: "mappin.badge.plus")
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.appAccent)

                        Text(LogFeatureLogic.createSpotPrompt(for: trip))
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    } footer: {
                        Text("Catchbook will prefill the saved pin from this trip before you fine-tune it.")
                    }
                }

                Section {
                    Button {
                        viewHistory()
                    } label: {
                        PrimaryActionLabel(title: "View in Trips", systemImage: "clock.arrow.circlepath")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.appAccent)

                    Button("Done") {
                        onDone()
                    }
                    .buttonStyle(.bordered)
                }
            }
            .navigationTitle("Trip Summary")
            .navigationBarTitleDisplayMode(.inline)
        }
        .sheet(isPresented: $showingSpotForm) {
            NewSpotForm(
                preselectedWaterbodyID: trip.waterbody?.id,
                initialCoordinate: trip.resolvedCoordinate
            )
        }
        .presentationDetents([.medium, .large])
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
