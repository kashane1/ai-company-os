import SwiftUI

struct PrivacyStepView: View {
    @Binding var privacyMode: PrivacyMode
    var onContinue: () -> Void
    var onBack: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xl) {
            Spacer(minLength: 0)
            VStack(alignment: .leading, spacing: Spacing.md) {
                AppBadge(text: "Step 2 of 4", tone: .appMomentum)
                Text("How visible should you be?")
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                Text("You can change this anytime in Profile.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                ForEach(PrivacyMode.allCases) { mode in
                    Button { privacyMode = mode } label: {
                        HStack(alignment: .top, spacing: Spacing.md) {
                            Image(systemName: privacyMode == mode ? "largecircle.fill.circle" : "circle")
                                .foregroundStyle(privacyMode == mode ? Color.appAccent : Color.appBorder)
                                .font(.title2)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(mode.title)
                                    .font(.headline)
                                Text(mode.subtitle)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            Spacer()
                        }
                        .padding(Spacing.md)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(Color.appBackground)
                                .overlay(RoundedRectangle(cornerRadius: 12)
                                    .stroke(privacyMode == mode ? Color.appAccent : Color.appBorder, lineWidth: 1))
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
            .appSurface(prominent: true)
            Spacer(minLength: 0)
            VStack(spacing: Spacing.sm) {
                Button("Continue") { onContinue() }
                    .buttonStyle(ActionPillButtonStyle(prominent: true))
                Button("Back") { onBack() }
                    .buttonStyle(ActionPillButtonStyle())
            }
        }
        .padding(Spacing.xl)
    }
}
