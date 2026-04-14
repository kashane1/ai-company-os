import PhotosUI
import SwiftData
import SwiftUI

struct ActiveTripView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var trip: Trip
    let onTripEnded: (Trip) -> Void

    @Query(sort: \Trip.startAt, order: .reverse) private var allTrips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var allCatches: [CatchRecord]
    @Query(sort: \Spot.createdAt) private var spots: [Spot]

    @State private var species = ""
    @State private var lureOrBait = ""
    @State private var disposition: CatchDisposition = .notRecorded
    @State private var method = ""
    @State private var gear = ""
    @State private var weight = ""
    @State private var length = ""
    @State private var waterDepth = ""
    @State private var note = ""
    @State private var showingOptionalFields = false
    @State private var didPrimeDefaults = false
    @State private var showingSavedConfirmation = false
    @State private var showingSavedBanner = false
    @State private var showingEndReview = false
    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var photos: [CatchPhotoDraft] = []
    @State private var photoLocationSuggestion: CatchPhotoLocationSuggestion?
    @State private var pendingMatchedSpotID: UUID?
    @State private var showingCamera = false
    @State private var editingCatchID: UUID?
    @State private var persistenceErrorMessage: String?
    @State private var endedTripSummary: EndedTripSummary?
    @AppStorage(CatchOptionalField.appStorageKey) private var storedVisibleFields = CatchOptionalField.storedValue(for: CatchOptionalField.defaultFields)
    @AppStorage(QuickCatchEntryMode.appStorageKey) private var storedQuickCatchEntryMode = QuickCatchEntryMode.full.rawValue
    @FocusState private var focusedField: QuickCatchField?

    private var catchesForTrip: [CatchRecord] {
        allCatches.filter { $0.trip?.id == trip.id }
    }

    private var catchesForSpot: [CatchRecord] {
        guard let spotID = trip.spot?.id else { return [] }
        return allCatches.filter { $0.trip?.spot?.id == spotID }
    }

    private var catchesForWaterbody: [CatchRecord] {
        // Returns [] when trip.waterbody is nil; the suggestion ranker in
        // LogFeatureLogic.historySuggestions falls through to spot-level and
        // global tiers. See ADR 2026-04-13-waterbody-is-never-a-gate.
        guard let waterbodyID = trip.waterbody?.id else { return [] }
        return allCatches.filter { $0.trip?.waterbody?.id == waterbodyID }
    }

    private var recallSummary: SpotRecallSummary? {
        guard let spot = trip.spot else { return nil }
        return SpotRecallSummary.build(for: spot, trips: allTrips, catches: allCatches)
    }

    private var recentSpeciesSuggestions: [String] {
        LogFeatureLogic.historySuggestions(
            query: species,
            prioritizedValues: trip.targetSpeciesList,
            spotValues: catchesForSpot.map(\.species),
            waterbodyValues: catchesForWaterbody.map(\.species),
            globalValues: allCatches.map(\.species)
        )
    }

    private var recentLureSuggestions: [String] {
        LogFeatureLogic.historySuggestions(
            query: lureOrBait,
            spotValues: catchesForSpot.map(\.lureOrBait),
            waterbodyValues: catchesForWaterbody.map(\.lureOrBait),
            globalValues: allCatches.map(\.lureOrBait)
        )
    }

    private var recentGearSuggestions: [String] {
        LogFeatureLogic.historySuggestions(
            query: gear,
            spotValues: catchesForSpot.map(\.gear),
            waterbodyValues: catchesForWaterbody.map(\.gear),
            globalValues: allCatches.map(\.gear)
        )
    }

    private var visibleFields: Set<CatchOptionalField> {
        CatchOptionalField.fields(from: storedVisibleFields)
    }

    private var quickCatchEntryMode: QuickCatchEntryMode {
        QuickCatchEntryMode(rawValue: storedQuickCatchEntryMode) ?? .full
    }

    private var tripSpeciesTallies: [(species: String, count: Int)] {
        Dictionary(grouping: catchesForTrip, by: \.speciesDisplayName)
            .map { ($0.key, $0.value.count) }
            .sorted {
                if $0.count != $1.count {
                    return $0.count > $1.count
                }
                return $0.species.localizedCaseInsensitiveCompare($1.species) == .orderedAscending
            }
    }

    private var quickCatchContext: QuickCatchContextSummary {
        LogFeatureLogic.quickCatchContextSummary(trip: trip)
    }

    private var canUseCamera: Bool {
        UIImagePickerController.isSourceTypeAvailable(.camera)
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

                Picker("Entry Mode", selection: $storedQuickCatchEntryMode) {
                    ForEach(QuickCatchEntryMode.allCases) { mode in
                        Text(mode.label).tag(mode.rawValue)
                    }
                }
                .pickerStyle(.segmented)

                TextField("Species", text: $species)
                    .textInputAutocapitalization(.words)
                    .submitLabel(.done)
                    .focused($focusedField, equals: .species)
                    .onSubmit {
                        if !species.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                            saveCatch(action: .save, tallyOnly: quickCatchEntryMode == .tally)
                        }
                    }
                    .characterLimit(CharacterLimits.catchSpecies, text: $species)

                if !recentSpeciesSuggestions.isEmpty {
                    Text(
                        trip.targetSpeciesList.isEmpty
                            ? (species.isEmpty ? "Recent species appear here as quick picks." : "Matching species from your log.")
                            : (species.isEmpty ? "Trip targets appear here as quick picks." : "Matching species from this trip and your log.")
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)

                    SuggestionRow(label: "Species", values: recentSpeciesSuggestions) { value in
                        species = value
                    }
                }

                if quickCatchEntryMode == .full {
                    TextField("Lure or bait", text: $lureOrBait)
                        .textInputAutocapitalization(.words)
                        .focused($focusedField, equals: .lureOrBait)
                        .characterLimit(CharacterLimits.catchLureOrBait, text: $lureOrBait)

                    if !recentLureSuggestions.isEmpty {
                        SuggestionRow(label: "Lure", values: recentLureSuggestions) { value in
                            lureOrBait = value
                        }
                    }
                    DisclosureGroup("More details", isExpanded: $showingOptionalFields) {
                        CatchFieldVisibilityEditor(storedVisibleFields: $storedVisibleFields)

                        if visibleFields.contains(.disposition) {
                            Picker("Disposition", selection: $disposition) {
                                ForEach(CatchDisposition.allCases) { option in
                                    Text(option.label).tag(option)
                                }
                            }
                        }

                        if visibleFields.contains(.method) {
                            TextField("Method", text: $method)
                                .textInputAutocapitalization(.words)
                                .focused($focusedField, equals: .method)
                                .characterLimit(CharacterLimits.catchMethod, text: $method)
                        }

                        if visibleFields.contains(.gear) {
                            TextField("Gear", text: $gear)
                                .textInputAutocapitalization(.words)
                                .focused($focusedField, equals: .gear)
                                .characterLimit(CharacterLimits.catchGear, text: $gear)
                            if !recentGearSuggestions.isEmpty {
                                SuggestionRow(label: "Gear", values: recentGearSuggestions) { value in
                                    gear = value
                                }
                            }
                        }

                        if visibleFields.contains(.weight) {
                            TextField("Weight (kg)", text: $weight)
                                .keyboardType(.decimalPad)
                                .focused($focusedField, equals: .weight)
                        }
                        if visibleFields.contains(.length) {
                            TextField("Length (cm)", text: $length)
                                .keyboardType(.decimalPad)
                                .focused($focusedField, equals: .length)
                        }
                        if visibleFields.contains(.waterDepth) {
                            TextField("Water depth (m)", text: $waterDepth)
                                .keyboardType(.decimalPad)
                                .focused($focusedField, equals: .waterDepth)
                        }
                        if visibleFields.contains(.note) {
                            TextField("Note", text: $note, axis: .vertical)
                                .lineLimit(2...4)
                                .focused($focusedField, equals: .note)
                                .characterLimit(CharacterLimits.catchNote, text: $note)
                        }

                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            if visibleFields.contains(.photo), !photos.isEmpty {
                                CatchPhotoDraftStripView(photos: photos) { id in
                                    photos.removeAll { $0.id == id }
                                    if photos.isEmpty {
                                        photoLocationSuggestion = nil
                                        pendingMatchedSpotID = nil
                                        selectedPhotoItem = nil
                                    }
                                }
                            }

                            if visibleFields.contains(.photo) {
                                PhotosPicker(selection: $selectedPhotoItem, matching: .images) {
                                    Label(photos.isEmpty ? "Add from Library" : "Add Another from Library", systemImage: "photo.on.rectangle")
                                        .font(.footnote.weight(.medium))
                                }
                                .buttonStyle(.bordered)
                                .tint(.appAccent)
                                .disabled(photos.count >= 4)
                                .accessibilityIdentifier("quickCatch.photoLibraryButton")

                                Button {
                                    showingCamera = true
                                } label: {
                                    Label("Take Photo", systemImage: "camera")
                                        .font(.footnote.weight(.medium))
                                }
                                .buttonStyle(.bordered)
                                .disabled(!canUseCamera || photos.count >= 4)

                                Text("Up to 4 photos. If photo access is unavailable, you can still save the catch.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)

                                if let photoLocationSuggestion {
                                    PhotoSpotSuggestionCard(
                                        suggestion: photoLocationSuggestion,
                                        currentSpotID: trip.spot?.id,
                                        pendingSpotID: pendingMatchedSpotID
                                    ) { spotID in
                                        pendingMatchedSpotID = spotID
                                    }
                                }
                            } else {
                                Text("Photos are hidden right now. Turn them back on in Visible Fields when you want richer catch detail.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                } else {
                    if !tripSpeciesTallies.isEmpty {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            Text("Trip tally")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)
                            ForEach(Array(tripSpeciesTallies.prefix(4).enumerated()), id: \.offset) { _, tally in
                                HStack {
                                    Text(tally.species)
                                    Spacer()
                                    Text("\(tally.count)")
                                        .font(.caption.monospacedDigit())
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                        .padding(.vertical, Spacing.xs)
                    }
                }

                if showingSavedBanner {
                    SavedConfirmationBanner(text: "Catch saved!")
                        .frame(maxWidth: .infinity)
                        .listRowSeparator(.hidden)
                }

                Button {
                    saveCatch(action: .save, tallyOnly: quickCatchEntryMode == .tally)
                } label: {
                    PrimaryActionLabel(title: quickCatchEntryMode == .tally ? "Add To Tally" : "Save", systemImage: quickCatchEntryMode == .tally ? "plus.circle.fill" : "checkmark.circle.fill")
                }
                .buttonStyle(.borderedProminent)
                .tint(.appAccent)
                .accessibilityIdentifier("quickCatch.saveButton")
                .listRowSeparator(.hidden)
                .sensoryFeedback(.success, trigger: showingSavedConfirmation)

                if quickCatchEntryMode == .full {
                    Button {
                        saveCatch(action: .saveAndAddAnother, tallyOnly: false)
                    } label: {
                        PrimaryActionLabel(title: "Save & Add Another", systemImage: "plus.circle.fill")
                    }
                    .buttonStyle(.bordered)
                    .tint(.appAccent)
                    .listRowSeparator(.hidden)
                }
            } header: {
                Text("Quick Catch")
            } footer: {
                Text(quickCatchEntryMode == .tally ? "Tally mode keeps logging species-first for busy sessions. Each tap still creates a real catch record in this trip." : "Time and spot attach automatically. Optional fields stay collapsed so a basic catch can be logged fast, even offline.")
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
                if let data = try? await newValue.loadTransferable(type: Data.self) {
                    appendPhoto(data: data)
                }
                selectedPhotoItem = nil
            }
        }
        .sheet(isPresented: $showingCamera) {
            CameraCaptureView { data in
                appendPhoto(data: data)
                showingCamera = false
            } onCancel: {
                showingCamera = false
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
        .sheet(item: $endedTripSummary) { summary in
            TripEndedSummaryView(trip: summary.trip) {
                endedTripSummary = nil
            } viewHistory: {
                let trip = summary.trip
                endedTripSummary = nil
                onTripEnded(trip)
            }
        }
    }

    // MARK: - Actions

    private func saveCatch(action: QuickCatchSaveAction, tallyOnly: Bool) {
        let draft = TripEditingLogic.catchDraft(
            species: species,
            lureOrBait: tallyOnly ? "" : lureOrBait,
            method: tallyOnly ? "" : method,
            gear: tallyOnly ? "" : gear,
            weight: tallyOnly ? "" : weight,
            length: tallyOnly ? "" : length,
            waterDepth: tallyOnly ? "" : waterDepth,
            note: tallyOnly ? "" : note,
            disposition: tallyOnly ? .notRecorded : disposition,
            photoData: tallyOnly ? nil : photos.first?.data
        )
        let catchRecord = CatchRecord(
            species: draft.species,
            trip: trip,
            caughtAt: .now,
            lureOrBait: draft.lureOrBait,
            method: draft.method,
            gear: draft.gear,
            weightKg: draft.weightKg,
            lengthCm: draft.lengthCm,
            waterDepthM: draft.waterDepthM,
            note: draft.note,
            disposition: draft.disposition,
            photoReference: draft.photoReference,
            photoData: tallyOnly ? nil : photos.first?.data,
            photoContentType: draft.photoContentType
        )

        modelContext.insert(catchRecord)
        PersistenceWriteCoordinator.perform(
            commit: {
                if let pendingMatchedSpotID,
                   let matchedSpot = spots.first(where: { $0.id == pendingMatchedSpotID }) {
                    TripEditingLogic.applyMatchedSpot(matchedSpot, to: trip)
                }
                CatchPhotoMigrationService.sync(record: catchRecord, drafts: photos, in: modelContext)
                try PersonalBestService.refresh(with: catchRecord, in: modelContext)
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                let resetState = LogFeatureLogic.resetQuickCatchStateAfterSave(
                    lureOrBait: lureOrBait,
                    method: method,
                    gear: gear
                )
                species = resetState.species
                lureOrBait = resetState.lureOrBait
                disposition = resetState.disposition
                method = resetState.method
                gear = resetState.gear
                weight = resetState.weight
                length = resetState.length
                waterDepth = resetState.waterDepth
                note = resetState.note
                photos = []
                photoLocationSuggestion = nil
                pendingMatchedSpotID = nil
                selectedPhotoItem = nil
                showingOptionalFields = resetState.showingOptionalFields
                if action == .saveAndAddAnother || tallyOnly {
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

    private func appendPhoto(data: Data) {
        guard photos.count < 4 else { return }
        photos.append(CatchPhotoDraft(data: data))
        updatePhotoLocationSuggestion(from: data)
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
                endedTripSummary = EndedTripSummary(trip: trip)
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
            gear: gear,
            catchesForSpot: catchesForSpot,
            allCatches: allCatches
        )
        didPrimeDefaults = defaults.didPrimeDefaults
        lureOrBait = defaults.lureOrBait
        method = defaults.method
        gear = defaults.gear
    }

    private func updatePhotoLocationSuggestion(from data: Data) {
        guard let metadata = CatchPhotoMetadataService.metadata(from: data),
              let coordinate = metadata.coordinate else {
            photoLocationSuggestion = nil
            pendingMatchedSpotID = nil
            return
        }

        photoLocationSuggestion = CatchPhotoLocationSuggestion(
            coordinate: coordinate,
            matches: CatchPhotoMetadataService.nearbySpotMatches(for: coordinate, spots: spots)
        )
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

// MARK: - End Trip Review

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

// MARK: - Trip Ended Summary

struct TripEndedSummaryView: View {
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
                initialCoordinate: trip.resolvedCoordinate
            )
        }
        .presentationDetents([.medium, .large])
    }
}

struct EndedTripSummary: Identifiable {
    let trip: Trip

    var id: UUID { trip.id }
}
