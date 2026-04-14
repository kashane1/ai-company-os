import SwiftData
import SwiftUI

struct PersonalBestsListView: View {
    @Query(sort: \PersonalBest.updatedAt, order: .reverse) private var personalBests: [PersonalBest]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]

    var body: some View {
        List {
            if personalBests.isEmpty {
                ContentUnavailableView {
                    Label("No Personal Bests", systemImage: "trophy")
                } description: {
                    Text("Log catches with weight or length to start tracking personal records by species.")
                }
            } else {
                ForEach(personalBests, id: \.id) { record in
                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        HStack {
                            Image(systemName: "trophy.fill")
                                .font(.footnote)
                                .foregroundStyle(.appWarning)
                            Text(record.species)
                                .font(.headline)
                        }

                        if let heaviest = record.heaviestWeightKg {
                            StatCapsule(value: "\(heaviest.formatted()) kg", label: "Heaviest", icon: "scalemass")
                        }

                        if let longest = record.longestLengthCm {
                            StatCapsule(value: "\(longest.formatted()) cm", label: "Longest", icon: "ruler")
                        }

                        Text(HomeDashboardLogic.personalBestSummaryText(
                            longestLengthCm: record.longestLengthCm,
                            heaviestWeightKg: record.heaviestWeightKg
                        ))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, Spacing.xs)
                }
            }
        }
        .navigationTitle("Personal Bests")
    }
}
