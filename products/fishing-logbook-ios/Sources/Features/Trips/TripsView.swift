import SwiftData
import SwiftUI

struct TripsView: View {
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]

    var body: some View {
        NavigationStack {
            Group {
                if trips.isEmpty {
                    ContentUnavailableView {
                        Label("No Trips Yet", systemImage: "water.waves")
                    } description: {
                        Text("Start a trip from the Log tab to begin building your private fishing memory.")
                    }
                } else {
                    List {
                        ForEach(trips, id: \.id) { trip in
                            NavigationLink {
                                TripDetailView(trip: trip)
                            } label: {
                                TripRow(
                                    trip: trip,
                                    catchCount: catches.filter { $0.trip?.id == trip.id }.count
                                )
                            }
                        }
                    }
                }
            }
            .navigationTitle("Trips")
        }
    }
}

// MARK: - Trip Row

private struct TripRow: View {
    let trip: Trip
    let catchCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack(alignment: .firstTextBaseline) {
                Text(trip.title)
                    .font(.subheadline.weight(.semibold))

                if trip.isActive {
                    AppBadge(text: "Live")
                }

                Spacer()

                Text(catchCount == 0 && !trip.isActive ? "Skunked" : "\(catchCount)")
                    .font(.subheadline.weight(.semibold).monospacedDigit())
                    .foregroundColor(catchCount == 0 && !trip.isActive ? .secondary : .appAccent)
            }

            HStack(spacing: Spacing.md) {
                Label(AppFormatters.tripDate.string(from: trip.startAt), systemImage: "calendar")

                if let endAt = trip.endAt {
                    let duration = endAt.timeIntervalSince(trip.startAt)
                    if let durationText = AppFormatters.duration.string(from: duration) {
                        Label(durationText, systemImage: "timer")
                    }
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if let spot = trip.spot?.title {
                Label(spot, systemImage: "mappin")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.vertical, Spacing.xs)
    }
}

// MARK: - Trip Detail

struct TripDetailView: View {
    let trip: Trip

    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var allCatches: [CatchRecord]

    private var catches: [CatchRecord] {
        allCatches.filter { $0.trip?.id == trip.id }
    }

    var body: some View {
        List {
            // Summary Stats
            Section {
                HStack(spacing: Spacing.xl) {
                    TripStatPill(value: "\(catches.count)", label: catches.count == 1 ? "Catch" : "Catches", icon: "fish")
                    if let endAt = trip.endAt {
                        let duration = endAt.timeIntervalSince(trip.startAt)
                        if let durationText = AppFormatters.duration.string(from: duration) {
                            TripStatPill(value: durationText, label: "Duration", icon: "timer")
                        }
                    }
                    TripStatPill(
                        value: trip.outcomeRawValue.capitalized,
                        label: "Outcome",
                        icon: trip.outcomeRawValue == TripOutcome.skunked.rawValue ? "xmark.circle" : "checkmark.circle"
                    )
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, Spacing.sm)
                .listRowBackground(Color.clear)
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
                if !trip.targetSpecies.isEmpty {
                    LabeledContent("Target", value: trip.targetSpecies)
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
                    if let placeSummary = snapshot.placeSummary {
                        LabeledContent("Place", value: placeSummary)
                    }
                    if let timeWindowSummary = snapshot.timeWindowSummary {
                        LabeledContent("Window", value: timeWindowSummary)
                    }
                    if let lightLevelSummary = snapshot.lightLevelSummary {
                        LabeledContent("Light", value: lightLevelSummary)
                    }
                    LabeledContent("Weather", value: snapshot.weatherLine)
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
                        CatchHistoryRow(catchRecord: catchRecord, includeTimestamp: true)
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
            }
        }
        .navigationTitle(trip.title)
        .navigationBarTitleDisplayMode(.large)
    }
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
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }
}
