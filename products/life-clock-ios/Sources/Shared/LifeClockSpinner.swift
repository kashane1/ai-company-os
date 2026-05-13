import SwiftUI

/// Shared, branded loading indicator for Life Clock surfaces.
///
/// Replaces ad-hoc `ProgressView() + "Loading…"` patterns. The premium-feel
/// audit (2026-05-12) flagged eight surfaces using bare `ProgressView()` —
/// a `loading-bare` violation against the premium-bar rubric. This view
/// gives them a single, on-brand alternative.
///
/// Design intent:
///  - The system `ProgressView` carries the heavy lifting (accessibility,
///    iOS-native indeterminate animation, Reduce-Motion fallback).
///  - The branded layer is a slot for tone-appropriate caption + a tinted
///    accent so the load state reads as part of Life Clock, not iOS chrome.
///  - Caption is optional. When the surface already conveys context (e.g.
///    a button label next to the spinner), the caption-less constructor is
///    the right call.
///
/// Sizes:
///  - `.inline` (default for button-adjacent use; SwiftUI default size)
///  - `.regular` (for in-card loading; uses `.controlSize(.large)`)
///  - `.full` (centered-in-frame for full-screen loading states)
///
/// Cross-references:
///  - Premium-bar: `docs/products/life-clock/premium-bar.md` § "Loading states"
///  - Audit prompt: `premium-feel-backlog-2026-05-12-standard.md` Prompt 4
///    (`loading-bare`)
struct LifeClockSpinner: View {
    enum Size {
        case inline
        case regular
        case full
    }

    let caption: String?
    let size: Size

    init(_ caption: String? = nil, size: Size = .inline) {
        self.caption = caption
        self.size = size
    }

    var body: some View {
        switch size {
        case .inline:
            ProgressView()
                .tint(.accentColor)
                .accessibilityLabel(caption ?? "Loading")
        case .regular:
            HStack(spacing: 8) {
                ProgressView()
                    .controlSize(.large)
                    .tint(.accentColor)
                if let caption {
                    Text(caption)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel(caption ?? "Loading")
        case .full:
            VStack(spacing: 16) {
                ProgressView()
                    .controlSize(.large)
                    .tint(.accentColor)
                if let caption {
                    Text(caption)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding()
            .accessibilityElement(children: .combine)
            .accessibilityLabel(caption ?? "Loading")
        }
    }
}

#Preview("inline") {
    LifeClockSpinner()
        .padding()
}

#Preview("regular") {
    LifeClockSpinner("Loading subscription options", size: .regular)
        .padding()
}

#Preview("full") {
    LifeClockSpinner("Reading your Apple Health data…", size: .full)
}
