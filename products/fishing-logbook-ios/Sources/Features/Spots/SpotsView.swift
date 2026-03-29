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

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xs) {
            Text(spot.title)
                .font(.subheadline.weight(.semibold))

            HStack(spacing: Spacing.md) {
                Label(spot.waterbody?.name ?? "Unknown water", systemImage: "water.waves")
                if spot.latitude != nil {
                    Label("Pinned", systemImage: "mappin")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if !spot.notes.isEmpty {
                Text(spot.notes)
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
        catches.filter { $0.trip?.spot?.id == spot.id }
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
                    SpotStatView(value: "\(summary.recentTrips.count)", label: "Trips")
                    SpotStatView(value: "\(summary.catchCount)", label: "Catches")
                    SpotStatView(
                        value: summary.successfulTripCount > 0 ? "\(summary.successfulTripCount)" : "0",
                        label: "Productive"
                    )
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, Spacing.sm)
                .listRowBackground(Color.clear)
            }

            // Insight Cards
            if !summary.cards.isEmpty {
                Section("Private Recall") {
                    ForEach(summary.cards, id: \.id) { card in
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
                    ForEach(summary.recentTrips, id: \.id) { (trip: Trip) in
                        NavigationLink {
                            TripDetailView(trip: trip)
                        } label: {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                HStack {
                                    Text(AppFormatters.tripDate.string(from: trip.startAt))
                                        .font(.subheadline)
                                    Spacer()
                                    Text(trip.outcomeRawValue.capitalized)
                                        .font(.caption.weight(.medium))
                                        .foregroundColor(
                                            trip.outcomeRawValue == TripOutcome.skunked.rawValue
                                                ? .secondary : .appAccent
                                        )
                                }
                                if let snapshot = trip.conditionSnapshot {
                                    Text(snapshot.displaySummary)
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
