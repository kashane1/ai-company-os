import CoreLocation
import MapKit
import SwiftData
import SwiftUI

struct NewSpotForm: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @StateObject private var locationRecorder = LocationRecorder()

    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]

    @State private var title = ""
    @State private var notes = ""
    @State private var selectedWaterbodyID: UUID?
    @State private var showingWaterbodyForm = false
    @State private var showingCoordinatePicker = false
    @State private var selectedCoordinate: CLLocationCoordinate2D?
    @State private var hasCustomizedCoordinate = false
    @State private var persistenceErrorMessage: String?
    @State private var pendingDetected: WaterbodyAutoDetectionService.Detected?
    @State private var waterbodyWasAutoDetected = false
    @State private var isDetectingWaterbody = false

    var preselectedWaterbodyID: UUID?
    var initialCoordinate: CLLocationCoordinate2D?
    var onSaved: ((Spot) -> Void)?

    init(
        preselectedWaterbodyID: UUID? = nil,
        initialCoordinate: CLLocationCoordinate2D? = nil,
        onSaved: ((Spot) -> Void)? = nil
    ) {
        self.preselectedWaterbodyID = preselectedWaterbodyID
        self.initialCoordinate = initialCoordinate
        self.onSaved = onSaved
        _selectedWaterbodyID = State(initialValue: preselectedWaterbodyID)
        _selectedCoordinate = State(initialValue: initialCoordinate)
        _hasCustomizedCoordinate = State(initialValue: initialCoordinate != nil)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Spot name", text: $title)
                        .textInputAutocapitalization(.words)
                        .submitLabel(.next)

                    Picker("Waterbody", selection: $selectedWaterbodyID) {
                        Text("None").tag(Optional<UUID>.none)
                        if !waterbodies.isEmpty {
                            Divider()
                            ForEach(waterbodies, id: \.id) { waterbody in
                                Text(waterbody.name).tag(Optional(waterbody.id))
                            }
                        }
                    }

                    if isDetectingWaterbody {
                        HStack(spacing: Spacing.sm) {
                            ProgressView()
                                .controlSize(.small)
                            Text("Detecting waterbody…")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    } else if waterbodyWasAutoDetected, pendingDetected != nil || selectedWaterbodyID != nil {
                        Text("Detected from your location")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }

                    Button {
                        showingWaterbodyForm = true
                    } label: {
                        Label("Add Waterbody", systemImage: "plus")
                            .font(.footnote)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)

                    TextField("Notes", text: $notes, axis: .vertical)
                        .lineLimit(2...4)

                    Button {
                        if selectedCoordinate == nil {
                            selectedCoordinate = preferredInitialCoordinate
                        }
                        showingCoordinatePicker = true
                    } label: {
                        Label(selectedCoordinate == nil ? "Drop Spot Pin" : "Refine Spot Pin", systemImage: "mappin.and.ellipse")
                    }

                    if let pinnedCoordinate = selectedCoordinate {
                        LabeledContent("Spot pin", value: coordinateText(for: pinnedCoordinate))
                        SpotCoordinatePreview(
                            title: title.isEmpty ? "Pinned spot" : title,
                            coordinate: pinnedCoordinate
                        )

                        Button("Use Current Location") {
                            if let location = locationRecorder.lastLocation?.coordinate {
                                selectedCoordinate = location
                                hasCustomizedCoordinate = true
                            }
                        }
                        .disabled(locationRecorder.lastLocation == nil)
                    }
                } header: {
                    Text("Spot")
                } footer: {
                    Text("Private by default. Drop a pin and we'll try to guess the waterbody from Apple Maps. You can skip or change it any time.")
                }
            }
            .navigationTitle("New Spot")
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
            .interactiveDismissDisabled(!title.isEmpty)
        }
        .presentationDetents([.medium, .large])
        .onAppear {
            locationRecorder.requestIfNeeded()
            primeCoordinateIfNeeded()
        }
        .task(id: selectedCoordinate?.latitude) {
            guard selectedCoordinate != nil,
                  selectedWaterbodyID == nil,
                  pendingDetected == nil else { return }
            await detectWaterbody()
        }
        .onChange(of: locationRecorder.lastLocation?.coordinate.latitude) { _, _ in
            primeCoordinateIfNeeded()
        }
        .onChange(of: selectedWaterbodyID) { oldValue, newValue in
            primeCoordinateIfNeeded()
            // User manually changed the picker → clear auto-detect state so
            // the "Detected from your location" caption goes away and we
            // don't overwrite their choice on the next save().
            if oldValue != newValue, newValue != nil {
                if let match = waterbodies.first(where: { $0.id == newValue }),
                   pendingDetected?.name.lowercased() != match.name.lowercased() {
                    pendingDetected = nil
                    waterbodyWasAutoDetected = false
                }
            }
        }
        .sheet(isPresented: $showingWaterbodyForm) {
            NewWaterbodyForm { waterbody in
                selectedWaterbodyID = waterbody.id
                pendingDetected = nil
                waterbodyWasAutoDetected = false
            }
        }
        .sheet(isPresented: $showingCoordinatePicker) {
            SpotCoordinatePickerSheet(
                title: title.isEmpty ? "Spot Pin" : title,
                initialCoordinate: selectedCoordinate ?? preferredInitialCoordinate
            ) { coordinate in
                selectedCoordinate = coordinate
                hasCustomizedCoordinate = true
                // New pin → re-run detection for the new location.
                pendingDetected = nil
                waterbodyWasAutoDetected = false
            }
        }
        .persistenceFailureAlert(message: $persistenceErrorMessage)
    }

    private var canSave: Bool {
        SpotFormLogic.canSave(title: title)
    }

    private var selectedWaterbody: Waterbody? {
        waterbodies.first(where: { $0.id == selectedWaterbodyID })
    }

    private func save() {
        let draft = SpotFormLogic.draft(title: title, notes: notes, coordinate: selectedCoordinate)
        var spotToDeliver: Spot?
        PersistenceWriteCoordinator.perform(
            commit: {
                let resolvedWaterbody: Waterbody?
                if let userPicked = selectedWaterbody {
                    resolvedWaterbody = userPicked
                } else if let pendingDetected {
                    // Defer-commit: the auto-detected waterbody is only
                    // inserted now, inside the save transaction, so
                    // dismissing the form leaves no phantom records.
                    resolvedWaterbody = try WaterbodyAutoDetectionService.findOrCreate(
                        pendingDetected,
                        in: modelContext
                    )
                } else {
                    resolvedWaterbody = nil
                }

                let spot = Spot(
                    title: draft.title,
                    waterbody: resolvedWaterbody,
                    latitude: draft.latitude,
                    longitude: draft.longitude,
                    notes: draft.notes
                )
                modelContext.insert(spot)
                spotToDeliver = spot
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                if let spotToDeliver {
                    onSaved?(spotToDeliver)
                }
                dismiss()
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }

    private var preferredInitialCoordinate: CLLocationCoordinate2D? {
        if let selectedCoordinate {
            return selectedCoordinate
        }

        if let location = locationRecorder.lastLocation?.coordinate {
            return location
        }

        if let initialCoordinate {
            return initialCoordinate
        }

        return coordinateIfPresent(
            latitude: selectedWaterbody?.latitude,
            longitude: selectedWaterbody?.longitude
        )
    }

    private func primeCoordinateIfNeeded() {
        guard !hasCustomizedCoordinate, selectedCoordinate == nil else { return }
        selectedCoordinate = preferredInitialCoordinate
    }

    private func coordinateText(for coordinate: CLLocationCoordinate2D) -> String {
        String(format: "%.4f, %.4f", coordinate.latitude, coordinate.longitude)
    }

    // MARK: - Waterbody Auto-Detection

    @MainActor
    private func detectWaterbody() async {
        guard let coordinate = selectedCoordinate ?? initialCoordinate else { return }
        isDetectingWaterbody = true
        defer { isDetectingWaterbody = false }

        guard let detected = await WaterbodyAutoDetectionService.detect(at: coordinate) else {
            return
        }

        // Late result after the user dismissed or manually picked? Drop it.
        guard !Task.isCancelled, selectedWaterbodyID == nil else { return }

        pendingDetected = detected
        waterbodyWasAutoDetected = true

        // If an existing Waterbody already matches by name, select it in the
        // picker so the user sees the hit immediately. The actual findOrCreate
        // call still happens inside save() so that cancelling the form never
        // leaves a phantom row.
        let lowered = detected.name.lowercased()
        if let existing = waterbodies.first(where: { $0.name.lowercased() == lowered }) {
            selectedWaterbodyID = existing.id
        }
    }
}

private struct SpotCoordinatePreview: View {
    let title: String
    let coordinate: CLLocationCoordinate2D

    var body: some View {
        Map(
            position: .constant(
                .region(
                    MKCoordinateRegion(
                        center: coordinate,
                        span: MKCoordinateSpan(latitudeDelta: 0.03, longitudeDelta: 0.03)
                    )
                )
            )
        ) {
            Marker(title, coordinate: coordinate)
        }
        .frame(height: 180)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

private struct SpotCoordinatePickerSheet: View {
    @Environment(\.dismiss) private var dismiss

    @State private var selectedCoordinate: CLLocationCoordinate2D
    @State private var position: MapCameraPosition

    let title: String
    let onSave: (CLLocationCoordinate2D) -> Void

    init(
        title: String,
        initialCoordinate: CLLocationCoordinate2D?,
        onSave: @escaping (CLLocationCoordinate2D) -> Void
    ) {
        let fallbackCoordinate = initialCoordinate ?? CLLocationCoordinate2D(latitude: 47.6062, longitude: -122.3321)
        _selectedCoordinate = State(initialValue: fallbackCoordinate)
        _position = State(
            initialValue: .region(
                MKCoordinateRegion(
                    center: fallbackCoordinate,
                    span: MKCoordinateSpan(latitudeDelta: 0.06, longitudeDelta: 0.06)
                )
            )
        )
        self.title = title
        self.onSave = onSave
    }

    var body: some View {
        NavigationStack {
            MapReader { proxy in
                Map(position: $position) {
                    Marker(title, coordinate: selectedCoordinate)
                }
                .onTapGesture { point in
                    if let coordinate = proxy.convert(point, from: .local) {
                        selectedCoordinate = coordinate
                    }
                }
            }
            .overlay(alignment: .bottom) {
                Text("Tap the map to fine-tune your saved spot pin.")
                    .font(.footnote)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(.ultraThinMaterial, in: Capsule())
                    .padding(.bottom, 20)
            }
            .navigationTitle("Choose Spot Pin")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Use Pin") {
                        onSave(selectedCoordinate)
                        dismiss()
                    }
                    .fontWeight(.semibold)
                }
            }
        }
    }
}
