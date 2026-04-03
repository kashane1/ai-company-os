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
                        Image(systemName: "plus")
                    }
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

private struct SpotDetailView: View {
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

    private var recentTripSummaries: [SpotRecentTripSummary] {
        SpotPresentationLogic.recentTripSummaries(trips: summary.recentTrips)
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

            // Recent Catches
            Section {
                if catchesHere.isEmpty {
                    SectionEmptyState(
                        icon: "fish",
                        title: "No catches here yet",
                        subtitle: "Your catch history at this spot will appear here."
                    )
                } else {
                    ForEach(catchesHere.prefix(5), id: \.id) { catchRecord in
                        CatchHistoryRow(catchRecord: catchRecord, includeTimestamp: true)
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
            }

            // Trip History
            if !summary.recentTrips.isEmpty {
                Section("Recent Trips") {
                    ForEach(Array(zip(summary.recentTrips, recentTripSummaries)), id: \.0.id) { trip, tripSummary in
                        NavigationLink {
                            TripDetailView(trip: trip)
                        } label: {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                HStack {
                                    Text(tripSummary.dateText)
                                        .font(.subheadline)
                                    Spacer()
                                    Text(tripSummary.outcomeText)
                                        .font(.caption.weight(.medium))
                                        .foregroundColor(
                                            tripSummary.isSkunked
                                                ? .secondary : .appAccent
                                        )
                                }
                                if let conditionSummary = tripSummary.conditionSummary {
                                    Text(conditionSummary)
                                        .font(.caption)
                                        .foregroundStyle(.tertiary)
                                }
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle(spot.title)
        .navigationBarTitleDisplayMode(.large)
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
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }
}
