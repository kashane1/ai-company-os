import MapKit
import PhotosUI
import SwiftData
import SwiftUI
import UIKit

struct TripsView: View {
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]
    @Query(sort: \Spot.createdAt) private var spots: [Spot]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]
    @Binding private var selectedTripID: UUID?
    @State private var path = NavigationPath()
    @State private var selectedWaterbodyID: UUID?
    @State private var speciesQuery = ""
    @State private var dateFilter: TripDateFilter = .all
    @State private var seasonFilter: TripSeasonFilter = .all
    @State private var selectedLure: String?
    @State private var showsMap = false
    @State private var selectedWaterbodySummary: WaterbodySummary?
    @State private var mapCameraPosition = MapCameraPosition.region(TripHistoryLogic.mapRegion(for: []))

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

    private var catchesByTripID: [UUID: [CatchRecord]] {
        Dictionary(grouping: catches) { $0.trip?.id }
            .reduce(into: [UUID: [CatchRecord]]()) { result, element in
                guard let tripID = element.key else { return }
                result[tripID] = element.value.sorted { $0.caughtAt > $1.caughtAt }
            }
    }

    private var historySections: [TripHistorySection] {
        TripHistoryLogic.sections(trips: filteredTrips, catches: catches)
    }

    private var waterbodySummaries: [WaterbodySummary] {
        TripHistoryLogic.waterbodySummaries(
            trips: filteredTrips,
            catches: catches,
            spots: spots,
            waterbodies: waterbodies
        )
    }

    private var listSnapshot: TripsListSnapshot {
        TripsListSnapshot(
            availableWaterbodies: availableWaterbodies,
            availableLures: availableLures,
            hasActiveFilters: hasActiveFilters,
            filteredTrips: filteredTrips,
            historySections: historySections,
            catchCountsByTripID: catchCountsByTripID,
            catchesByTripID: catchesByTripID
        )
    }

    var body: some View {
        NavigationStack(path: $path) {
            content
            .navigationTitle("Trips")
            .navigationDestination(for: UUID.self) { tripID in
                TripDestinationContent(trips: trips, tripID: tripID)
            }
            .toolbar {
                if !trips.isEmpty {
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
            }
            .onAppear {
                openPendingTripIfPossible()
                refreshMapRegion()
            }
            .onChange(of: availableLures) { _, _ in
                clearUnavailableSelectedLure()
            }
            .onChange(of: selectedTripID) { _, _ in
                openPendingTripIfPossible()
            }
            .onChange(of: trips.map(\.id)) { _, _ in
                openPendingTripIfPossible()
                refreshMapRegion()
            }
            .onChange(of: filteredTrips.map(\.id)) { _, _ in
                refreshMapRegion()
            }
            .onChange(of: spots.map(\.id)) { _, _ in
                refreshMapRegion()
            }
        }
        .sheet(item: $selectedWaterbodySummary) { summary in
            WaterbodySummarySheet(summary: summary)
                .presentationDetents([.medium, .large])
        }
    }

    @ViewBuilder
    private var content: some View {
        if trips.isEmpty {
            ContentUnavailableView {
                Label("No Trips Yet", systemImage: "water.waves")
            } description: {
                Text("Start a trip from the Log tab to begin building private fishing memory by water, spot, and season.")
            }
        } else if showsMap {
            TripsMapContent(
                summaries: waterbodySummaries,
                hasFilteredTrips: !filteredTrips.isEmpty,
                position: $mapCameraPosition,
                onSelect: { summary in
                    selectedWaterbodySummary = summary
                }
            )
        } else {
            TripsListContent(
                snapshot: listSnapshot,
                selectedWaterbodyID: $selectedWaterbodyID,
                dateFilter: $dateFilter,
                seasonFilter: $seasonFilter,
                speciesQuery: $speciesQuery,
                selectedLure: $selectedLure,
                onClearFilters: clearFilters
            )
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

    private func clearFilters() {
        selectedWaterbodyID = nil
        speciesQuery = ""
        dateFilter = .all
        seasonFilter = .all
        selectedLure = nil
    }

    private func refreshMapRegion() {
        mapCameraPosition = .region(TripHistoryLogic.mapRegion(for: waterbodySummaries))
    }
}

private struct TripDestinationContent: View {
    let trips: [Trip]
    let tripID: UUID

    var body: some View {
        if let trip = trips.first(where: { $0.id == tripID }) {
            TripDetailView(trip: trip)
        } else {
            ContentUnavailableView("Trip not found", systemImage: "exclamationmark.triangle")
        }
    }
}

private struct TripsListSnapshot {
    let availableWaterbodies: [Waterbody]
    let availableLures: [String]
    let hasActiveFilters: Bool
    let filteredTrips: [Trip]
    let historySections: [TripHistorySection]
    let catchCountsByTripID: [UUID: Int]
    let catchesByTripID: [UUID: [CatchRecord]]
}

private struct TripsListContent: View {
    let snapshot: TripsListSnapshot
    @Binding var selectedWaterbodyID: UUID?
    @Binding var dateFilter: TripDateFilter
    @Binding var seasonFilter: TripSeasonFilter
    @Binding var speciesQuery: String
    @Binding var selectedLure: String?
    let onClearFilters: () -> Void

    var body: some View {
        List {
            filtersSection
            tripContent
        }
    }

    private var filtersSection: some View {
        Section("Filters") {
            Picker("Water", selection: $selectedWaterbodyID) {
                Text("All waters").tag(Optional<UUID>.none)
                ForEach(snapshot.availableWaterbodies, id: \.id) { waterbody in
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
                ForEach(snapshot.availableLures, id: \.self) { lure in
                    Text(lure).tag(Optional(lure))
                }
            }
            .pickerStyle(.menu)

            if snapshot.hasActiveFilters {
                Button("Clear Filters", action: onClearFilters)
                    .font(.footnote.weight(.medium))
            }
        }
    }

    @ViewBuilder
    private var tripContent: some View {
        if snapshot.filteredTrips.isEmpty {
            Section {
                SectionEmptyState(
                    icon: "line.3.horizontal.decrease.circle",
                    title: "No trips match these filters",
                    subtitle: "Try a different water, species, lure, or season to bring your history back into view."
                )
            }
        } else {
            ForEach(snapshot.historySections) { section in
                Section {
                    ForEach(section.trips, id: \.id) { trip in
                        TripHistoryRow(
                            trip: trip,
                            catchCount: snapshot.catchCountsByTripID[trip.id, default: 0],
                            catches: snapshot.catchesByTripID[trip.id, default: []],
                            showSpotTitle: section.spot == nil
                        )
                    }
                } header: {
                    TripHistorySectionHeader(section: section)
                }
            }
        }
    }
}

private struct TripHistoryRow: View {
    let trip: Trip
    let catchCount: Int
    let catches: [CatchRecord]
    let showSpotTitle: Bool

    var body: some View {
        NavigationLink(value: trip.id) {
            TripRow(
                trip: trip,
                catchCount: catchCount,
                catches: catches,
                showSpotTitle: showSpotTitle
            )
        }
    }
}

private struct TripsMapContent: View {
    let summaries: [WaterbodySummary]
    let hasFilteredTrips: Bool
    @Binding var position: MapCameraPosition
    let onSelect: (WaterbodySummary) -> Void

    var body: some View {
        CatchbookMapView(
            items: summaries,
            position: $position,
            coordinate: \.coordinate
        ) { summary in
            Button {
                onSelect(summary)
            } label: {
                WaterbodyMapAnnotation(summary: summary)
            }
            .buttonStyle(.plain)
        } overlay: {
            if !hasFilteredTrips {
                Text("No trips match these filters.")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, Spacing.lg)
                    .padding(.vertical, Spacing.md)
                    .background(.regularMaterial, in: Capsule())
                    .allowsHitTesting(false)
            } else if summaries.isEmpty {
                Text("No waters with saved coordinates yet.")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, Spacing.lg)
                    .padding(.vertical, Spacing.md)
                    .background(.regularMaterial, in: Capsule())
                    .allowsHitTesting(false)
            }
        }
    }
}

private struct WaterbodyMapAnnotation: View {
    let summary: WaterbodySummary

    private var tripCountText: String {
        "\(summary.tripCount) \(summary.tripCount == 1 ? "trip" : "trips")"
    }

    var body: some View {
        Text("\(summary.waterbodyName) · \(tripCountText)")
            .font(.caption.weight(.semibold))
            .foregroundStyle(.white)
            .padding(.horizontal, Spacing.md)
            .padding(.vertical, Spacing.sm)
            .background(
                SpotPresentationLogic.waterbodyColor(for: summary.waterbodyID),
                in: Capsule()
            )
            .shadow(color: .black.opacity(0.12), radius: 4, y: 2)
    }
}

private struct WaterbodySummarySheet: View {
    let summary: WaterbodySummary

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(alignment: .leading, spacing: Spacing.md) {
                        Text(summary.waterbodyName)
                            .font(.title2.weight(.bold))

                        AppBadge(text: summary.waterbodyType.label)

                        HStack(spacing: Spacing.lg) {
                            StatCapsule(value: "\(summary.tripCount)", label: summary.tripCount == 1 ? "Trip" : "Trips", icon: "water.waves")
                            StatCapsule(value: "\(summary.catchCount)", label: summary.catchCount == 1 ? "Catch" : "Catches", icon: "fish")
                            StatCapsule(value: "\(summary.spotCount)", label: summary.spotCount == 1 ? "Spot" : "Spots", icon: "mappin")
                        }

                        Text(lastTripText)
                            .font(.footnote)
                            .foregroundStyle(.secondary)

                        Text(summary.coordinateSource.detailText)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, Spacing.sm)
                }

                Section("Spots") {
                    if summary.spots.isEmpty {
                        SectionEmptyState(
                            icon: "mappin.slash",
                            title: "No saved spots yet",
                            subtitle: "Trips here can still build memory before you pin exact spots."
                        )
                    } else {
                        ForEach(summary.spots, id: \.id) { spot in
                            NavigationLink {
                                SpotDetailView(spot: spot)
                            } label: {
                                Text(spot.title)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Water Summary")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private var lastTripText: String {
        guard let lastTripDate = summary.lastTripDate else {
            return "No trips yet"
        }

        return "Last trip: \(AppFormatters.tripDate.string(from: lastTripDate))"
    }
}

// MARK: - Trip Row

private struct TripRow: View {
    let trip: Trip
    let catchCount: Int
    let catches: [CatchRecord]
    let showSpotTitle: Bool

    private var rowSummary: TripRowSummary {
        TripPresentationLogic.tripRowSummary(trip: trip, catchCount: catchCount)
    }

    private var memoryRecap: TripMemoryRecap {
        TripPresentationLogic.tripMemoryRecap(trip: trip, catches: catches)
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

                if let waterbodyName = trip.waterbody?.name {
                    Label(waterbodyName, systemImage: "water.waves")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            Text(memoryRecap.primaryLine)
                .font(.caption.weight(.medium))
                .foregroundStyle(rowSummary.showsSkunkedStyle ? .secondary : .primary)

            if let secondaryLine = memoryRecap.secondaryLine {
                Text(secondaryLine)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            if showSpotTitle, let spot = rowSummary.spotTitle {
                Label(spot, systemImage: "mappin")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.vertical, Spacing.xs)
    }
}

private struct TripHistorySectionHeader: View {
    let section: TripHistorySection

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            if let spot = section.spot {
                NavigationLink {
                    SpotDetailView(spot: spot)
                } label: {
                    HStack(spacing: Spacing.xs) {
                        Label(section.title, systemImage: "mappin.and.ellipse")
                            .font(.footnote.weight(.semibold))
                        Spacer()
                        Image(systemName: "arrow.up.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.tertiary)
                    }
                }
                .buttonStyle(.plain)
            } else {
                Label(section.title, systemImage: "mappin.slash")
                    .font(.footnote.weight(.semibold))
            }

            if let subtitle = section.subtitle {
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .textCase(nil)
        .padding(.top, Spacing.xxs)
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
    @Environment(\.modelContext) private var modelContext

    let trip: Trip

    @Query(sort: \Trip.startAt, order: .reverse) private var allTrips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var allCatches: [CatchRecord]
    @State private var activeSheet: TripDetailSheet?
    @State private var shareImage: UIImage?
    @State private var showingShareSheet = false

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

    private var recallSummary: TripDetailRecallSummary {
        TripPresentationLogic.tripDetailRecallSummary(trip: trip, catches: catches)
    }

    private var recentSpotTrips: [TripSpotReplaySummary] {
        TripPresentationLogic.recentSpotTripSummaries(
            currentTrip: trip,
            allTrips: allTrips,
            catches: allCatches
        )
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

            Section {
                TripDetailRecallCard(summary: recallSummary)
                    .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
            } header: {
                Text("Trip Recall")
            } footer: {
                Text("This recap only uses the trip you saved here.")
            }

            if let spot = trip.spot {
                Section {
                    NavigationLink {
                        SpotDetailView(spot: spot)
                    } label: {
                        LabeledContent {
                            Image(systemName: "arrow.up.right")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.tertiary)
                        } label: {
                            VStack(alignment: .leading, spacing: Spacing.xxs) {
                                Text("Open recall for \(spot.title)")
                                Text("Jump from this trip into your saved spot memory.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }

                    if recentSpotTrips.isEmpty {
                        Text("This is your only saved trip at \(spot.title) so far.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(recentSpotTrips) { relatedTrip in
                            NavigationLink {
                                TripDetailView(trip: relatedTrip.trip)
                            } label: {
                                SpotReplayRow(summary: relatedTrip)
                            }
                        }
                    }
                } header: {
                    Text("Spot Memory")
                } footer: {
                    if !recentSpotTrips.isEmpty {
                        Text("Recent trips at this same spot.")
                    }
                }
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
                if let spot = trip.spot {
                    NavigationLink {
                        SpotDetailView(spot: spot)
                    } label: {
                        Label("Open spot detail", systemImage: "mappin.and.ellipse")
                    }
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
                    if let locationSummaryLine = snapshot.locationSummaryLine {
                        LabeledContent("Location", value: locationSummaryLine)
                    } else if let placeSummary = snapshot.placeSummary {
                        LabeledContent("Place", value: placeSummary)
                    }
                    if let timeWindowSummary = snapshot.timeWindowSummary {
                        LabeledContent("Window", value: timeWindowSummary)
                    }
                    if let lightLevelSummary = snapshot.lightLevelSummary {
                        LabeledContent("Light", value: lightLevelSummary)
                    }
                    LabeledContent("Weather", value: snapshot.weatherLine)
                    if snapshot.weatherSummary != nil {
                        WeatherAttributionView()
                    }
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
                        .contextMenu {
                            Button {
                                shareCatch(catchRecord)
                            } label: {
                                Label("Share Catch", systemImage: "square.and.arrow.up")
                            }
                        }
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            Button {
                                shareCatch(catchRecord)
                            } label: {
                                Label("Share Catch", systemImage: "square.and.arrow.up")
                            }
                            .tint(.appAccent)
                        }
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
        .sheet(isPresented: $showingShareSheet) {
            if let shareImage {
                ActivityShareSheet(activityItems: [shareImage])
            }
        }
    }

    private func shareCatch(_ catchRecord: CatchRecord) {
        guard let image = CatchSharing.makeImage(for: catchRecord, in: modelContext) else { return }
        shareImage = image
        showingShareSheet = true
    }
}

private struct TripDetailRecallCard: View {
    let summary: TripDetailRecallSummary

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Text(summary.headline)
                .font(.headline)

            if let supportingText = summary.supportingText {
                Text(supportingText)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            VStack(spacing: Spacing.sm) {
                ForEach(summary.items) { item in
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
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .appCard(prominent: true)
    }
}

private struct SpotReplayRow: View {
    let summary: TripSpotReplaySummary

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xxs) {
            HStack {
                Text(summary.trip.title)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text(summary.catchText)
                    .font(.caption.weight(.semibold).monospacedDigit())
                    .foregroundColor(summary.isSkunked ? .secondary : .appAccent)
            }

            Text(summary.dateText)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, Spacing.xxs)
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
    @State private var persistenceErrorMessage: String?
    @State private var showingClearLocationConfirmation = false
    @FocusState private var isTextInputFocused: Bool

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

    private var conditionsFooterText: String {
        "Descriptive notes only. Temperature and coordinates are captured automatically and can't be edited by hand."
    }

    private var recordedLocationFooterText: String {
        if let confidenceLabel = trip.locationConfidenceLabel {
            return "\(confidenceLabel) reflects whether this trip is using an observed outing coordinate or a saved-place fallback. Clearing removes the recorded coordinate and temperature from this trip permanently."
        }

        return "Captured when the trip started. Clearing removes the coordinates and temperature from this trip permanently."
    }

    @ViewBuilder
    private var whereSection: some View {
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
    }

    @ViewBuilder
    private var tripSection: some View {
        Section("Trip") {
            DatePicker("Started", selection: $startAt)
            Toggle("Trip is still active", isOn: $isTripActive)
            if !isTripActive {
                DatePicker("Ended", selection: $endAt, in: startAt...)
            }
            TextField("Target species, separated by commas", text: $targetSpecies)
                .textInputAutocapitalization(.words)
                .focused($isTextInputFocused)
            TextField("Notes", text: $notes, axis: .vertical)
                .lineLimit(2...4)
                .focused($isTextInputFocused)
        }
    }

    @ViewBuilder
    private func conditionsSection(snapshot: ConditionSnapshot) -> some View {
        Section {
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
        } header: {
            Text("Conditions")
        } footer: {
            Text(conditionsFooterText)
        }

        if snapshot.latitude != nil || snapshot.longitude != nil || snapshot.temperatureC != nil {
            recordedLocationSection(snapshot: snapshot)
        }
    }

    @ViewBuilder
    private func recordedLocationSection(snapshot: ConditionSnapshot) -> some View {
        Section {
            if let coordinateSummary = snapshot.coordinateSummary {
                LabeledContent("Coordinates", value: coordinateSummary)
            }
            if let celsius = snapshot.temperatureC {
                LabeledContent("Temperature", value: temperatureText(celsius: celsius))
            }
            Button("Clear Recorded Location", role: .destructive) {
                showingClearLocationConfirmation = true
            }
        } header: {
            Text("Recorded Location")
        } footer: {
            Text(recordedLocationFooterText)
        }
    }

    private func temperatureText(celsius: Double) -> String {
        let measurement = Measurement<UnitTemperature>(value: celsius, unit: .celsius)
        let formatter = MeasurementFormatter()
        formatter.unitOptions = [.naturalScale, .providedUnit]
        formatter.numberFormatter.maximumFractionDigits = 0
        return formatter.string(from: measurement)
    }

    var body: some View {
        NavigationStack {
            Form {
                whereSection
                tripSection

                if let snapshot = trip.conditionSnapshot {
                    conditionsSection(snapshot: snapshot)
                }
            }
            .navigationTitle("Edit Trip")
            .navigationBarTitleDisplayMode(.inline)
            .scrollDismissesKeyboard(.interactively)
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
                KeyboardDoneToolbar { isTextInputFocused = false }
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
        .persistenceFailureAlert(message: $persistenceErrorMessage)
        .confirmationDialog(
            "Clear recorded location?",
            isPresented: $showingClearLocationConfirmation,
            titleVisibility: .visible
        ) {
            Button("Clear Location", role: .destructive) {
                clearRecordedLocation()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This permanently removes the coordinates and temperature from this trip.")
        }
    }

    private func clearRecordedLocation() {
        guard let snapshot = trip.conditionSnapshot else { return }
        snapshot.latitude = nil
        snapshot.longitude = nil
        snapshot.temperatureC = nil
        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {},
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
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
                precipitationSummary: precipitationSummary
            )
            snapshot.placeSummary = draft.placeSummary
            snapshot.timeWindowSummary = draft.timeWindowSummary
            snapshot.lightLevelSummary = draft.lightLevelSummary
            snapshot.weatherSummary = draft.weatherSummary
            snapshot.windSummary = draft.windSummary
            snapshot.cloudCoverSummary = draft.cloudCoverSummary
            snapshot.precipitationSummary = draft.precipitationSummary
        }

        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                dismiss()
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
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
    @State private var persistenceErrorMessage: String?
    @FocusState private var isTextInputFocused: Bool

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
                .focused($isTextInputFocused)
            DatePicker("Caught at", selection: $caughtAt)
            TextField("Lure or bait", text: $lureOrBait)
                .textInputAutocapitalization(.words)
                .focused($isTextInputFocused)
            TextField("Method", text: $method)
                .textInputAutocapitalization(.words)
                .focused($isTextInputFocused)
            TextField("Weight (kg)", text: $weight)
                .keyboardType(.decimalPad)
                .focused($isTextInputFocused)
            TextField("Length (cm)", text: $length)
                .keyboardType(.decimalPad)
                .focused($isTextInputFocused)
            TextField("Note", text: $note, axis: .vertical)
                .lineLimit(2...4)
                .focused($isTextInputFocused)
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
            .scrollDismissesKeyboard(.interactively)
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
                KeyboardDoneToolbar { isTextInputFocused = false }
            }
        }
        .presentationDetents([.large])
        .confirmationDialog(
            "Delete this catch?",
            isPresented: $showingDeleteConfirmation,
            titleVisibility: .visible
        ) {
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
        .persistenceFailureAlert(message: $persistenceErrorMessage)
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

        persistCatchChanges {
            dismiss()
        }
    }

    private func deleteCatch() {
        guard let catchRecord else { return }
        modelContext.delete(catchRecord)
        persistCatchChanges {
            dismiss()
        }
    }

    private func persistCatchChanges(onSuccess: @escaping () -> Void) {
        PersistenceWriteCoordinator.perform(
            commit: {
                try syncTripOutcomeAndPersonalBests(for: trip, in: modelContext)
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: onSuccess,
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }

    private func shareCatch() {
        guard let catchRecord else { return }
        guard let image = CatchSharing.makeImage(for: catchRecord, in: modelContext) else { return }
        shareImage = image
        showingShareSheet = true
    }
}

private enum CatchSharing {
    @MainActor
    static func makeImage(for catchRecord: CatchRecord, in modelContext: ModelContext) -> UIImage? {
        let catches = (try? modelContext.fetch(FetchDescriptor<CatchRecord>())) ?? []
        let personalBests = (try? modelContext.fetch(FetchDescriptor<PersonalBest>())) ?? []

        return CatchShareCardRenderer.renderImage(
            for: catchRecord,
            catches: catches,
            personalBests: personalBests
        )
    }
}

struct CatchShareCardContent {
    let badgeText: String?
    let speciesName: String
    let dateText: String
    let lureOrBaitText: String?
    let weightText: String?
    let lengthText: String?
    let photoData: Data?
}

enum CatchShareCardBadge: Equatable {
    case longest(species: String)
    case heaviest(species: String)
    case first(species: String)

    var text: String {
        switch self {
        case let .longest(species):
            return "Longest \(species)"
        case let .heaviest(species):
            return "Heaviest \(species)"
        case let .first(species):
            return "First \(species)"
        }
    }
}

enum CatchShareCardLogic {
    private static let coarseDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        return formatter
    }()

    static func badge(
        for catchRecord: CatchRecord,
        catches: [CatchRecord],
        personalBests: [PersonalBest]
    ) -> CatchShareCardBadge? {
        let species = normalizedSpecies(catchRecord.species)
        guard !species.isEmpty else { return nil }

        if personalBests.contains(where: { normalizedSpecies($0.species) == species && $0.longestCatchID == catchRecord.id }) {
            return .longest(species: catchRecord.speciesDisplayName)
        }

        if personalBests.contains(where: { normalizedSpecies($0.species) == species && $0.heaviestCatchID == catchRecord.id }) {
            return .heaviest(species: catchRecord.speciesDisplayName)
        }

        let speciesCatches = catches.filter { normalizedSpecies($0.species) == species }
        guard let firstCatch = speciesCatches.min(by: catchOrdering(_:_:)), firstCatch.id == catchRecord.id else {
            return nil
        }

        return .first(species: catchRecord.speciesDisplayName)
    }

    static func content(
        for catchRecord: CatchRecord,
        catches: [CatchRecord] = [],
        personalBests: [PersonalBest] = []
    ) -> CatchShareCardContent {
        CatchShareCardContent(
            badgeText: badge(for: catchRecord, catches: catches, personalBests: personalBests)?.text,
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

    private static func normalizedSpecies(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func catchOrdering(_ lhs: CatchRecord, _ rhs: CatchRecord) -> Bool {
        if lhs.caughtAt != rhs.caughtAt {
            return lhs.caughtAt < rhs.caughtAt
        }

        return lhs.id.uuidString < rhs.id.uuidString
    }
}

enum CatchShareCardRenderer {
    @MainActor
    static func renderImage(
        for catchRecord: CatchRecord,
        catches: [CatchRecord] = [],
        personalBests: [PersonalBest] = [],
        scale: CGFloat = 3
    ) -> UIImage? {
        let renderer = ImageRenderer(
            content: CatchShareCardView(
                content: CatchShareCardLogic.content(
                    for: catchRecord,
                    catches: catches,
                    personalBests: personalBests
                )
            )
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
                colors: [Color.catchbookSky.opacity(0.35), Color.catchbookAqua.opacity(0.18), Color(.systemBackground)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            VStack(alignment: .leading, spacing: 32) {
                Text(content.dateText)
                    .font(.system(size: 42, weight: .medium, design: .rounded))
                    .foregroundStyle(.secondary)

                if let badgeText = content.badgeText {
                    Text(badgeText.uppercased())
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 24)
                        .padding(.vertical, 12)
                        .background(Color.appAccent, in: Capsule())
                }

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
                                .lineLimit(1)
                                .minimumScaleFactor(0.7)
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

private func syncTripOutcomeAndPersonalBests(for trip: Trip, in context: ModelContext) throws {
    let catches = try context.fetch(FetchDescriptor<CatchRecord>())
        .filter { $0.trip?.id == trip.id }

    trip.outcomeRawValue = TripEditingLogic.tripOutcome(endAt: trip.endAt, catchCount: catches.count).rawValue
    try PersonalBestService.rebuild(in: context)
}
