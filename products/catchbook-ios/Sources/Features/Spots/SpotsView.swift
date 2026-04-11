import SwiftData
import SwiftUI

struct SpotsView: View {
    @Query(sort: \Spot.createdAt) private var spots: [Spot]

    @State private var showingSpotForm = false

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
        .sheet(isPresented: $showingSpotForm) {
            NewSpotForm()
        }
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
