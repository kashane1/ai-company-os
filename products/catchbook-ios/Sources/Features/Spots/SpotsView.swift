import MapKit
import SwiftData
import SwiftUI

struct SpotsView: View {
    @Query(sort: \Spot.createdAt) private var spots: [Spot]

    @State private var showingSpotForm = false
    @State private var showsMap = false
    @State private var mapCameraPosition = MapCameraPosition.region(SpotPresentationLogic.mapRegion(for: []))

    private var spotsWithCoordinates: [Spot] {
        SpotPresentationLogic.spotsWithCoordinates(from: spots)
    }

    var body: some View {
        NavigationStack {
            Group {
                if spots.isEmpty {
                    ContentUnavailableView {
                        Label("No Spots Saved", systemImage: "mappin.and.ellipse")
                    } description: {
                        Text("Save your private fishing spots to build recall over time.")
                    } actions: {
                        Button {
                            showingSpotForm = true
                        } label: {
                            Label("Add Spot", systemImage: "plus")
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.appAccent)
                    }
                } else if showsMap {
                    SpotsMapContent(
                        spots: spotsWithCoordinates,
                        position: $mapCameraPosition
                    )
                } else {
                    List {
                        ForEach(spots, id: \.id) { spot in
                            NavigationLink {
                                SpotDetailView(spot: spot)
                            } label: {
                                SpotRow(spot: spot)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Spots")
            .toolbar {
                if !spots.isEmpty {
                    ToolbarItem(placement: .topBarLeading) {
                        Button {
                            showsMap.toggle()
                            if showsMap {
                                refreshMapRegion()
                            }
                        } label: {
                            Label(
                                showsMap ? "Show list" : "Show map",
                                systemImage: showsMap ? "list.bullet" : "map"
                            )
                            .labelStyle(.iconOnly)
                        }
                        .accessibilityLabel(showsMap ? "Show list" : "Show map")
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showingSpotForm = true
                    } label: {
                        Label("Add spot", systemImage: "plus")
                            .labelStyle(.iconOnly)
                    }
                    .accessibilityLabel("Add spot")
                }
            }
        }
        .onAppear(perform: refreshMapRegion)
        .onChange(of: spots.map(\.id)) { _, _ in
            refreshMapRegion()
        }
        .onChange(of: spotsWithCoordinates.map(\.coordinateSummary)) { _, _ in
            refreshMapRegion()
        }
        .sheet(isPresented: $showingSpotForm) {
            NewSpotForm()
        }
    }

    private func refreshMapRegion() {
        mapCameraPosition = .region(SpotPresentationLogic.mapRegion(for: spotsWithCoordinates))
    }
}

// MARK: - Spot Row

private struct SpotRow: View {
    let spot: Spot
    private var rowDetails: SpotRowDetails {
        SpotPresentationLogic.rowDetails(for: spot)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xs) {
            Text(spot.title)
                .font(.subheadline.weight(.semibold))

            HStack(spacing: Spacing.md) {
                Label(rowDetails.waterbodyName, systemImage: "water.waves")
                if rowDetails.isPinned {
                    Label("Pinned", systemImage: "mappin")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if let notesPreview = rowDetails.notesPreview {
                Text(notesPreview)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, Spacing.xxs)
    }
}

private struct SpotMapAnnotation: View {
    let title: String
    let color: Color

    var body: some View {
        VStack(spacing: Spacing.xxs) {
            Text(title)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(Color.catchbookText)
                .padding(.horizontal, Spacing.sm)
                .padding(.vertical, Spacing.xs)
                .background(.thinMaterial, in: Capsule())

            Image(systemName: "mappin.circle.fill")
                .font(.title3)
                .foregroundStyle(color)
                .shadow(color: color.opacity(0.2), radius: 4, y: 2)
        }
    }
}

private struct SpotsMapContent: View {
    let spots: [Spot]
    @Binding var position: MapCameraPosition

    var body: some View {
        CatchbookMapView(
            items: spots,
            position: $position,
            coordinate: Self.coordinate(for:)
        ) { spot in
            NavigationLink {
                SpotDetailView(spot: spot)
            } label: {
                SpotMapAnnotation(
                    title: spot.title,
                    color: SpotPresentationLogic.waterbodyColor(for: spot.waterbody?.id)
                )
            }
            .buttonStyle(.plain)
        } overlay: {
            if spots.isEmpty {
                Text("No spots with saved coordinates yet.")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, Spacing.lg)
                    .padding(.vertical, Spacing.md)
                    .background(.regularMaterial, in: Capsule())
                    .allowsHitTesting(false)
            }
        }
    }

    private static func coordinate(for spot: Spot) -> CLLocationCoordinate2D? {
        guard let latitude = spot.latitude, let longitude = spot.longitude else {
            return nil
        }

        return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

// MARK: - Spot Detail

struct SpotDetailView: View {
    let spot: Spot

    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]

    private var summary: SpotRecallSummary {
        SpotRecallSummary.build(for: spot, trips: trips, catches: catches)
    }

    private var catchesHere: [CatchRecord] {
        SpotPresentationLogic.catchesHere(spotID: spot.id, catches: catches)
    }

    private var statSummary: SpotStatSummary {
        SpotPresentationLogic.statSummary(for: summary)
    }

    private var recallDetails: [SpotRecallDetailItem] {
        SpotPresentationLogic.recallDetails(for: summary)
    }

    private var recentTripSummaries: [SpotRecentTripSummary] {
        SpotPresentationLogic.recentTripSummaries(trips: summary.recentTrips, catches: catchesHere)
    }

    private var recentCatchSummaries: [SpotRecentCatchSummary] {
        SpotPresentationLogic.recentCatchSummaries(catches: catchesHere)
    }

    private var privateRecallCards: [DeterministicInsightCard] {
        SpotPresentationLogic.privateRecallCards(for: summary)
    }

    private var lastTimeHereCard: HomeReplayCard? {
        Self.lastTimeHereCard(for: spot, trips: trips, catches: catches)
    }

    private var catchMapMarkers: [CatchMapMarker] {
        TripBrowseLogic.catchMapMarkers(for: catchesHere)
    }

    var body: some View {
        List {
            // Overview
            Section("Overview") {
                LabeledContent("Water", value: spot.waterbody?.name ?? "Unknown")
                LabeledContent("Privacy", value: "Private")
                if spot.latitude != nil {
                    LabeledContent("Coordinates", value: spot.coordinateSummary)
                }
                if !spot.notes.isEmpty {
                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        Text("Notes")
                            .foregroundStyle(.secondary)
                        Text(spot.notes)
                    }
                }
            }

            // Recall Stats
            Section {
                HStack(spacing: Spacing.xl) {
                    SpotStatView(value: statSummary.tripCountText, label: "Trips")
                    SpotStatView(value: statSummary.catchCountText, label: "Catches")
                    SpotStatView(value: statSummary.productiveTripCountText, label: "Productive")
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, Spacing.sm)
                .listRowBackground(Color.clear)
            }

            if !catchMapMarkers.isEmpty {
                Section("Map") {
                    CatchMapSection(
                        markers: catchMapMarkers,
                        fallbackCoordinate: coordinateIfPresent(latitude: spot.latitude, longitude: spot.longitude),
                        footerText: "Catch markers only appear when the linked trip has a saved observed or fallback location."
                    )
                    .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                }
            }

            if let lastTimeHereCard {
                Section {
                    LastTimeHereCard(card: lastTimeHereCard)
                        .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                } header: {
                    Text("Last Time Here")
                }
            }

            Section {
                if recallDetails.isEmpty {
                    SectionEmptyState(
                        icon: "clock.badge.questionmark",
                        title: "Not enough history yet",
                        subtitle: "A few trips here will turn this into a useful private memory before your next outing."
                    )
                } else {
                    ForEach(recallDetails) { item in
                        VStack(alignment: .leading, spacing: Spacing.xxs) {
                            Text(item.title)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)
                            Text(item.value)
                                .font(.body.weight(.medium))
                            if let evidence = item.evidence {
                                Text(evidence)
                                    .font(.caption)
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .padding(.vertical, Spacing.xxs)
                    }
                }
            } header: {
                Text("Recall Snapshot")
            } footer: {
                Text("Every recall line comes from your own saved trips and catches.")
            }

            // Insight Cards
            if !privateRecallCards.isEmpty {
                Section("Private Recall") {
                    ForEach(privateRecallCards, id: \.id) { card in
                        DeterministicInsightCardView(card: card)
                            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                    }
                }
            } else {
                Section("Private Recall") {
                    SectionEmptyState(
                        icon: "sparkles",
                        title: "Not enough data yet",
                        subtitle: "Log a few trips here to unlock pattern cards."
                    )
                }
            }

            // Trip History
            if !summary.recentTrips.isEmpty {
                Section {
                    ForEach(Array(zip(summary.recentTrips, recentTripSummaries)), id: \.0.id) { trip, tripSummary in
                        NavigationLink {
                            TripDetailView(trip: trip)
                        } label: {
                            SpotRecentTripRow(summary: tripSummary)
                        }
                    }
                } header: {
                    HStack {
                        Text("Recent Trips")
                        Spacer()
                        Text("\(summary.tripCount)")
                            .font(.footnote.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                } footer: {
                    Text("Open a trip to move from spot recall into that trip's private memory.")
                }
            }

            // Recent Catches
            Section {
                if recentCatchSummaries.isEmpty {
                    SectionEmptyState(
                        icon: "fish",
                        title: "No catches here yet",
                        subtitle: "Your catch history at this spot will appear here."
                    )
                } else {
                    ForEach(recentCatchSummaries) { catchSummary in
                        if let tripID = catchSummary.tripID,
                           let trip = trips.first(where: { $0.id == tripID }) {
                            NavigationLink {
                                TripDetailView(trip: trip)
                            } label: {
                                SpotRecentCatchRow(summary: catchSummary)
                            }
                        } else {
                            SpotRecentCatchRow(summary: catchSummary)
                        }
                    }
                }
            } header: {
                HStack {
                    Text("Recent Catches")
                    Spacer()
                    Text("\(catchesHere.count)")
                        .font(.footnote.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            } footer: {
                if !recentCatchSummaries.isEmpty {
                    Text("Recent catches stay linked to the trips you logged here.")
                }
            }
        }
        .navigationTitle(spot.title)
        .navigationBarTitleDisplayMode(.large)
    }

    static func lastTimeHereCard(
        for spot: Spot,
        trips: [Trip],
        catches: [CatchRecord],
        calendar: Calendar = .current
    ) -> HomeReplayCard? {
        guard let trip = trips.first(where: { !$0.isActive && $0.spot?.id == spot.id }) else {
            return nil
        }

        let tripCatches = catches.filter { $0.trip?.id == trip.id }
        return HomeDashboardLogic.lastTimeHereCard(
            trip: trip,
            catches: tripCatches,
            calendar: calendar
        )
    }
}

private struct SpotRecentTripRow: View {
    let summary: SpotRecentTripSummary

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            HStack {
                Text(summary.dateText)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text(summary.catchText)
                    .font(.caption.weight(.semibold).monospacedDigit())
                    .foregroundColor(summary.isSkunked ? .secondary : .appAccent)
            }

            HStack(spacing: Spacing.sm) {
                Text(summary.outcomeText)
                if let topSpeciesText = summary.topSpeciesText {
                    Text("Top \(topSpeciesText)")
                }
                if let topLureText = summary.topLureText {
                    Text(topLureText)
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if let conditionSummary = summary.conditionSummary {
                Text(conditionSummary)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, Spacing.xxs)
    }
}

private struct SpotRecentCatchRow: View {
    let summary: SpotRecentCatchSummary

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            HStack {
                Text(summary.species)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text(summary.dateText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let tripTitle = summary.tripTitle {
                Text(tripTitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let lureOrBait = summary.lureOrBait {
                Text(lureOrBait)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let metricSummary = summary.metricSummary {
                Text(metricSummary)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.vertical, Spacing.xxs)
    }
}

// MARK: - Spot Stat

private struct SpotStatView: View {
    let value: String
    let label: String

    var body: some View {
        VStack(spacing: Spacing.xxs) {
            Text(value)
                .font(.title3.weight(.bold).monospacedDigit())
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
