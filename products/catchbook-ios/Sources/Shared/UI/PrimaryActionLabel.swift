import SwiftUI

struct PrimaryActionLabel: View {
    let title: String
    let systemImage: String

    var body: some View {
        HStack(spacing: Spacing.sm) {
            Image(systemName: systemImage)
            Text(title)
        }
        .font(.headline)
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.xs)
    }
}
