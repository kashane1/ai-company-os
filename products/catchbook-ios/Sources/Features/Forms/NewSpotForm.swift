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
                if waterbodies.isEmpty {
                    Section {
                        SectionEmptyState(
                            icon: "water.waves",
                            title: "No waterbodies yet",
                            subtitle: "Add a waterbody first, then save this spot."
                        )

                        Button {
                            showingWaterbodyForm = true
                        } label: {
                            Label("Add Waterbody", systemImage: "plus.circle.fill")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.appAccent)
                    }
                } else {
                    Section {
                        TextField("Spot name", text: $title)
                            .textInputAutocapitalization(.words)
                            .submitLabel(.next)

                        Picker("Waterbody", selection: $selectedWaterbodyID) {
                            Text("Select water").tag(Optional<UUID>.none)
                            ForEach(waterbodies, id: \.id) { waterbody in
                                Text(waterbody.name).tag(Optional(waterbody.id))
                            }
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
                        Text("Private by default. Catchbook drops a pin using your best available location and lets you adjust it if needed.")
                    }
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
        .onChange(of: locationRecorder.lastLocation?.coordinate.latitude) { _, _ in
            primeCoordinateIfNeeded()
        }
        .onChange(of: selectedWaterbodyID) { _, _ in
            primeCoordinateIfNeeded()
        }
        .sheet(isPresented: $showingWaterbodyForm) {
            NewWaterbodyForm { waterbody in
                selectedWaterbodyID = waterbody.id
            }
        }
        .sheet(isPresented: $showingCoordinatePicker) {
            SpotCoordinatePickerSheet(
                title: title.isEmpty ? "Spot Pin" : title,
                initialCoordinate: selectedCoordinate ?? preferredInitialCoordinate
            ) { coordinate in
                selectedCoordinate = coordinate
                hasCustomizedCoordinate = true
            }
        }
        .persistenceFailureAlert(message: $persistenceErrorMessage)
    }

    private var canSave: Bool {
        SpotFormLogic.canSave(title: title, selectedWaterbodyID: selectedWaterbodyID)
    }

    private var selectedWaterbody: Waterbody? {
        waterbodies.first(where: { $0.id == selectedWaterbodyID })
    }

    private func save() {
        let draft = SpotFormLogic.draft(title: title, notes: notes, coordinate: selectedCoordinate)
        let spot = Spot(
            title: draft.title,
            waterbody: selectedWaterbody,
            latitude: draft.latitude,
            longitude: draft.longitude,
            notes: draft.notes
        )
        modelContext.insert(spot)
        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                onSaved?(spot)
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
