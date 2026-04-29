import SwiftUI

enum DesignTokens {
    /// Maximum readable content width for scrollable surfaces. Locks cards
    /// to a comfortable column on iPad and Mac Catalyst (when supported);
    /// effectively a no-op on iPhone where the screen is already narrower.
    /// 720pt matches Apple's HIG "long-form reading" target.
    static let readableColumnWidth: CGFloat = 720

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

// MARK: - Readable column

extension View {
    /// Constrains scrolling content to a readable column on wide screens.
    /// Centers the content via `.frame(maxWidth:)`, leaving padding outside
    /// the column to mimic native iPad readability. No-op on narrow screens.
    func readableColumn() -> some View {
        self.frame(maxWidth: DesignTokens.readableColumnWidth)
            .frame(maxWidth: .infinity)
    }
}
