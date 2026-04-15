import CoreLocation
import MapKit
import SwiftData
import SwiftUI

struct NewSpotForm: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @StateObject private var locationRecorder = LocationRecorder()

    @State private var title: String
    @State private var notes: String
    @State private var pinColor: SpotPinColor
    @State private var showingCoordinatePicker = false
    @State private var selectedCoordinate: CLLocationCoordinate2D?
    @State private var hasCustomizedCoordinate: Bool
    @State private var persistenceErrorMessage: String?
    @State private var showingDeleteConfirmation = false
    // Auto-detected waterbody for this spot. Captured silently from the pin
    // coordinate; committed inside save() so cancelling leaves no phantom row.
    // The user never sees or picks waterbody — it's a passive tag.
    @State private var pendingDetected: WaterbodyAutoDetectionService.Detected?

    var initialCoordinate: CLLocationCoordinate2D?
    var editingSpot: Spot?
    var onSaved: ((Spot) -> Void)?
    var onDeleted: (() -> Void)?

    private var isEditing: Bool { editingSpot != nil }

    init(
        initialCoordinate: CLLocationCoordinate2D? = nil,
        editingSpot: Spot? = nil,
        onSaved: ((Spot) -> Void)? = nil,
        onDeleted: (() -> Void)? = nil
    ) {
        self.initialCoordinate = initialCoordinate
        self.editingSpot = editingSpot
        self.onSaved = onSaved
        self.onDeleted = onDeleted

        let existingCoordinate: CLLocationCoordinate2D? = {
            guard let spot = editingSpot,
                  let latitude = spot.latitude,
                  let longitude = spot.longitude
            else { return nil }
            return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
        }()
        let seedCoordinate = existingCoordinate ?? initialCoordinate

        _title = State(initialValue: editingSpot?.title ?? "")
        _notes = State(initialValue: editingSpot?.notes ?? "")
        _pinColor = State(initialValue: editingSpot?.pinColor ?? .blue)
        _selectedCoordinate = State(initialValue: seedCoordinate)
        _hasCustomizedCoordinate = State(initialValue: seedCoordinate != nil)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Spot name", text: $title)
                        .textInputAutocapitalization(.words)
                        .submitLabel(.next)
                        .characterLimit(CharacterLimits.spotName, text: $title)

                    TextField("Notes", text: $notes, axis: .vertical)
                        .lineLimit(2...4)
                        .characterLimit(CharacterLimits.spotNotes, text: $notes)

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
                    Text("Private by default. Drop a pin to mark this spot.")
                }

                Section {
                    HStack(spacing: Spacing.md) {
                        ForEach(SpotPinColor.allCases) { color in
                            Button {
                                pinColor = color
                            } label: {
                                ZStack {
                                    Circle()
                                        .strokeBorder(
                                            pinColor == color ? Color.appAccent : Color.clear,
                                            lineWidth: 2
                                        )
                                        .frame(width: 36, height: 36)
                                    Image(systemName: "mappin.circle.fill")
                                        .font(.title2)
                                        .foregroundStyle(color.color)
                                }
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("\(color.label) pin")
                            .accessibilityAddTraits(pinColor == color ? [.isSelected] : [])
                        }
                        Spacer(minLength: 0)
                    }
                    .padding(.vertical, Spacing.xs)
                } header: {
                    Text("Pin Color")
                } footer: {
                    Text("Pick a color to help group and filter spots on the list view.")
                }

                if isEditing {
                    Section {
                        Button(role: .destructive) {
                            showingDeleteConfirmation = true
                        } label: {
                            Label("Delete Spot", systemImage: "trash")
                        }
                    }
                }
            }
            .navigationTitle(isEditing ? "Edit Spot" : "New Spot")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(isEditing ? "Done" : "Save") {
                        save()
                    }
                    .fontWeight(.semibold)
                    .disabled(!canSave)
                }
            }
            .interactiveDismissDisabled(!title.isEmpty)
            .alert("Delete Spot?", isPresented: $showingDeleteConfirmation) {
                Button("Delete", role: .destructive) { deleteEditingSpot() }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This removes the spot from your saved places. Trips and catches logged here stay, but will no longer be linked to this spot.")
            }
        }
        .presentationDetents([.medium, .large])
        .onAppear {
            locationRecorder.requestIfNeeded()
            primeCoordinateIfNeeded()
        }
        .task(id: selectedCoordinate?.latitude) {
            // Editing preserves the existing waterbody tag — users who want
            // re-detection can delete and recreate the spot.
            guard !isEditing else { return }
            guard selectedCoordinate != nil, pendingDetected == nil else { return }
            await detectWaterbody()
        }
        .onChange(of: locationRecorder.lastLocation?.coordinate.latitude) { _, _ in
            primeCoordinateIfNeeded()
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
            }
        }
        .persistenceFailureAlert(message: $persistenceErrorMessage)
    }

    private var canSave: Bool {
        SpotFormLogic.canSave(title: title)
    }

    private func save() {
        let draft = SpotFormLogic.draft(title: title, notes: notes, coordinate: selectedCoordinate)
        var spotToDeliver: Spot?
        PersistenceWriteCoordinator.perform(
            commit: {
                if let editingSpot {
                    // Edit path: mutate the existing record in place so
                    // related trips/catches remain linked. Waterbody is left
                    // untouched — see the .task guard above.
                    editingSpot.title = draft.title
                    editingSpot.notes = draft.notes
                    editingSpot.latitude = draft.latitude
                    editingSpot.longitude = draft.longitude
                    editingSpot.pinColor = pinColor
                    spotToDeliver = editingSpot
                } else {
                    let resolvedWaterbody: Waterbody?
                    if let pendingDetected {
                        // Defer-commit: the auto-detected waterbody is only
                        // inserted now, inside the save transaction, so
                        // dismissing the form leaves no phantom records. The
                        // user never picked it — it's a passive tag derived
                        // from the spot's coordinate.
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
                        notes: draft.notes,
                        pinColor: pinColor
                    )
                    modelContext.insert(spot)
                    spotToDeliver = spot
                }
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

    private func deleteEditingSpot() {
        guard let editingSpot else { return }
        PersistenceWriteCoordinator.perform(
            commit: {
                modelContext.delete(editingSpot)
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                onDeleted?()
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

        return initialCoordinate
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

        guard let detected = await WaterbodyAutoDetectionService.detect(at: coordinate) else {
            return
        }

        // Late result after the user dismissed? Drop it.
        guard !Task.isCancelled else { return }

        pendingDetected = detected
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
