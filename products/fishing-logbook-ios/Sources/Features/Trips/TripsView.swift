import SwiftData
import SwiftUI

struct TripsView: View {
    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]

    var body: some View {
        NavigationStack {
            List {
                if trips.isEmpty {
                    Text("Trips will appear here after you start logging.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(trips, id: \.id) { trip in
                        NavigationLink {
                            TripDetailView(trip: trip)
                        } label: {
                            TripRow(trip: trip, catchCount: catches.filter { $0.trip?.id == trip.id }.count)
                        }
                    }
                }
            }
            .navigationTitle("Trips")
        }
    }
}

struct TripDetailView: View {
    let trip: Trip

    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var allCatches: [CatchRecord]

    private var catches: [CatchRecord] {
        allCatches.filter { $0.trip?.id == trip.id }
    }

    var body: some View {
        List {
            Section("Overview") {
                LabeledContent("Waterbody", value: trip.waterbody?.name ?? "Unknown")
                LabeledContent("Spot", value: trip.spot?.title ?? "General waterbody")
                LabeledContent("Started", value: AppFormatters.tripDate.string(from: trip.startAt))
                if let endAt = trip.endAt {
                    LabeledContent("Ended", value: AppFormatters.tripDate.string(from: endAt))
                    let duration = endAt.timeIntervalSince(trip.startAt)
                    LabeledContent("Duration", value: AppFormatters.duration.string(from: duration) ?? "—")
                } else {
                    LabeledContent("Status", value: "In progress")
                }
                LabeledContent("Outcome", value: trip.outcomeRawValue.capitalized)
            }

            if let conditionSnapshot = trip.conditionSnapshot {
                Section("Condition Context") {
                    Text(conditionSnapshot.displaySummary)
                }
            }

            Section("Catches") {
                if catches.isEmpty {
                    Text("No catches logged on this trip.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(catches, id: \.id) { catchRecord in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(catchRecord.species)
                                .font(.headline)
                            Text(AppFormatters.tripDate.string(from: catchRecord.caughtAt))
                                .foregroundStyle(.secondary)
                            if !catchRecord.lureOrBait.isEmpty {
                                Text("Lure: \(catchRecord.lureOrBait)")
                                    .font(.footnote)
                            }
                            if let weight = catchRecord.weightKg {
                                Text("Weight: \(weight.formatted()) kg")
                                    .font(.footnote)
                            }
                            if let length = catchRecord.lengthCm {
                                Text("Length: \(length.formatted()) cm")
                                    .font(.footnote)
                            }
                            if !catchRecord.note.isEmpty {
                                Text(catchRecord.note)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle(trip.title)
    }
}

private struct TripRow: View {
    let trip: Trip
    let catchCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(trip.title)
                    .font(.headline)
                if trip.isActive {
                    Text("LIVE")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(.teal.opacity(0.15), in: Capsule())
                }
            }
            Text(AppFormatters.tripDate.string(from: trip.startAt))
                .foregroundStyle(.secondary)
            Text("\(catchCount) catches")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
    }
}
