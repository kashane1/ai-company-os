import SwiftData
import SwiftUI

struct TripStartSheet: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss

    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]
    @Query(sort: \Spot.createdAt) private var spots: [Spot]
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
    @State private var showingActiveTripAlert = false
    @FocusState private var isTextInputFocused: Bool

    let context: TripStartContext

    private var conditionPreview: ConditionCapturePreview {
        ConditionCaptureService.preview(
            waterbody: selectedWaterbody,
            spot: selectedSpot,
            location: locationRecorder.lastLocation
        )
    }

    private var activeTrip: Trip? {
        trips.first(where: \.isActive)
    }

    private var lastTimeHereCard: HomeReplayCard? {
        guard let selectedSpotID else { return nil }
        guard let trip = trips.first(where: { !$0.isActive && $0.spot?.id == selectedSpotID }) else {
            return nil
        }
        let tripCatches = catches.filter { $0.trip?.id == trip.id }
        return HomeDashboardLogic.lastTimeHereCard(
            trip: trip,
            catches: tripCatches
        )
    }

    var body: some View {
        NavigationStack {
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
                            if activeTrip != nil {
                                showingActiveTripAlert = true
                            } else {
                                startTrip()
                            }
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
            .navigationTitle("Start Trip")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .scrollDismissesKeyboard(.interactively)
            .toolbar {
                KeyboardDoneToolbar { isTextInputFocused = false }
            }
        }
        .onAppear {
            locationRecorder.requestIfNeeded()
            // Pre-select spot/waterbody from context (e.g., "Start Trip Here" from Spots)
            if let spot = context.preselectedSpot {
                selectedSpotID = spot.id
                selectedWaterbodyID = spot.waterbody?.id
            } else if let waterbody = context.preselectedWaterbody {
                selectedWaterbodyID = waterbody.id
            }
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
        .alert("Trip Already Active", isPresented: $showingActiveTripAlert) {
            Button("End & Start New", role: .destructive) {
                endActiveTripAndStartNew()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            if let activeTrip {
                Text("You have an active trip at \(activeTrip.title). End it and start a new one?")
            } else {
                Text("You have an active trip. End it and start a new one?")
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
                let location = locationRecorder.lastLocation
                Task {
                    await ConditionCaptureService.enrichWithWeather(snapshot, location: location)
                    try? modelContext.save()
                }
                dismiss()
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }

    private func endActiveTripAndStartNew() {
        guard let activeTrip else { return }
        let tripCatches = catches.filter { $0.trip?.id == activeTrip.id }
        activeTrip.endAt = .now
        activeTrip.outcomeRawValue = LogFeatureLogic.endTripOutcome(catchCount: tripCatches.count).rawValue
        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                startTrip()
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }
}

// MARK: - Condition Preview Row

struct ConditionPreviewRow: View {
    let preview: ConditionCapturePreview

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Label(preview.snapshot.statusLine, systemImage: preview.isLocationReady ? "checkmark.circle.fill" : "location.slash")
                .font(.subheadline)
                .foregroundStyle(preview.isLocationReady ? .appAccent : .secondary)

            if let mergedLocationLine = preview.snapshot.locationSummaryLine {
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
}
