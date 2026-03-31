import SwiftUI

struct DeterministicInsightCard: Identifiable {
    enum Kind: String {
        case lastTrips
        case bestTimeWindow
        case mostEffectiveLure
        case seasonality
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
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack(spacing: Spacing.sm) {
                Image(systemName: card.systemImage)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.appAccent)
                    .frame(width: 24, height: 24)
                    .background(Color.appCardBackground, in: Circle())

                Text(card.title)
                    .font(.subheadline.weight(.semibold))
            }

            Text(card.body)
                .font(.footnote)
                .foregroundStyle(.secondary)

            Text("Based on \(card.supportingSampleCount) logged \(card.supportingSampleCount == 1 ? "sample" : "samples")")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .appCard()
    }
}
