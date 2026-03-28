import SwiftData
import SwiftUI

struct HomeView: View {
    @Binding var selectedTab: AppTab

    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]
    @Query(sort: \PersonalBest.updatedAt, order: .reverse) private var personalBests: [PersonalBest]

    private var activeTrip: Trip? {
        trips.first(where: \.isActive)
    }

    private var latestCompletedTrip: Trip? {
        trips.first(where: { !$0.isActive })
    }

    private var latestSpotSummary: SpotRecallSummary? {
        guard let latestSpot = latestCompletedTrip?.spot else { return nil }
        return SpotRecallSummary.build(for: latestSpot, trips: trips, catches: catches)
    }

    var body: some View {
        NavigationStack {
            List {
                if let activeTrip {
                    Section("Trip in Progress") {
                        ActiveTripHero(activeTrip: activeTrip) {
                            selectedTab = .log
                        }
                    }
                } else {
                    Section {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Ready for the next trip")
                                .font(.headline)
                            Text("Start a trip quickly, keep it private, and let the app remember what worked.")
                                .foregroundStyle(.secondary)
                            Button("Start a trip") {
                                selectedTab = .log
                            }
                            .buttonStyle(.borderedProminent)
                        }
                    }
                }

                if let latestCompletedTrip {
                    Section("Last Trip") {
                        NavigationLink {
                            TripDetailView(trip: latestCompletedTrip)
                        } label: {
                            VStack(alignment: .leading, spacing: 6) {
                                Text(latestCompletedTrip.title)
                                    .font(.headline)
                                Text(AppFormatters.tripDate.string(from: latestCompletedTrip.startAt))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }

                if let latestSpotSummary, let spot = latestCompletedTrip?.spot {
                    Section("Private Recall For \(spot.title)") {
                        ForEach(latestSpotSummary.cards, id: \.id) { card in
                            DeterministicInsightCardView(card: card)
                        }
                    }
                }

                if !personalBests.isEmpty {
                    Section("Personal Bests") {
                        ForEach(personalBests.prefix(3), id: \.id) { record in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(record.species)
                                    .font(.headline)
                                Text(personalBestSummary(record))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Fishing Logbook")
        }
    }

    private func personalBestSummary(_ record: PersonalBest) -> String {
        let length = record.longestLengthCm.map { "Longest \($0.formatted()) cm" }
        let weight = record.heaviestWeightKg.map { "Heaviest \($0.formatted()) kg" }
        return [length, weight].compactMap { $0 }.joined(separator: " • ")
    }
}

private struct ActiveTripHero: View {
    let activeTrip: Trip
    let resume: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(activeTrip.title)
                .font(.headline)
            Text("Started \(AppFormatters.tripDate.string(from: activeTrip.startAt))")
                .foregroundStyle(.secondary)
            Button("Resume logging") {
                resume()
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(.vertical, 6)
    }
}
