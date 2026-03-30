import PhotosUI
import SwiftData
import SwiftUI

struct TripsView: View {
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]
    @Binding private var selectedTripID: UUID?
    @State private var path = NavigationPath()

    init(selectedTripID: Binding<UUID?> = .constant(nil)) {
        _selectedTripID = selectedTripID
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
                        ForEach(trips, id: \.id) { trip in
                            NavigationLink(value: trip.id) {
                                TripRow(
                                    trip: trip,
                                    catchCount: catches.filter { $0.trip?.id == trip.id }.count
                                )
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
}

// MARK: - Trip Row

private struct TripRow: View {
    let trip: Trip
    let catchCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack(alignment: .firstTextBaseline) {
                Text(trip.title)
                    .font(.subheadline.weight(.semibold))

                if trip.isActive {
                    AppBadge(text: "Live")
                }

                Spacer()

                Text(catchCount == 0 && !trip.isActive ? "Skunked" : "\(catchCount)")
                    .font(.subheadline.weight(.semibold).monospacedDigit())
                    .foregroundColor(catchCount == 0 && !trip.isActive ? .secondary : .appAccent)
            }

            HStack(spacing: Spacing.md) {
                Label(AppFormatters.tripDate.string(from: trip.startAt), systemImage: "calendar")

                if let endAt = trip.endAt {
                    let duration = endAt.timeIntervalSince(trip.startAt)
                    if let durationText = AppFormatters.duration.string(from: duration) {
                        Label(durationText, systemImage: "timer")
                    }
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if let spot = trip.spot?.title {
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
        var stats: [(value: String, label: String, icon: String)] = [
            ("\(catches.count)", catches.count == 1 ? "Catch" : "Catches", "fish")
        ]

        if let endAt = trip.endAt,
           let durationText = AppFormatters.duration.string(from: endAt.timeIntervalSince(trip.startAt)) {
            stats.append((durationText, "Duration", "timer"))
        }

        if !trip.targetSpeciesList.isEmpty {
            let targetCount = trip.targetSpeciesList.count
            stats.append(("\(targetCount)", targetCount == 1 ? "Target" : "Targets", "scope"))
        }

        return stats
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
        guard let selectedWaterbodyID else { return spots }
        return spots.filter { $0.waterbody?.id == selectedWaterbodyID }
    }

    private var canSave: Bool {
        selectedWaterbodyID != nil && (isTripActive || endAt >= startAt)
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
            if filteredSpots.contains(where: { $0.id == selectedSpotID }) {
                return
            }
            selectedSpotID = nil
            if newValue == nil {
                selectedSpotID = nil
            }
        }
    }

    private func save() {
        trip.waterbody = waterbodies.first(where: { $0.id == selectedWaterbodyID })
        trip.spot = filteredSpots.first(where: { $0.id == selectedSpotID })
        trip.startAt = startAt
        trip.endAt = isTripActive ? nil : endAt
        trip.targetSpecies = targetSpecies.trimmingCharacters(in: .whitespacesAndNewlines)
        trip.notes = notes.trimmingCharacters(in: .whitespacesAndNewlines)
        trip.outcomeRawValue = tripOutcome(for: trip.endAt, catchCount: catchCount).rawValue

        if let snapshot = trip.conditionSnapshot {
            snapshot.placeSummary = trimmedOrNil(placeSummary)
            snapshot.timeWindowSummary = trimmedOrNil(timeWindowSummary)
            snapshot.lightLevelSummary = trimmedOrNil(lightLevelSummary)
            snapshot.weatherSummary = trimmedOrNil(weatherSummary)
            snapshot.windSummary = trimmedOrNil(windSummary)
            snapshot.cloudCoverSummary = trimmedOrNil(cloudCoverSummary)
            snapshot.precipitationSummary = trimmedOrNil(precipitationSummary)
            snapshot.temperatureC = Double(temperatureC.trimmingCharacters(in: .whitespacesAndNewlines))
            snapshot.latitude = Double(latitude.trimmingCharacters(in: .whitespacesAndNewlines))
            snapshot.longitude = Double(longitude.trimmingCharacters(in: .whitespacesAndNewlines))
        }

        try? modelContext.save()
        dismiss()
    }
}

private struct CatchEditorView: View {
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
    }

    private func save() {
        let record = catchRecord ?? CatchRecord(species: "", trip: trip)
        if catchRecord == nil {
            modelContext.insert(record)
        }

        record.trip = trip
        record.species = species.trimmingCharacters(in: .whitespacesAndNewlines)
        record.caughtAt = caughtAt
        record.lureOrBait = lureOrBait.trimmingCharacters(in: .whitespacesAndNewlines)
        record.method = method.trimmingCharacters(in: .whitespacesAndNewlines)
        record.weightKg = Double(weight.trimmingCharacters(in: .whitespacesAndNewlines))
        record.lengthCm = Double(length.trimmingCharacters(in: .whitespacesAndNewlines))
        record.note = note.trimmingCharacters(in: .whitespacesAndNewlines)
        record.photoData = photoData
        record.photoReference = photoData == nil ? nil : "embedded-photo"
        record.photoContentType = photoData == nil ? nil : "image/jpeg"

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

private func trimmedOrNil(_ value: String) -> String? {
    let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
    return trimmed.isEmpty ? nil : trimmed
}

private func tripOutcome(for endAt: Date?, catchCount: Int) -> TripOutcome {
    guard endAt != nil else { return .active }
    return catchCount == 0 ? .skunked : .caught
}

private func syncTripOutcomeAndPersonalBests(for trip: Trip, in context: ModelContext) throws {
    let catches = try context.fetch(FetchDescriptor<CatchRecord>())
        .filter { $0.trip?.id == trip.id }

    trip.outcomeRawValue = tripOutcome(for: trip.endAt, catchCount: catches.count).rawValue
    try PersonalBestService.rebuild(in: context)
}
