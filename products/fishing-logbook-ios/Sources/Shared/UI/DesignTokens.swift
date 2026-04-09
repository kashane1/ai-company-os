import SwiftUI

// MARK: - Color Tokens

extension ShapeStyle where Self == Color {
    static var appAccent: Color { .teal }
    static var appCardBackground: Color { .teal.opacity(0.06) }
    static var appCardBackgroundProminent: Color { .teal.opacity(0.10) }
    static var appSuccess: Color { .green }
    static var appWarning: Color { .orange }
    static var appSkunked: Color { .secondary }
}

// MARK: - Spacing

enum Spacing {
    static let xxs: CGFloat = 2
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 20
    static let xxl: CGFloat = 24
    static let xxxl: CGFloat = 32
}

// MARK: - Card Style

struct AppCardStyle: ViewModifier {
    var prominent: Bool = false

    func body(content: Content) -> some View {
        content
            .padding(Spacing.lg)
            .background(
                prominent ? Color.appCardBackgroundProminent : Color.appCardBackground,
                in: RoundedRectangle(cornerRadius: 14, style: .continuous)
            )
    }
}

extension View {
    func appCard(prominent: Bool = false) -> some View {
        modifier(AppCardStyle(prominent: prominent))
    }
}

// MARK: - Stat Capsule

struct StatCapsule: View {
    let value: String
    let label: String
    var icon: String? = nil

    var body: some View {
        HStack(spacing: Spacing.xs) {
            if let icon {
                Image(systemName: icon)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.appAccent)
            }
            Text(value)
                .font(.subheadline.weight(.semibold))
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

// MARK: - Section Empty State

struct SectionEmptyState: View {
    let icon: String
    let title: String
    let subtitle: String

    var body: some View {
        VStack(spacing: Spacing.sm) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundStyle(.tertiary)
            Text(title)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)
            Text(subtitle)
                .font(.caption)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.xl)
    }
}

// MARK: - Badge

struct AppBadge: View {
    let text: String
    var color: Color = .appAccent

    var body: some View {
        Text(text)
            .font(.caption2.weight(.bold))
            .textCase(.uppercase)
            .padding(.horizontal, 7)
            .padding(.vertical, 3)
            .foregroundStyle(color)
            .background(color.opacity(0.12), in: Capsule())
    }
}

// MARK: - Inline Metadata Row

struct MetadataRow: View {
    let items: [(icon: String, text: String)]

    var body: some View {
        HStack(spacing: Spacing.md) {
            ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                Label(item.text, systemImage: item.icon)
            }
        }
        .font(.footnote)
        .foregroundStyle(.secondary)
    }
}

// MARK: - Suggestion Chip

struct SuggestionChip: View {
    let text: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(text)
                .font(.footnote.weight(.medium))
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(.fill.tertiary, in: Capsule())
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Suggestion Row

struct SuggestionRow: View {
    let label: String
    let values: [String]
    let onSelect: (String) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: Spacing.sm) {
                ForEach(values, id: \.self) { value in
                    SuggestionChip(text: value) {
                        onSelect(value)
                    }
                }
            }
        }
        .listRowInsets(EdgeInsets(top: 4, leading: 20, bottom: 4, trailing: 20))
    }
}

// MARK: - Saved Confirmation Banner

struct SavedConfirmationBanner: View {
    let text: String

    var body: some View {
        HStack(spacing: Spacing.xs) {
            Image(systemName: "checkmark.circle.fill")
            Text(text)
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(.appAccent)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.appAccent.opacity(0.12), in: Capsule())
        .transition(.move(edge: .top).combined(with: .opacity))
    }
}
