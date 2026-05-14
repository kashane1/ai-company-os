import SwiftUI

struct SupportMomentCard: View {
    let moment: SupportMoment
    let dismissAction: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
            Image(systemName: moment.tone == .celebration ? "sparkles" : "heart.text.square")
                .foregroundStyle(moment.tone == .celebration ? DesignTokens.Palette.positive : Color.accentColor)
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text(moment.title)
                    .font(.headline)
                Text(moment.detail)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button {
                dismissAction()
            } label: {
                Image(systemName: "xmark")
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)
                    .padding(DesignTokens.Spacing.xs)
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("supportMoment.dismiss")
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        .cardLighting()
    }
}
