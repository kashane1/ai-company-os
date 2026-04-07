import SwiftUI

extension ShapeStyle where Self == Color {
    static var appAccent: Color { Color(red: 0.12, green: 0.39, blue: 0.78) }
    static var appMomentum: Color { Color(red: 0.98, green: 0.60, blue: 0.18) }
    static var appSafe: Color { Color(red: 0.11, green: 0.54, blue: 0.42) }
    static var appBackground: Color { Color(red: 0.96, green: 0.97, blue: 0.98) }
    static var appCard: Color { Color.white.opacity(0.86) }
    static var appCardStrong: Color { Color.white.opacity(0.97) }
    static var appBorder: Color { Color.black.opacity(0.08) }
}

enum Spacing {
    static let xs: CGFloat = 6
    static let sm: CGFloat = 10
    static let md: CGFloat = 14
    static let lg: CGFloat = 18
    static let xl: CGFloat = 24
    static let xxl: CGFloat = 32
}

struct AppSurface: ViewModifier {
    var prominent: Bool = false

    func body(content: Content) -> some View {
        content
            .padding(Spacing.lg)
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(prominent ? Color.appCardStrong : Color.appCard)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .stroke(Color.appBorder, lineWidth: 1)
            )
    }
}

extension View {
    func appSurface(prominent: Bool = false) -> some View {
        modifier(AppSurface(prominent: prominent))
    }
}

struct AppBadge: View {
    let text: String
    var tone: Color = .appAccent

    var body: some View {
        Text(text)
            .font(.caption2.weight(.bold))
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .foregroundStyle(tone)
            .background(tone.opacity(0.14), in: Capsule())
    }
}

struct SectionHeader: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.title3.weight(.semibold))
            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

struct InfoRow: View {
    let icon: String
    let text: String

    var body: some View {
        Label(text, systemImage: icon)
            .font(.footnote)
            .foregroundStyle(.secondary)
    }
}

struct ActionPillButtonStyle: ButtonStyle {
    var prominent: Bool = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline.weight(.semibold))
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity)
            .background(
                prominent ? Color.appAccent.opacity(configuration.isPressed ? 0.72 : 1.0) :
                    Color.appBorder.opacity(configuration.isPressed ? 0.18 : 0.12),
                in: Capsule()
            )
            .foregroundStyle(prominent ? Color.white : Color.primary)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
    }
}
