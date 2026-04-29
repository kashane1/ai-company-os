import SwiftUI

struct InviteCodeStepView: View {
    @Binding var inviteCode: String
    var redeemed: Bool
    var onRedeem: () -> Void
    var onContinue: () -> Void
    var onBack: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xl) {
            Spacer(minLength: 0)
            VStack(alignment: .leading, spacing: Spacing.md) {
                AppBadge(text: "Step 4 of 4", tone: .appMomentum)
                Text("Did someone share a code?")
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                Text("If a friend already invited you to a plan, dropping the code here puts you on the right context from minute one. Skip if not.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                TextField("Invite code", text: $inviteCode)
                    .textInputAutocapitalization(.never)
                    .disableAutocorrection(true)
                    .font(.title3)
                    .padding(.vertical, Spacing.sm)
                    .padding(.horizontal, Spacing.md)
                    .background(Color.appBackground)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.appBorder, lineWidth: 1))

                if redeemed {
                    Label("Code accepted — you're in.", systemImage: "checkmark.seal.fill")
                        .font(.subheadline)
                        .foregroundStyle(Color.appAccent)
                }
            }
            .appSurface(prominent: true)
            Spacer(minLength: 0)
            VStack(spacing: Spacing.sm) {
                if !redeemed {
                    Button("Apply code") { onRedeem() }
                        .buttonStyle(ActionPillButtonStyle(prominent: true))
                        .disabled(inviteCode.trimmingCharacters(in: .whitespaces).isEmpty)
                }
                Button(redeemed ? "Continue" : "Skip") { onContinue() }
                    .buttonStyle(ActionPillButtonStyle(prominent: redeemed))
                Button("Back") { onBack() }
                    .buttonStyle(ActionPillButtonStyle())
            }
        }
        .padding(Spacing.xl)
    }
}
