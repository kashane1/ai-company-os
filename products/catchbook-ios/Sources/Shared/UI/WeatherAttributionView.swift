import SwiftUI
import WeatherKit

/// Apple WeatherKit Display Attribution.
///
/// Per Apple's WeatherKit Display Attribution Requirements, any surface that
/// shows WeatherKit data must display the " Weather" mark as a link to the
/// legal attribution page. The legal page itself lists the data sources, so a
/// single `Link` to `WeatherAttribution.legalPageURL` satisfies both the mark
/// display and data-sources-link requirements.
///
/// The view loads the official combined mark asset when available and falls
/// back to the Apple-logo glyph + "Weather" text if asset loading fails.
@available(iOS 17.0, *)
struct WeatherAttributionView: View {
    @Environment(\.colorScheme) private var colorScheme
    @State private var attribution: WeatherAttribution?

    var body: some View {
        Group {
            if let attribution {
                Link(destination: attribution.legalPageURL) {
                    HStack(spacing: 4) {
                        AsyncImage(
                            url: colorScheme == .dark
                                ? attribution.combinedMarkDarkURL
                                : attribution.combinedMarkLightURL
                        ) { phase in
                            switch phase {
                            case .success(let image):
                                image
                                    .resizable()
                                    .scaledToFit()
                                    .frame(height: 14)
                                    .accessibilityHidden(true)
                            default:
                                // Fallback to Apple-logo glyph if asset fails to load.
                                Text("\u{F8FF} Weather")
                            }
                        }
                    }
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                }
                .accessibilityLabel("Weather data from Apple Weather. Tap for legal attribution and data sources.")
            } else {
                // Minimal static fallback while the attribution is loading or unavailable.
                Text("\u{F8FF} Weather")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .task {
            attribution = await WeatherKitService.shared.attribution()
        }
    }
}

#Preview {
    if #available(iOS 17.0, *) {
        WeatherAttributionView()
            .padding()
    }
}
