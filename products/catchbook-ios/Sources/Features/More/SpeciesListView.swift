import SwiftData
import SwiftUI

struct SpeciesListView: View {
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]

    private var speciesEntries: [SpeciesListLogic.SpeciesEntry] {
        SpeciesListLogic.speciesEntries(from: catches)
    }

    var body: some View {
        List {
            if speciesEntries.isEmpty {
                ContentUnavailableView {
                    Label("No Species Yet", systemImage: "fish")
                } description: {
                    Text("Species you've caught will appear here once you start logging catches.")
                }
            } else {
                Section {
                    ForEach(speciesEntries) { entry in
                        HStack {
                            Text(entry.species)
                                .font(.subheadline)
                            Spacer()
                            Text("\(entry.count)")
                                .font(.subheadline.monospacedDigit())
                                .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, Spacing.xxs)
                    }
                } header: {
                    Text("\(speciesEntries.count) species")
                } footer: {
                    Text("Counts reflect all catches in your logbook.")
                }
            }
        }
        .navigationTitle("Species")
    }
}
