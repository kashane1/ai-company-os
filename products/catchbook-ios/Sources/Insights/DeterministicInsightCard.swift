import SwiftUI

struct DeterministicInsightCard: Identifiable {
    enum Kind: String {
        case lastTrips
        case recency
        case productivity
        case species
        case conditions
        case lure
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
    /// Singular noun for the support count (e.g. "sample", "trip", "catch").
    /// Plural is formed by appending "s" unless explicitly provided.
    let sampleNounSingular: String
    let sampleNounPlural: String

    init(
        kind: Kind,
        title: String,
        body: String,
        supportingSampleCount: Int,
        systemImage: String,
        sampleNounSingular: String = "sample",
        sampleNounPlural: String? = nil
    ) {
        self.kind = kind
        self.title = title
        self.body = body
        self.supportingSampleCount = supportingSampleCount
        self.systemImage = systemImage
        self.sampleNounSingular = sampleNounSingular
        self.sampleNounPlural = sampleNounPlural ?? "\(sampleNounSingular)s"
    }

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

            Text("Based on \(card.supportingSampleCount) logged \(card.supportingSampleCount == 1 ? card.sampleNounSingular : card.sampleNounPlural)")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .appCard()
    }
}
