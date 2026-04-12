import MapKit
import SwiftData
import SwiftUI

struct NewWaterbodyForm: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @StateObject private var searchModel = WaterbodySearchModel()
    @StateObject private var locationRecorder = LocationRecorder()

    @State private var name = ""
    @State private var type: WaterbodyType = .lake
    @State private var selectedCoordinate: CLLocationCoordinate2D?
    @State private var showingCoordinatePicker = false
    @State private var hasCustomizedCoordinate = false
    @State private var isResolvingSuggestion = false
    @State private var persistenceErrorMessage: String?

    var onSaved: ((Waterbody) -> Void)?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Search waters or places", text: $name)
                        .textInputAutocapitalization(.words)
                        .submitLabel(.search)

                    if isResolvingSuggestion {
                        ProgressView("Finding place details…")
                            .font(.footnote)
                    }

                    if !searchModel.suggestions.isEmpty {
                        ForEach(searchModel.suggestions) { suggestion in
                            Button {
                                selectSuggestion(suggestion)
                            } label: {
                                VStack(alignment: .leading, spacing: Spacing.xxs) {
                                    Text(suggestion.title)
                                        .foregroundStyle(.primary)
                                    if !suggestion.subtitle.isEmpty {
                                        Text(suggestion.subtitle)
                                            .font(.footnote)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                            .buttonStyle(.plain)
                            .disabled(isResolvingSuggestion)
                        }
                    }
                } header: {
                    Text("Search First")
                } footer: {
                    Text("Catchbook uses Apple Maps search first when it can. If nothing fits, you can still save a private custom water.")
                }

                Section {
                    TextField("Water name", text: $name)
                        .textInputAutocapitalization(.words)
                        .submitLabel(.done)

                    Picker("Type", selection: $type) {
                        ForEach(WaterbodyType.allCases) { value in
                            Text(value.label).tag(value)
                        }
                    }

                    Button {
                        if selectedCoordinate == nil, let location = locationRecorder.lastLocation?.coordinate {
                            selectedCoordinate = location
                        }
                        showingCoordinatePicker = true
                    } label: {
                        Label(selectedCoordinate == nil ? "Choose on Map" : "Refine Map Pin", systemImage: "map")
                    }

                    if let pinnedCoordinate = selectedCoordinate {
                        LabeledContent("Canonical pin", value: coordinateText(for: pinnedCoordinate))
                        WaterbodyCoordinatePreview(
                            title: name.isEmpty ? "Pinned water" : name,
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
                    Text("Waterbody")
                } footer: {
                    Text("Private by default. Your saved coordinate becomes the waterbody's canonical map anchor when you choose one.")
                }
            }
            .navigationTitle("New Water")
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
                    .disabled(!WaterbodyFormLogic.canSave(name: name) || isResolvingSuggestion)
                }
            }
            .interactiveDismissDisabled(!name.isEmpty)
        }
        .presentationDetents([.medium, .large])
        .onAppear {
            locationRecorder.requestIfNeeded()
        }
        .onChange(of: name) { _, newValue in
            searchModel.updateQuery(newValue)
        }
        .sheet(isPresented: $showingCoordinatePicker) {
            WaterbodyCoordinatePickerSheet(
                title: name.isEmpty ? "Waterbody Pin" : name,
                initialCoordinate: selectedCoordinate ?? locationRecorder.lastLocation?.coordinate
            ) { coordinate in
                selectedCoordinate = coordinate
                hasCustomizedCoordinate = true
            }
        }
        .persistenceFailureAlert(message: $persistenceErrorMessage)
    }

    private func save() {
        let draft = WaterbodyFormLogic.draft(name: name, type: type, coordinate: selectedCoordinate)
        let waterbody = Waterbody(
            name: draft.name,
            type: draft.type,
            latitude: draft.latitude,
            longitude: draft.longitude
        )
        modelContext.insert(waterbody)
        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                onSaved?(waterbody)
                dismiss()
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }

    private func selectSuggestion(_ suggestion: WaterbodySearchSuggestion) {
        isResolvingSuggestion = true

        Task {
            let result = await searchModel.resolveCoordinate(for: suggestion)

            await MainActor.run {
                name = suggestion.title
                if let result {
                    selectedCoordinate = result
                }
                hasCustomizedCoordinate = true
                isResolvingSuggestion = false
            }
        }
    }

    private func coordinateText(for coordinate: CLLocationCoordinate2D) -> String {
        String(format: "%.4f, %.4f", coordinate.latitude, coordinate.longitude)
    }
}

private final class WaterbodySearchModel: NSObject, ObservableObject, MKLocalSearchCompleterDelegate {
    @Published private(set) var suggestions: [WaterbodySearchSuggestion] = []

    private let completer = MKLocalSearchCompleter()

    override init() {
        super.init()
        completer.delegate = self
    }

    func updateQuery(_ query: String) {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            suggestions = []
        } else {
            completer.queryFragment = trimmed
        }
    }

    func resolveCoordinate(for suggestion: WaterbodySearchSuggestion) async -> CLLocationCoordinate2D? {
        let request = MKLocalSearch.Request(completion: suggestion.completion)
        let search = MKLocalSearch(request: request)

        do {
            let response = try await search.start()
            return response.mapItems.first?.placemark.coordinate
        } catch {
            return nil
        }
    }

    nonisolated func completerDidUpdateResults(_ completer: MKLocalSearchCompleter) {
        let nextSuggestions = completer.results.prefix(5).map(WaterbodySearchSuggestion.init)
        Task { @MainActor in
            self.suggestions = nextSuggestions
        }
    }

    nonisolated func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) {
        Task { @MainActor in
            self.suggestions = []
        }
    }
}

private struct WaterbodySearchSuggestion: Identifiable {
    let id = UUID()
    let title: String
    let subtitle: String
    let completion: MKLocalSearchCompletion

    init(completion: MKLocalSearchCompletion) {
        self.title = completion.title
        self.subtitle = completion.subtitle
        self.completion = completion
    }
}

private struct WaterbodyCoordinatePreview: View {
    let title: String
    let coordinate: CLLocationCoordinate2D

    var body: some View {
        Map(
            position: .constant(
                .region(
                    MKCoordinateRegion(
                        center: coordinate,
                        span: MKCoordinateSpan(latitudeDelta: 0.08, longitudeDelta: 0.08)
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

private struct WaterbodyCoordinatePickerSheet: View {
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
                    span: MKCoordinateSpan(latitudeDelta: 0.2, longitudeDelta: 0.2)
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
                Text("Tap the map to place the canonical water pin.")
                    .font(.footnote)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(.ultraThinMaterial, in: Capsule())
                    .padding(.bottom, 20)
            }
            .navigationTitle("Choose Water Pin")
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
