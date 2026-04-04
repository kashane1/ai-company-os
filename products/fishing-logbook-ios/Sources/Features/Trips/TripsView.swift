import PhotosUI
import SwiftData
import SwiftUI
import UIKit

struct TripsView: View {
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]
    @Binding private var selectedTripID: UUID?
    @State private var path = NavigationPath()
    @State private var selectedWaterbodyID: UUID?
    @State private var speciesQuery = ""
    @State private var dateFilter: TripDateFilter = .all
    @State private var seasonFilter: TripSeasonFilter = .all
    @State private var selectedLure: String?

    init(selectedTripID: Binding<UUID?> = .constant(nil)) {
        _selectedTripID = selectedTripID
    }

    private var availableWaterbodies: [Waterbody] {
        TripHistoryLogic.availableWaterbodies(waterbodies: waterbodies, trips: trips)
    }

    private var filteredTrips: [Trip] {
        TripHistoryLogic.filteredTrips(
            trips: trips,
            catches: catches,
            selectedWaterbodyID: selectedWaterbodyID,
            speciesQuery: speciesQuery,
            dateFilter: dateFilter,
            seasonFilter: seasonFilter,
            selectedLure: selectedLure
        )
    }

    private var availableLures: [String] {
        TripHistoryLogic.availableLures(
            trips: trips,
            catches: catches,
            selectedWaterbodyID: selectedWaterbodyID,
            speciesQuery: speciesQuery,
            dateFilter: dateFilter,
            seasonFilter: seasonFilter
        )
    }

    private var hasActiveFilters: Bool {
        TripHistoryLogic.hasActiveFilters(
            selectedWaterbodyID: selectedWaterbodyID,
            speciesQuery: speciesQuery,
            dateFilter: dateFilter,
            seasonFilter: seasonFilter,
            selectedLure: selectedLure
        )
    }

    private var catchCountsByTripID: [UUID: Int] {
        Dictionary(catches.compactMap { catchRecord in
            guard let tripID = catchRecord.trip?.id else { return nil }
            return (tripID, 1)
        }, uniquingKeysWith: +)
    }

    var body: some View {
        NavigationStack(path: $path) {
            Group {
                if trips.isEmpty {
                    ContentUnavailableView {
                        Label("No Trips Yet", systemImage: "water.waves")
                    } description: {
                        Text("Start a trip from the Log tab to begin building your private fishing memory.")
                    }
                } else {
                    List {
                        Section("Filters") {
                            Picker("Water", selection: $selectedWaterbodyID) {
                                Text("All waters").tag(Optional<UUID>.none)
                                ForEach(availableWaterbodies, id: \.id) { waterbody in
                                    Text(waterbody.name).tag(Optional(waterbody.id))
                                }
                            }
                            .pickerStyle(.menu)

                            Picker("Date", selection: $dateFilter) {
                                ForEach(TripDateFilter.allCases) { filter in
                                    Text(filter.label).tag(filter)
                                }
                            }
                            .pickerStyle(.menu)

                            Picker("Season", selection: $seasonFilter) {
                                ForEach(TripSeasonFilter.allCases) { filter in
                                    Text(filter.label).tag(filter)
                                }
                            }
                            .pickerStyle(.menu)

                            TextField("Species", text: $speciesQuery)
                                .textInputAutocapitalization(.words)
                                .accessibilityIdentifier("trips.filter.speciesField")

                            Picker("Lure", selection: $selectedLure) {
                                Text("All lures").tag(Optional<String>.none)
                                ForEach(availableLures, id: \.self) { lure in
                                    Text(lure).tag(Optional(lure))
                                }
                            }
                            .pickerStyle(.menu)

                            if hasActiveFilters {
                                Button("Clear Filters") {
                                    selectedWaterbodyID = nil
                                    speciesQuery = ""
                                    dateFilter = .all
                                    seasonFilter = .all
                                    selectedLure = nil
                                }
                                .font(.footnote.weight(.medium))
                            }
                        }

                        if filteredTrips.isEmpty {
                            Section {
                                SectionEmptyState(
                                    icon: "line.3.horizontal.decrease.circle",
                                    title: "No trips match these filters",
                                    subtitle: "Try a different water, species, date, season, or lure."
                                )
                            }
                        } else {
                            ForEach(filteredTrips, id: \.id) { trip in
                                NavigationLink(value: trip.id) {
                                    TripRow(
                                        trip: trip,
                                        catchCount: catchCountsByTripID[trip.id, default: 0]
                                    )
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Trips")
            .navigationDestination(for: UUID.self) { tripID in
                if let trip = trips.first(where: { $0.id == tripID }) {
                    TripDetailView(trip: trip)
                } else {
                    ContentUnavailableView("Trip not found", systemImage: "exclamationmark.triangle")
                }
            }
            .onAppear {
                openPendingTripIfPossible()
            }
            .onChange(of: availableLures) { _, _ in
                clearUnavailableSelectedLure()
            }
            .onChange(of: selectedTripID) { _, _ in
                openPendingTripIfPossible()
            }
            .onChange(of: trips.map(\.id)) { _, _ in
                openPendingTripIfPossible()
            }
        }
    }

    private func openPendingTripIfPossible() {
        guard let selectedTripID, trips.contains(where: { $0.id == selectedTripID }) else { return }
        path = NavigationPath()
        path.append(selectedTripID)
        self.selectedTripID = nil
    }

    private func clearUnavailableSelectedLure() {
        guard let selectedLure else { return }

        let normalizedSelection = selectedLure
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        let selectionIsAvailable = availableLures.contains { lure in
            lure.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == normalizedSelection
        }

        if !selectionIsAvailable {
            self.selectedLure = nil
        }
    }
}

// MARK: - Trip Row

private struct TripRow: View {
    let trip: Trip
    let catchCount: Int
    private var rowSummary: TripRowSummary {
        TripPresentationLogic.tripRowSummary(trip: trip, catchCount: catchCount)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack(alignment: .firstTextBaseline) {
                Text(trip.title)
                    .font(.subheadline.weight(.semibold))

                if trip.isActive {
                    AppBadge(text: "Live")
                }

                Spacer()

                Text(rowSummary.catchCountText)
                    .font(.subheadline.weight(.semibold).monospacedDigit())
                    .foregroundColor(rowSummary.showsSkunkedStyle ? .secondary : .appAccent)
            }

            HStack(spacing: Spacing.md) {
                Label(AppFormatters.tripDate.string(from: trip.startAt), systemImage: "calendar")

                if let durationText = rowSummary.durationText {
                    Label(durationText, systemImage: "timer")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if let spot = rowSummary.spotTitle {
                Label(spot, systemImage: "mappin")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.vertical, Spacing.xs)
    }
}

// MARK: - Trip Detail

private enum TripDetailSheet: Identifiable {
    case editTrip
    case newCatch
    case editCatch(UUID)

    var id: String {
        switch self {
        case .editTrip:
            return "edit-trip"
        case .newCatch:
            return "new-catch"
        case let .editCatch(id):
            return "edit-catch-\(id.uuidString)"
        }
    }
}

struct TripDetailView: View {
    let trip: Trip

    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var allCatches: [CatchRecord]
    @State private var activeSheet: TripDetailSheet?

    private var catches: [CatchRecord] {
        allCatches.filter { $0.trip?.id == trip.id }
    }

    private var topStats: [(value: String, label: String, icon: String)] {
        TripPresentationLogic.topStats(
            catchCount: catches.count,
            durationText: trip.endAt.flatMap { AppFormatters.duration.string(from: $0.timeIntervalSince(trip.startAt)) },
            targetSpeciesCount: trip.targetSpeciesList.count
        ).map { ($0.value, $0.label, $0.icon) }
    }

    var body: some View {
        List {
            Section {
                HStack(spacing: Spacing.xl) {
                    ForEach(Array(topStats.enumerated()), id: \.offset) { _, stat in
                        TripStatPill(value: stat.value, label: stat.label, icon: stat.icon)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, Spacing.sm)
                .listRowBackground(Color.clear)
            }

            Section("Details") {
                LabeledContent("Water", value: trip.waterbody?.name ?? "Unknown")
                LabeledContent("Spot", value: trip.spot?.title ?? "General area")
                LabeledContent("Started", value: AppFormatters.tripDate.string(from: trip.startAt))
                if let endAt = trip.endAt {
                    LabeledContent("Ended", value: AppFormatters.tripDate.string(from: endAt))
                } else {
                    HStack {
                        Text("Status")
                        Spacer()
                        AppBadge(text: "Live")
                    }
                }
                if !trip.targetSpeciesList.isEmpty {
                    LabeledContent(
                        trip.targetSpeciesList.count > 1 ? "Targets" : "Target",
                        value: trip.targetSpeciesList.joined(separator: ", ")
                    )
                }
                if !trip.notes.isEmpty {
                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        Text("Notes")
                            .foregroundStyle(.secondary)
                        Text(trip.notes)
                    }
                }
            }

            if let snapshot = trip.conditionSnapshot {
                Section("Conditions") {
                    LabeledContent("Status", value: snapshot.statusLine)
                    if let placeSummary = snapshot.placeSummary {
                        LabeledContent("Place", value: placeSummary)
                    }
                    if let timeWindowSummary = snapshot.timeWindowSummary {
                        LabeledContent("Window", value: timeWindowSummary)
                    }
                    if let lightLevelSummary = snapshot.lightLevelSummary {
                        LabeledContent("Light", value: lightLevelSummary)
                    }
                    LabeledContent("Weather", value: snapshot.weatherLine)
                    if let coordinateSummary = snapshot.coordinateSummary {
                        LabeledContent("Coordinates", value: coordinateSummary)
                    }
                }
            }

            Section {
                if catches.isEmpty {
                    SectionEmptyState(
                        icon: "fish",
                        title: "No catches",
                        subtitle: trip.outcomeRawValue == TripOutcome.skunked.rawValue
                            ? "Tough day. They all count."
                            : "No catches logged on this trip."
                    )
                } else {
                    ForEach(catches, id: \.id) { catchRecord in
                        Button {
                            activeSheet = .editCatch(catchRecord.id)
                        } label: {
                            CatchHistoryRow(catchRecord: catchRecord, includeTimestamp: true)
                        }
                        .buttonStyle(.plain)
                    }
                }
            } header: {
                HStack {
                    Text("Catches")
                    Spacer()
                    Text("\(catches.count)")
                        .font(.footnote.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            } footer: {
                Button {
                    activeSheet = .newCatch
                } label: {
                    Label("Add Catch", systemImage: "plus.circle.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.appAccent)
            }
        }
        .navigationTitle(trip.title)
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Edit Trip") {
                    activeSheet = .editTrip
                }
            }
        }
        .sheet(item: $activeSheet) { sheet in
            switch sheet {
            case .editTrip:
                TripEditorView(trip: trip, catchCount: catches.count)
            case .newCatch:
                CatchEditorView(trip: trip)
            case let .editCatch(catchID):
                if let catchRecord = catches.first(where: { $0.id == catchID }) {
                    CatchEditorView(trip: trip, catchRecord: catchRecord)
                } else {
                    ContentUnavailableView("Catch not found", systemImage: "exclamationmark.triangle")
                }
            }
        }
    }
}

private struct TripEditorView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]
    @Query(sort: \Spot.createdAt) private var spots: [Spot]

    let trip: Trip
    let catchCount: Int

    @State private var selectedWaterbodyID: UUID?
    @State private var selectedSpotID: UUID?
    @State private var startAt: Date
    @State private var endAt: Date
    @State private var isTripActive: Bool
    @State private var targetSpecies: String
    @State private var notes: String
    @State private var placeSummary: String
    @State private var timeWindowSummary: String
    @State private var lightLevelSummary: String
    @State private var weatherSummary: String
    @State private var windSummary: String
    @State private var cloudCoverSummary: String
    @State private var precipitationSummary: String
    @State private var temperatureC: String
    @State private var latitude: String
    @State private var longitude: String

    init(trip: Trip, catchCount: Int) {
        self.trip = trip
        self.catchCount = catchCount
        _selectedWaterbodyID = State(initialValue: trip.waterbody?.id)
        _selectedSpotID = State(initialValue: trip.spot?.id)
        _startAt = State(initialValue: trip.startAt)
        _endAt = State(initialValue: trip.endAt ?? Date())
        _isTripActive = State(initialValue: trip.endAt == nil)
        _targetSpecies = State(initialValue: trip.targetSpecies)
        _notes = State(initialValue: trip.notes)
        _placeSummary = State(initialValue: trip.conditionSnapshot?.placeSummary ?? "")
        _timeWindowSummary = State(initialValue: trip.conditionSnapshot?.timeWindowSummary ?? "")
        _lightLevelSummary = State(initialValue: trip.conditionSnapshot?.lightLevelSummary ?? "")
        _weatherSummary = State(initialValue: trip.conditionSnapshot?.weatherSummary ?? "")
        _windSummary = State(initialValue: trip.conditionSnapshot?.windSummary ?? "")
        _cloudCoverSummary = State(initialValue: trip.conditionSnapshot?.cloudCoverSummary ?? "")
        _precipitationSummary = State(initialValue: trip.conditionSnapshot?.precipitationSummary ?? "")
        _temperatureC = State(initialValue: trip.conditionSnapshot?.temperatureC.map { String($0) } ?? "")
        _latitude = State(initialValue: trip.conditionSnapshot?.latitude.map { String($0) } ?? "")
        _longitude = State(initialValue: trip.conditionSnapshot?.longitude.map { String($0) } ?? "")
    }

    private var filteredSpots: [Spot] {
        TripEditingLogic.filteredSpots(spots: spots, selectedWaterbodyID: selectedWaterbodyID)
    }

    private var canSave: Bool {
        TripEditingLogic.canSave(
            selectedWaterbodyID: selectedWaterbodyID,
            isTripActive: isTripActive,
            startAt: startAt,
            endAt: endAt
        )
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Where") {
                    Picker("Waterbody", selection: $selectedWaterbodyID) {
                        Text("Select water").tag(Optional<UUID>.none)
                        ForEach(waterbodies, id: \.id) { waterbody in
                            Text(waterbody.name).tag(Optional(waterbody.id))
                        }
                    }

                    Picker("Spot", selection: $selectedSpotID) {
                        Text("General area").tag(Optional<UUID>.none)
                        ForEach(filteredSpots, id: \.id) { spot in
                            Text(spot.title).tag(Optional(spot.id))
                        }
                    }
                }

                Section("Trip") {
                    DatePicker("Started", selection: $startAt)
                    Toggle("Trip is still active", isOn: $isTripActive)
                    if !isTripActive {
                        DatePicker("Ended", selection: $endAt, in: startAt...)
                    }
                    TextField("Target species, separated by commas", text: $targetSpecies)
                        .textInputAutocapitalization(.words)
                    TextField("Notes", text: $notes, axis: .vertical)
                        .lineLimit(2...4)
                }

                if trip.conditionSnapshot != nil {
                    Section("Conditions") {
                        TextField("Place summary", text: $placeSummary)
                            .textInputAutocapitalization(.words)
                        TextField("Time window", text: $timeWindowSummary)
                            .textInputAutocapitalization(.words)
                        TextField("Light", text: $lightLevelSummary)
                            .textInputAutocapitalization(.words)
                        TextField("Weather", text: $weatherSummary)
                            .textInputAutocapitalization(.words)
                        TextField("Wind", text: $windSummary)
                            .textInputAutocapitalization(.words)
                        TextField("Cloud cover", text: $cloudCoverSummary)
                            .textInputAutocapitalization(.words)
                        TextField("Precipitation", text: $precipitationSummary)
                            .textInputAutocapitalization(.words)
                        TextField("Temperature C", text: $temperatureC)
                            .keyboardType(.decimalPad)
                        TextField("Latitude", text: $latitude)
                            .keyboardType(.decimalPad)
                        TextField("Longitude", text: $longitude)
                            .keyboardType(.decimalPad)
                    }
                }
            }
            .navigationTitle("Edit Trip")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        save()
                    }
                    .fontWeight(.semibold)
                    .disabled(!canSave)
                }
            }
        }
        .presentationDetents([.large])
        .onChange(of: selectedWaterbodyID) { _, newValue in
            selectedSpotID = TripEditingLogic.selectedSpotIDAfterWaterbodyChange(
                selectedSpotID: selectedSpotID,
                filteredSpots: filteredSpots
            )
            if newValue == nil { selectedSpotID = nil }
        }
    }

    private func save() {
        trip.waterbody = waterbodies.first(where: { $0.id == selectedWaterbodyID })
        trip.spot = filteredSpots.first(where: { $0.id == selectedSpotID })
        trip.startAt = startAt
        trip.endAt = isTripActive ? nil : endAt
        trip.targetSpecies = TripEditingLogic.normalizedText(targetSpecies)
        trip.notes = TripEditingLogic.normalizedText(notes)
        trip.outcomeRawValue = TripEditingLogic.tripOutcome(endAt: trip.endAt, catchCount: catchCount).rawValue

        if let snapshot = trip.conditionSnapshot {
            let draft = TripEditingLogic.conditionDraft(
                placeSummary: placeSummary,
                timeWindowSummary: timeWindowSummary,
                lightLevelSummary: lightLevelSummary,
                weatherSummary: weatherSummary,
                windSummary: windSummary,
                cloudCoverSummary: cloudCoverSummary,
                precipitationSummary: precipitationSummary,
                temperatureC: temperatureC,
                latitude: latitude,
                longitude: longitude
            )
            snapshot.placeSummary = draft.placeSummary
            snapshot.timeWindowSummary = draft.timeWindowSummary
            snapshot.lightLevelSummary = draft.lightLevelSummary
            snapshot.weatherSummary = draft.weatherSummary
            snapshot.windSummary = draft.windSummary
            snapshot.cloudCoverSummary = draft.cloudCoverSummary
            snapshot.precipitationSummary = draft.precipitationSummary
            snapshot.temperatureC = draft.temperatureC
            snapshot.latitude = draft.latitude
            snapshot.longitude = draft.longitude
        }

        try? modelContext.save()
        dismiss()
    }
}

struct CatchEditorView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    let trip: Trip
    let catchRecord: CatchRecord?

    @State private var species: String
    @State private var caughtAt: Date
    @State private var lureOrBait: String
    @State private var method: String
    @State private var weight: String
    @State private var length: String
    @State private var note: String
    @State private var photoData: Data?
    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var showingDeleteConfirmation = false
    @State private var shareImage: UIImage?
    @State private var showingShareSheet = false

    init(trip: Trip, catchRecord: CatchRecord? = nil) {
        self.trip = trip
        self.catchRecord = catchRecord
        _species = State(initialValue: catchRecord?.species ?? "")
        _caughtAt = State(initialValue: catchRecord?.caughtAt ?? trip.endAt ?? Date())
        _lureOrBait = State(initialValue: catchRecord?.lureOrBait ?? "")
        _method = State(initialValue: catchRecord?.method ?? "")
        _weight = State(initialValue: catchRecord?.weightKg.map { String($0) } ?? "")
        _length = State(initialValue: catchRecord?.lengthCm.map { String($0) } ?? "")
        _note = State(initialValue: catchRecord?.note ?? "")
        _photoData = State(initialValue: catchRecord?.photoData)
    }

    private var sheetTitle: String {
        catchRecord == nil ? "Add Catch" : "Edit Catch"
    }

    @ViewBuilder
    private var catchSection: some View {
        Section("Catch") {
            TextField("Species (optional)", text: $species)
                .textInputAutocapitalization(.words)
            DatePicker("Caught at", selection: $caughtAt)
            TextField("Lure or bait", text: $lureOrBait)
                .textInputAutocapitalization(.words)
            TextField("Method", text: $method)
                .textInputAutocapitalization(.words)
            TextField("Weight (kg)", text: $weight)
                .keyboardType(.decimalPad)
            TextField("Length (cm)", text: $length)
                .keyboardType(.decimalPad)
            TextField("Note", text: $note, axis: .vertical)
                .lineLimit(2...4)
        }
    }

    @ViewBuilder
    private var photoSection: some View {
        Section {
            if let photoData {
                HStack(spacing: Spacing.md) {
                    CatchPhotoThumbnailView(data: photoData)
                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        Text("Photo attached")
                            .font(.footnote.weight(.semibold))
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
            }
            .buttonStyle(.bordered)
            .tint(.appAccent)
        } header: {
            Text("Photo")
        } footer: {
            Text("Photo stays optional. You can save this catch without one.")
        }
    }

    @ViewBuilder
    private var deleteSection: some View {
        if catchRecord != nil {
            Section {
                Button {
                    shareCatch()
                } label: {
                    Label("Share Catch", systemImage: "square.and.arrow.up")
                }

                Button("Delete Catch", role: .destructive) {
                    showingDeleteConfirmation = true
                }
            }
        }
    }

    var body: some View {
        NavigationStack {
            Form {
                catchSection
                photoSection
                deleteSection
            }
            .navigationTitle(sheetTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        save()
                    }
                    .fontWeight(.semibold)
                }
            }
        }
        .presentationDetents([.large])
        .alert("Delete this catch?", isPresented: $showingDeleteConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Delete Catch", role: .destructive) {
                deleteCatch()
            }
        } message: {
            Text("This removes the catch from the trip history.")
        }
        .onChange(of: selectedPhotoItem) { _, newValue in
            guard let newValue else { return }
            Task {
                photoData = try? await newValue.loadTransferable(type: Data.self)
            }
        }
        .sheet(isPresented: $showingShareSheet) {
            if let shareImage {
                ActivityShareSheet(activityItems: [shareImage])
            }
        }
    }

    private func save() {
        let record = catchRecord ?? CatchRecord(species: "", trip: trip)
        if catchRecord == nil {
            modelContext.insert(record)
        }
        let draft = TripEditingLogic.catchDraft(
            species: species,
            lureOrBait: lureOrBait,
            method: method,
            weight: weight,
            length: length,
            note: note,
            photoData: photoData
        )

        record.trip = trip
        record.species = draft.species
        record.caughtAt = caughtAt
        record.lureOrBait = draft.lureOrBait
        record.method = draft.method
        record.weightKg = draft.weightKg
        record.lengthCm = draft.lengthCm
        record.note = draft.note
        record.photoData = photoData
        record.photoReference = draft.photoReference
        record.photoContentType = draft.photoContentType

        persistCatchChanges()
        dismiss()
    }

    private func deleteCatch() {
        guard let catchRecord else { return }
        modelContext.delete(catchRecord)
        persistCatchChanges()
        dismiss()
    }

    private func persistCatchChanges() {
        try? syncTripOutcomeAndPersonalBests(for: trip, in: modelContext)
        try? modelContext.save()
    }

    private func shareCatch() {
        guard let catchRecord else { return }
        guard let image = CatchShareCardRenderer.renderImage(for: catchRecord) else { return }
        shareImage = image
        showingShareSheet = true
    }
}

struct CatchShareCardContent {
    let speciesName: String
    let dateText: String
    let lureOrBaitText: String?
    let weightText: String?
    let lengthText: String?
    let photoData: Data?
}

enum CatchShareCardLogic {
    private static let coarseDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        return formatter
    }()

    static func content(for catchRecord: CatchRecord) -> CatchShareCardContent {
        CatchShareCardContent(
            speciesName: catchRecord.speciesDisplayName,
            dateText: coarseDateFormatter.string(from: catchRecord.caughtAt),
            lureOrBaitText: normalizedOptionalText(catchRecord.lureOrBait),
            weightText: catchRecord.weightKg.map { "\($0.formatted()) kg" },
            lengthText: catchRecord.lengthCm.map { "\($0.formatted()) cm" },
            photoData: catchRecord.photoData
        )
    }

    private static func normalizedOptionalText(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}

enum CatchShareCardRenderer {
    @MainActor
    static func renderImage(for catchRecord: CatchRecord, scale: CGFloat = 3) -> UIImage? {
        let renderer = ImageRenderer(
            content: CatchShareCardView(content: CatchShareCardLogic.content(for: catchRecord))
                .frame(width: 1080, height: 1350)
                .background(Color(.systemBackground))
        )
        renderer.scale = scale
        return renderer.uiImage
    }
}

private struct CatchShareCardView: View {
    let content: CatchShareCardContent

    private var detailRows: [String] {
        [content.lureOrBaitText, content.weightText, content.lengthText].compactMap { $0 }
    }

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color.teal.opacity(0.18), Color.blue.opacity(0.08), Color(.systemBackground)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            VStack(alignment: .leading, spacing: 32) {
                Text(content.dateText)
                    .font(.system(size: 42, weight: .medium, design: .rounded))
                    .foregroundStyle(.secondary)

                Text(content.speciesName)
                    .font(.system(size: 88, weight: .bold, design: .rounded))
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                    .minimumScaleFactor(0.75)

                if let image = sharePhoto {
                    image
                        .resizable()
                        .scaledToFill()
                        .frame(maxWidth: .infinity)
                        .frame(height: 620)
                        .clipShape(RoundedRectangle(cornerRadius: 36, style: .continuous))
                } else {
                    VStack(alignment: .leading, spacing: 20) {
                        Image(systemName: "fish.fill")
                            .font(.system(size: 72))
                            .foregroundStyle(.appAccent)
                        Text("Logged catch")
                            .font(.system(size: 48, weight: .semibold, design: .rounded))
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, minHeight: 360, alignment: .leading)
                    .padding(40)
                    .background(.background.opacity(0.92), in: RoundedRectangle(cornerRadius: 36, style: .continuous))
                }

                if !detailRows.isEmpty {
                    VStack(alignment: .leading, spacing: 16) {
                        ForEach(detailRows, id: \.self) { detail in
                            Text(detail)
                                .font(.system(size: 42, weight: .semibold, design: .rounded))
                                .foregroundStyle(.primary)
                        }
                    }
                }

                Spacer()
            }
            .padding(60)
        }
    }

    private var sharePhoto: Image? {
        guard let data = content.photoData, let uiImage = UIImage(data: data) else {
            return nil
        }
        return Image(uiImage: uiImage)
    }
}

private struct ActivityShareSheet: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

// MARK: - Trip Stat Pill

private struct TripStatPill: View {
    let value: String
    let label: String
    let icon: String

    var body: some View {
        VStack(spacing: Spacing.xs) {
            Image(systemName: icon)
                .font(.caption2)
                .foregroundStyle(.appAccent)
            Text(value)
                .font(.subheadline.weight(.semibold).monospacedDigit())
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }
}

private func syncTripOutcomeAndPersonalBests(for trip: Trip, in context: ModelContext) throws {
    let catches = try context.fetch(FetchDescriptor<CatchRecord>())
        .filter { $0.trip?.id == trip.id }

    trip.outcomeRawValue = TripEditingLogic.tripOutcome(endAt: trip.endAt, catchCount: catches.count).rawValue
    try PersonalBestService.rebuild(in: context)
}
