import SwiftData
import SwiftUI

struct SpotsView: View {
    @Query(sort: \Spot.createdAt) private var spots: [Spot]

    @State private var showingSpotForm = false

    var body: some View {
        NavigationStack {
            List {
                if spots.isEmpty {
                    Text("Saved spots will appear here for private recall.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(spots, id: \.id) { spot in
                        NavigationLink {
                            SpotDetailView(spot: spot)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(spot.title)
                                    .font(.headline)
                                Text(spot.waterbody?.name ?? "Unknown waterbody")
                                    .foregroundStyle(.secondary)
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
                        Label("Add Spot", systemImage: "plus")
                    }
                }
            }
        }
        .sheet(isPresented: $showingSpotForm) {
            NewSpotForm()
        }
    }
}

private struct SpotDetailView: View {
    let spot: Spot

    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]

    private var summary: SpotRecallSummary {
        SpotRecallSummary.build(for: spot, trips: trips, catches: catches)
    }

    var body: some View {
        List {
            Section("Overview") {
                LabeledContent("Waterbody", value: spot.waterbody?.name ?? "Unknown")
                LabeledContent("Privacy", value: "Private")
                LabeledContent("Coordinates", value: spot.coordinateSummary)
                if !spot.notes.isEmpty {
                    Text(spot.notes)
                        .foregroundStyle(.secondary)
                }
            }

            Section("Private Recall") {
                LabeledContent("Trips here", value: "\(summary.recentTrips.count)")
                LabeledContent("Catches here", value: "\(summary.catchCount)")
                if summary.cards.isEmpty {
                    Text("Log a few trips here to unlock private recall cards.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(summary.cards, id: \.id) { card in
                        DeterministicInsightCardView(card: card)
                    }
                }
            }

            Section("Last Trips Here") {
                if summary.recentTrips.isEmpty {
                    Text("No trips logged at this spot yet.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(summary.recentTrips, id: \.id) { trip in
                        NavigationLink {
                            TripDetailView(trip: trip)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(AppFormatters.tripDate.string(from: trip.startAt))
                                Text(trip.outcomeRawValue.capitalized)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle(spot.title)
    }
}
