import SwiftUI

struct TimeLedgerView: View {
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        NavigationStack {
            List {
                if store.ledger.isEmpty {
                    Text("No entries yet — your ledger fills up as data flows in.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(store.ledger, id: \.id) { entry in
                        ledgerRow(entry)
                    }
                }
                Section {
                    DisclaimerBanner()
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }
            }
            .navigationTitle("Time Ledger")
        }
    }

    private func ledgerRow(_ entry: TimeLedgerEntry) -> some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
            Image(systemName: sourceIcon(entry.source))
                .foregroundStyle(.secondary)
                .frame(width: 24)
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text(entry.title).font(.callout)
                Text(entry.driverType.capitalized + " · " + entry.source.capitalized)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(TimeDeltaFormatter.format(minutes: entry.deltaMinutes))
                .foregroundStyle(entry.deltaMinutes >= 0 ? DesignTokens.Palette.positive : DesignTokens.Palette.negative)
                .font(.callout.monospacedDigit())
        }
    }

    private func sourceIcon(_ source: String) -> String {
        switch source {
        case "healthkit": return "heart.text.square"
        case "manual": return "pencil"
        default: return "sparkles"
        }
    }
}
