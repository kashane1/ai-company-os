import SwiftUI

/// Shared empty state for Life Clock surfaces.
///
/// The premium-feel audit (2026-05-12) flagged the existing "No data
/// persisted for this day yet." pattern as `empty-state-flat` — generic,
/// dead-end, tone-mismatched. The rubric in `premium-bar.md` § "Empty
/// states" calls for three things:
///   1. A clear, branded explanation of why the surface is empty.
///   2. An action the user can take (or a clear "nothing to do here yet").
///   3. Tone alignment with the rest of the app's voice.
///
/// This view enforces the structure: title + body + optional action.
/// Surfaces opt in by replacing `Text("No data…")` with `EmptyStateView(...)`.
///
/// Design intent:
///  - `systemImage` is optional. When the surface already carries a
///    contextual icon (e.g., History day-detail's calendar icon), the
///    icon-less constructor is correct.
///  - `action` is optional but encouraged. An action turns a dead-end
///    into a forward motion.
///  - All copy slots accept tone-aware strings from the ToneMode pools;
///    the view itself doesn't pick tone — callers do.
///
/// Cross-references:
///  - Premium-bar: `docs/products/life-clock/premium-bar.md` § "Empty states"
///  - Audit prompt: `premium-feel-backlog-2026-05-12-standard.md` Prompt 2
///    (`empty-state-flat`)
struct EmptyStateView: View {
    let title: String
    let body_: String
    let systemImage: String?
    let actionTitle: String?
    let action: (() -> Void)?

    init(
        title: String,
        body: String,
        systemImage: String? = nil,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.title = title
        self.body_ = body
        self.systemImage = systemImage
        self.actionTitle = actionTitle
        self.action = action
    }

    var body: some View {
        VStack(spacing: 12) {
            if let systemImage {
                Image(systemName: systemImage)
                    .font(.system(size: 32, weight: .regular))
                    .foregroundStyle(.secondary)
                    .padding(.bottom, 4)
            }
            Text(title)
                .font(.headline)
                .multilineTextAlignment(.center)
            Text(body_)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .buttonStyle(.borderedProminent)
                    .padding(.top, 8)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .accessibilityElement(children: .combine)
    }
}

#Preview("icon + body only") {
    EmptyStateView(
        title: "Nothing logged here yet",
        body: "Once you log a habit or Apple Health imports a day, you'll see it here.",
        systemImage: "calendar"
    )
}

#Preview("with action") {
    EmptyStateView(
        title: "No Apple Health connection yet",
        body: "Life Clock needs basic activity, sleep, and resting heart-rate data to estimate today's time delta.",
        systemImage: "heart",
        actionTitle: "Connect Apple Health",
        action: {}
    )
}
