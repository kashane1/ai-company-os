import CoreLocation
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
    // selectedWaterbodyID is silent state — it's set by background auto-detection
    // (or by context preselection) so the trip gets tagged with a waterbody, but
    // the user never sees or picks it. Kept here so startTrip() can attach it
    // to the Trip model on creation.
    @State private var selectedWaterbodyID: UUID?
    @State private var selectedSpotID: UUID?
    @State private var targetSpecies = ""
    @State private var tripNotes = ""
    @State private var showingOptionalDetails = LogFeatureLogic.startTripOptionalDetailsInitiallyExpanded
    @State private var showingSpotForm = false
    @State private var persistenceErrorMessage: String?
    @State private var showingActiveTripAlert = false
    @AppStorage("tripStart.lastDetection") private var lastDetectionJSON: String = ""
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
                Section {
                    Picker("Spot", selection: $selectedSpotID) {
                        Text("No specific spot").tag(Optional<UUID>.none)
                        ForEach(spots, id: \.id) { spot in
                            Text(spot.title).tag(Optional(spot.id))
                        }
                    }

                    if let lastTimeHereCard {
                        LastTimeHereCard(card: lastTimeHereCard)
                            .listRowInsets(EdgeInsets(top: 4, leading: 0, bottom: 4, trailing: 0))
                    }

                    Button {
                        showingSpotForm = true
                    } label: {
                        Label("New Spot", systemImage: "plus")
                            .font(.footnote)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .listRowSeparator(.hidden, edges: .bottom)
                } header: {
                    Text("Where")
                } footer: {
                    Text("Spot is optional. Start the trip whenever you're ready — we'll tag whatever we can from your location.")
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
                    .accessibilityIdentifier("startTrip.button")
                    .listRowSeparator(.hidden)
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
            // Permission prompt is a side-effect, not async — keep in onAppear
            // so it fires on every sheet appearance.
            locationRecorder.requestIfNeeded()
        }
        .task {
            // .task { } instead of Task { } in .onAppear so SwiftUI cancels
            // the prefill automatically if the user dismisses mid-flight.
            // Handles context preselection synchronously, then falls through
            // to location-based prefill only if neither is set.
            if let spot = context.preselectedSpot {
                selectedSpotID = spot.id
                selectedWaterbodyID = spot.waterbody?.id
                return
            }
            if let waterbody = context.preselectedWaterbody {
                selectedWaterbodyID = waterbody.id
                return
            }
            await prefillWaterbodyFromLocation()
        }
        .sheet(isPresented: $showingSpotForm) {
            NewSpotForm { spot in
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

    // MARK: - Waterbody Prefill

    @MainActor
    private func prefillWaterbodyFromLocation() async {
        guard selectedWaterbodyID == nil else { return }
        guard let coordinate = locationRecorder.lastLocation?.coordinate else { return }

        // Cache gate: skip the network call if a recent detection is still
        // valid within 500m / 24h. Kills ~80% of trip-start network calls
        // for users who regularly fish the same waters.
        if let cached = TripStartDetectionCache.load(from: lastDetectionJSON),
           cached.isFresh(for: coordinate) {
            applyDetected(
                WaterbodyAutoDetectionService.Detected(
                    name: cached.name,
                    type: WaterbodyType(rawValue: cached.typeRawValue) ?? .lake,
                    coordinate: CLLocationCoordinate2D(latitude: cached.latitude, longitude: cached.longitude)
                )
            )
            return
        }

        guard let detected = await WaterbodyAutoDetectionService.detect(at: coordinate) else {
            return
        }

        // Late result after user picked something or dismissed? Drop it.
        guard !Task.isCancelled, selectedWaterbodyID == nil else { return }

        applyDetected(detected)

        // Update cache for next trip start.
        lastDetectionJSON = TripStartDetectionCache(
            name: detected.name,
            typeRawValue: detected.type.rawValue,
            latitude: detected.coordinate.latitude,
            longitude: detected.coordinate.longitude,
            timestamp: Date()
        ).toJSON() ?? ""
    }

    @MainActor
    private func applyDetected(_ detected: WaterbodyAutoDetectionService.Detected) {
        var resolvedID: UUID?
        PersistenceWriteCoordinator.perform(
            commit: {
                let waterbody = try WaterbodyAutoDetectionService.findOrCreate(detected, in: modelContext)
                resolvedID = waterbody.id
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                if let resolvedID {
                    selectedWaterbodyID = resolvedID
                }
            },
            onFailure: { _ in
                // Silent: prefill is non-critical; the form still works.
            }
        )
    }
}

// MARK: - Detection Cache

/// Lightweight cached last-detection result stored in @AppStorage as JSON.
/// Guards TripStartSheet's prefill path from hitting the network on every
/// appearance when the user is fishing the same spot repeatedly.
private struct TripStartDetectionCache: Codable {
    let name: String
    let typeRawValue: String
    let latitude: Double
    let longitude: Double
    let timestamp: Date

    static let freshnessWindow: TimeInterval = 60 * 60 * 24 // 24 hours
    static let freshnessRadiusMeters: Double = 500

    static func load(from json: String) -> TripStartDetectionCache? {
        guard !json.isEmpty, let data = json.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(TripStartDetectionCache.self, from: data)
    }

    func toJSON() -> String? {
        guard let data = try? JSONEncoder().encode(self) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func isFresh(for coordinate: CLLocationCoordinate2D) -> Bool {
        let age = Date().timeIntervalSince(timestamp)
        guard age >= 0, age < Self.freshnessWindow else { return false }
        let cached = CLLocation(latitude: latitude, longitude: longitude)
        let current = CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)
        return cached.distance(from: current) <= Self.freshnessRadiusMeters
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
