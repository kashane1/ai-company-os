import SwiftUI
import UIKit

// MARK: - Color tokens
//
// Brand tokens (BrandAccent / Momentum / Safe) live in Assets.xcassets
// with explicit Any + Dark appearance variants. Chrome tokens map to
// UIKit dynamic system colors so they adapt to the user's color scheme,
// accessibility contrast settings, and Reduce Transparency.

extension ShapeStyle where Self == Color {
    static var appAccent: Color { Color("BrandAccent", bundle: .main) }
    static var appMomentum: Color { Color("Momentum", bundle: .main) }
    static var appSafe: Color { Color("Safe", bundle: .main) }
    static var appBackground: Color { Color(UIColor.systemGroupedBackground) }
    static var appCard: Color { Color(UIColor.secondarySystemGroupedBackground) }
    static var appCardStrong: Color { Color(UIColor.secondarySystemGroupedBackground) }
    static var appBorder: Color { Color(UIColor.separator) }
}

// MARK: - Spacing

enum Spacing {
    static let xs: CGFloat = 6
    static let sm: CGFloat = 10
    static let md: CGFloat = 14
    static let lg: CGFloat = 18
    static let xl: CGFloat = 24
    static let xxl: CGFloat = 32
}

// MARK: - Surface
// tint: optional left-edge accent color — used to encode card state
// (e.g. appSafe for high-trust, appMomentum for forming, nil for neutral)

struct AppSurface: ViewModifier {
    var prominent: Bool = false
    var tint: Color? = nil

    func body(content: Content) -> some View {
        content
            .padding(Spacing.lg)
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(prominent ? Color.appCardStrong : Color.appCard)
                    .shadow(
                        color: Color(UIColor.label).opacity(prominent ? 0.10 : 0.06),
                        radius: prominent ? 16 : 8,
                        y: prominent ? 4 : 2
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .stroke(tint?.opacity(0.25) ?? Color.appBorder, lineWidth: 0.75)
            )
            .overlay(alignment: .leading) {
                if let tint {
                    RoundedRectangle(cornerRadius: 3, style: .continuous)
                        .fill(tint.opacity(0.7))
                        .frame(width: 3)
                        .padding(.vertical, Spacing.lg + 2)
                        .padding(.leading, 2)
                }
            }
    }
}

extension View {
    func appSurface(prominent: Bool = false, tint: Color? = nil) -> some View {
        modifier(AppSurface(prominent: prominent, tint: tint))
    }
}

// MARK: - Card divider

struct CardDivider: View {
    var body: some View {
        Rectangle()
            .fill(Color.appBorder)
            .frame(height: 0.5)
            .padding(.vertical, 2)
    }
}

// MARK: - Badge

struct AppBadge: View {
    let text: String
    var tone: Color = .appAccent

    var body: some View {
        Text(text)
            .font(.caption2.weight(.bold))
            .tracking(0.3)
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .foregroundStyle(tone)
            .background(tone.opacity(0.12), in: Capsule())
    }
}

// MARK: - Section header
// subtitle defaults to "" — omit when no subtitle is needed

struct SectionHeader: View {
    let title: String
    var subtitle: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.subheadline.weight(.semibold))
            if !subtitle.isEmpty {
                Text(subtitle)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

// MARK: - Info row

struct InfoRow: View {
    let icon: String
    let text: String

    var body: some View {
        Label(text, systemImage: icon)
            .font(.footnote)
            .foregroundStyle(.secondary)
    }
}

// MARK: - Participant avatar — initials circle for people surfaces

struct ParticipantAvatar: View {
    let name: String
    var size: CGFloat = 36
    var color: Color = .appAccent

    var body: some View {
        ZStack {
            Circle()
                .fill(color.opacity(0.12))
                .frame(width: size, height: size)
            Text(String(name.prefix(1)).uppercased())
                .font(.system(size: size * 0.38, weight: .semibold, design: .rounded))
                .foregroundStyle(color)
        }
    }
}

// MARK: - Action pill button — primary (accent fill) and secondary (neutral fill)

struct ActionPillButtonStyle: ButtonStyle {
    var prominent: Bool = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline.weight(.semibold))
            .padding(.horizontal, 16)
            .padding(.vertical, 11)
            .frame(maxWidth: .infinity)
            .background(
                Capsule().fill(
                    prominent
                        ? Color.appAccent.opacity(configuration.isPressed ? 0.78 : 1.0)
                        : Color(UIColor.secondarySystemFill).opacity(configuration.isPressed ? 1.4 : 1.0)
                )
            )
            .foregroundStyle(prominent ? Color.white : Color.primary)
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .animation(.spring(response: 0.2, dampingFraction: 0.75), value: configuration.isPressed)
    }
}

// MARK: - Plain press button — opacity-only feedback for non-themed rows (e.g. safety actions)

struct PlainPressButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .opacity(configuration.isPressed ? 0.55 : 1.0)
            .animation(.easeInOut(duration: 0.15), value: configuration.isPressed)
    }
}

// MARK: - Text link button — tertiary / inline actions

struct TextLinkButtonStyle: ButtonStyle {
    var color: Color = .appAccent

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline.weight(.medium))
            .foregroundStyle(color.opacity(configuration.isPressed ? 0.55 : 1.0))
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .animation(.spring(response: 0.2, dampingFraction: 0.75), value: configuration.isPressed)
    }
}
