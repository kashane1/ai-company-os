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

    private var totalCatches: Int { catches.count }
    private var totalTrips: Int { trips.filter { !$0.isActive }.count }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.xl) {
                    // Active Trip or Start CTA
                    if let activeTrip {
                        ActiveTripHero(activeTrip: activeTrip, catchCount: catches.filter { $0.trip?.id == activeTrip.id }.count) {
                            selectedTab = .log
                        }
                        .padding(.horizontal)
                    } else {
                        StartTripCTA {
                            selectedTab = .log
                        }
                        .padding(.horizontal)
                    }

                    // Quick Stats
                    if totalTrips > 0 {
                        HStack(spacing: Spacing.md) {
                            QuickStatCard(value: "\(totalTrips)", label: "Trips", icon: "water.waves")
                            QuickStatCard(value: "\(totalCatches)", label: "Catches", icon: "fish")
                            QuickStatCard(
                                value: "\(personalBests.count)",
                                label: personalBests.count == 1 ? "Best" : "Bests",
                                icon: "trophy"
                            )
                        }
                        .padding(.horizontal)
                    }

                    // Last Trip
                    if let latestCompletedTrip {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HomeSectionHeader(title: "Last Trip")
                                .padding(.horizontal)

                            NavigationLink {
                                TripDetailView(trip: latestCompletedTrip)
                            } label: {
                                LastTripCard(trip: latestCompletedTrip, catchCount: catches.filter { $0.trip?.id == latestCompletedTrip.id }.count)
                            }
                            .buttonStyle(.plain)
                            .padding(.horizontal)
                        }
                    }

                    // Private Recall
                    if let latestSpotSummary, !latestSpotSummary.cards.isEmpty, let spot = latestCompletedTrip?.spot {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HomeSectionHeader(title: "Recall for \(spot.title)")
                                .padding(.horizontal)

                            VStack(spacing: Spacing.sm) {
                                ForEach(latestSpotSummary.cards, id: \.id) { card in
                                    DeterministicInsightCardView(card: card)
                                }
                            }
                            .padding(.horizontal)
                        }
                    }

                    // Personal Bests
                    if !personalBests.isEmpty {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HomeSectionHeader(title: "Personal Bests")
                                .padding(.horizontal)

                            VStack(spacing: Spacing.sm) {
                                ForEach(personalBests.prefix(5), id: \.id) { record in
                                    PersonalBestRow(record: record)
                                }
                            }
                            .padding(.horizontal)
                        }
                    }
                }
                .padding(.vertical, Spacing.lg)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Logbook")
        }
    }
}

// MARK: - Start Trip CTA

private struct StartTripCTA: View {
    let action: () -> Void

    var body: some View {
        VStack(spacing: Spacing.lg) {
            Image(systemName: "water.waves")
                .font(.system(size: 36))
                .foregroundStyle(.teal.opacity(0.6))
                .padding(.top, Spacing.sm)

            Text("Ready when you are")
                .font(.title3.weight(.semibold))

            Text("Start a trip to begin logging catches. Your data stays private on this device.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.lg)

            Button(action: action) {
                Label("Start a Trip", systemImage: "plus.circle.fill")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, Spacing.md)
            }
            .buttonStyle(.borderedProminent)
            .tint(.appAccent)
        }
        .padding(Spacing.xxl)
        .background(.background, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

// MARK: - Active Trip Hero

private struct ActiveTripHero: View {
    let activeTrip: Trip
    let catchCount: Int
    let resume: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            HStack {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    HStack(spacing: Spacing.sm) {
                        AppBadge(text: "Live")
                        Text(elapsedText)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Text(activeTrip.title)
                        .font(.headline)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: Spacing.xxs) {
                    Text("\(catchCount)")
                        .font(.title2.weight(.bold).monospacedDigit())
                        .foregroundStyle(.appAccent)
                    Text(catchCount == 1 ? "catch" : "catches")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            if let snapshot = activeTrip.conditionSnapshot {
                Text(snapshot.displaySummary)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let spot = activeTrip.spot?.title {
                Label(spot, systemImage: "mappin")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Button(action: resume) {
                Label("Resume Logging", systemImage: "arrow.right.circle.fill")
                    .font(.subheadline.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, Spacing.sm)
            }
            .buttonStyle(.borderedProminent)
            .tint(.appAccent)
        }
        .appCard(prominent: true)
    }

    private var elapsedText: String {
        AppFormatters.duration.string(from: Date().timeIntervalSince(activeTrip.startAt)) ?? "now"
    }
}

// MARK: - Quick Stat Card

private struct QuickStatCard: View {
    let value: String
    let label: String
    let icon: String

    var body: some View {
        VStack(spacing: Spacing.xs) {
            Image(systemName: icon)
                .font(.footnote)
                .foregroundStyle(.appAccent)
            Text(value)
                .font(.title3.weight(.bold).monospacedDigit())
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.md)
        .background(.background, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

// MARK: - Last Trip Card

private struct LastTripCard: View {
    let trip: Trip
    let catchCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Text(trip.title)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }

            HStack(spacing: Spacing.lg) {
                Label(AppFormatters.tripDate.string(from: trip.startAt), systemImage: "calendar")
                Label(
                    "\(catchCount) \(catchCount == 1 ? "catch" : "catches")",
                    systemImage: "fish"
                )
            }
            .font(.footnote)
            .foregroundStyle(.secondary)

            if trip.outcomeRawValue == TripOutcome.skunked.rawValue {
                AppBadge(text: "Skunked", color: .secondary)
            }
        }
        .padding(Spacing.lg)
        .background(.background, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

// MARK: - Personal Best Row

private struct PersonalBestRow: View {
    let record: PersonalBest

    var body: some View {
        HStack(spacing: Spacing.md) {
            Image(systemName: "trophy.fill")
                .font(.footnote)
                .foregroundStyle(.orange)
                .frame(width: 28, height: 28)
                .background(.orange.opacity(0.10), in: Circle())

            VStack(alignment: .leading, spacing: Spacing.xxs) {
                Text(record.species)
                    .font(.subheadline.weight(.medium))
                Text(summaryText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()
        }
        .padding(Spacing.md)
        .background(.background, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var summaryText: String {
        let parts: [String?] = [
            record.longestLengthCm.map { "\($0.formatted()) cm" },
            record.heaviestWeightKg.map { "\($0.formatted()) kg" },
        ]
        return parts.compactMap { $0 }.joined(separator: " · ")
    }
}

// MARK: - Section Header

private struct HomeSectionHeader: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.footnote.weight(.semibold))
            .foregroundStyle(.secondary)
            .textCase(.uppercase)
    }
}
