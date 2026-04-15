import SwiftUI

/// Wraps a `TextField` (or any text-input view) with a trailing character counter
/// and enforces a hard character limit by truncating the bound string.
///
/// Usage:
/// ```swift
/// TextField("Spot name", text: $title)
///     .textInputAutocapitalization(.words)
///     .characterLimit(CharacterLimits.spotName, text: $title)
/// ```
///
/// The counter renders inside the same Form row as the field, pinned to the
/// trailing edge under the input. When the limit is reached the counter turns
/// orange so the user sees they've hit the cap.
struct CharacterLimitContainer<Content: View>: View {
    let limit: Int
    @Binding var text: String
    @ViewBuilder var content: () -> Content

    var body: some View {
        VStack(alignment: .trailing, spacing: 2) {
            content()
            Text("\(text.count)/\(limit)")
                .font(.caption2.monospacedDigit())
                .foregroundStyle(counterColor)
                .accessibilityHidden(true)
        }
        .onChange(of: text) { _, newValue in
            if newValue.count > limit {
                text = String(newValue.prefix(limit))
            }
        }
    }

    private var counterColor: Color {
        text.count >= limit ? .orange : .secondary.opacity(0.6)
    }
}

extension View {
    /// Attaches a character counter and enforces a max-length truncation on
    /// the provided text binding.
    func characterLimit(_ limit: Int, text: Binding<String>) -> some View {
        CharacterLimitContainer(limit: limit, text: text) { self }
    }
}

/// Centralized character limits for every user-facing text input. Keeping the
/// values here means the UI, tests, and (if we ever add them) validation rules
/// all agree on a single source of truth.
enum CharacterLimits {
    // Spot
    static let spotName = 50
    static let spotNotes = 500

    // Trip
    static let tripTargetSpecies = 200
    static let tripNotes = 1000

    // Catch
    static let catchSpecies = 60
    static let catchLureOrBait = 60
    static let catchMethod = 60
    static let catchGear = 100
    static let catchNote = 500

    // Saved lure
    static let lureName = 60
    static let lureColor = 40
    static let lureNotes = 400

    // Conditions edit-correct fields (short auto-populated summaries)
    static let conditionSummary = 80
}
