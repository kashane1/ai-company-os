import SwiftUI

struct NameStepView: View {
    @Binding var firstName: String
    var onContinue: () -> Void
    var onBack: () -> Void

    private var isValid: Bool {
        let trimmed = firstName.trimmingCharacters(in: .whitespaces)
        return trimmed.count >= 1 && trimmed.count <= 24
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xl) {
            Spacer(minLength: 0)
            VStack(alignment: .leading, spacing: Spacing.md) {
                AppBadge(text: "Step 1 of 4", tone: .appMomentum)
                Text("What should we call you?")
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                Text("Just a first name is enough. People in your shared contexts will see this when you join their plans.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                TextField("First name", text: $firstName)
                    .textInputAutocapitalization(.words)
                    .disableAutocorrection(true)
                    .font(.title3)
                    .padding(.vertical, Spacing.sm)
                    .padding(.horizontal, Spacing.md)
                    .background(Color.appBackground)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.appBorder, lineWidth: 1))
            }
            .appSurface(prominent: true)
            Spacer(minLength: 0)
            VStack(spacing: Spacing.sm) {
                Button("Continue") { onContinue() }
                    .buttonStyle(ActionPillButtonStyle(prominent: true))
                    .disabled(!isValid)
                Button("Back") { onBack() }
                    .buttonStyle(ActionPillButtonStyle())
            }
        }
        .padding(Spacing.xl)
    }
}
