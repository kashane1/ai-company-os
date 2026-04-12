import SwiftUI

// MARK: - Catchbook Brand Colors

extension Color {
    /// Sky Blue #B8E4F8 — lightest tint, backgrounds, empty states
    static let catchbookSky = Color(red: 0.722, green: 0.894, blue: 0.973)
    /// Aqua Blue #6DCFF6 — secondary accent, borders, tags, selected states
    static let catchbookAqua = Color(red: 0.427, green: 0.812, blue: 0.965)
    /// Ocean Blue #3BA3D9 — primary brand color, buttons, navigation tint, links
    static let catchbookOcean = Color(red: 0.231, green: 0.639, blue: 0.851)
    /// Deep Blue #1A7AB5 — headers, tab bar, toolbar backgrounds
    static let catchbookDeep = Color(red: 0.102, green: 0.478, blue: 0.710)
    /// Navy Blue #0D5E94 — darkest, text on light backgrounds, dark mode accents
    static let catchbookNavy = Color(red: 0.051, green: 0.369, blue: 0.580)
    /// Forest Green #4F8B68 — muted contrast tone for map grouping
    static let catchbookForest = Color(red: 0.310, green: 0.545, blue: 0.408)
    /// Amber #C89238 — muted warm contrast tone for map grouping
    static let catchbookAmber = Color(red: 0.784, green: 0.573, blue: 0.220)
    /// Soft Gray #C8D8E4 — shadows, dividers, secondary text
    static let catchbookShadow = Color(red: 0.784, green: 0.847, blue: 0.894)
    /// Dark Text #1A2A3A — near-black with blue tint
    static let catchbookText = Color(red: 0.102, green: 0.165, blue: 0.227)
}

// MARK: - Color Tokens

extension ShapeStyle where Self == Color {
    static var appAccent: Color { .catchbookOcean }
    static var appCardBackground: Color { .catchbookOcean.opacity(0.06) }
    static var appCardBackgroundProminent: Color { .catchbookOcean.opacity(0.10) }
    static var appSuccess: Color { Color(red: 0.204, green: 0.780, blue: 0.349) } // #34C759
    static var appWarning: Color { Color(red: 1.0, green: 0.624, blue: 0.039) }   // #FF9F0A
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
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .frame(minHeight: 44)
                .background(.fill.tertiary, in: Capsule())
                .contentShape(Capsule())
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
