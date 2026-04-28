import SwiftUI

enum DesignTokens {
    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
    }

    enum Radius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 18
    }

    enum Palette {
        static let surface = Color(.systemBackground)
        static let elevated = Color(.secondarySystemBackground)
        static let positive = Color.green.opacity(0.85)
        static let negative = Color.orange // muted, never alarming red
        static let muted = Color.secondary
    }
}
