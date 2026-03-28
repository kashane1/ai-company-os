import SwiftUI

struct DeterministicInsightCard: Identifiable {
    enum Kind: String {
        case lastTrips
        case bestTimeWindow
        case mostEffectiveLure
        case similarConditions
    }

    let kind: Kind
    let title: String
    let body: String
    let supportingSampleCount: Int
    let systemImage: String

    var id: String { kind.rawValue }
}

struct DeterministicInsightCardView: View {
    let card: DeterministicInsightCard

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(card.title, systemImage: card.systemImage)
                .font(.headline)
            Text(card.body)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("Based on \(card.supportingSampleCount) logged \(card.supportingSampleCount == 1 ? "sample" : "samples")")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(14)
        .background(.teal.opacity(0.08), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}
