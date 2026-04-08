import SwiftUI

struct LifecycleBadgeView: View {
    let lifecycle: PlanLifecycleState

    var body: some View {
        AppBadge(text: lifecycle.title, tone: tone)
    }

    private var tone: Color {
        switch lifecycle {
        case .open:
            .appAccent
        case .forming:
            .appMomentum
        case .confirmed:
            .appSafe
        case .active:
            .appAccent
        case .closed:
            .secondary
        }
    }
}

struct LifecycleProgressView: View {
    let lifecycle: PlanLifecycleState
    var compact: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? Spacing.xs : Spacing.sm) {
            Text(lifecycle.progressLabel)
                .font(compact ? .caption.weight(.semibold) : .footnote.weight(.semibold))
                .foregroundStyle(.secondary)

            HStack(spacing: compact ? 4 : 6) {
                ForEach(Array(PlanLifecycleState.allCases.enumerated()), id: \.offset) { index, state in
                    Capsule()
                        .fill(fillColor(for: index, state: state))
                        .frame(height: compact ? 6 : 8)
                }
            }
        }
    }

    private func fillColor(for index: Int, state: PlanLifecycleState) -> Color {
        let activeIndex = PlanLifecycleState.allCases.firstIndex(of: lifecycle) ?? 0
        guard index <= activeIndex else { return .appBorder }

        switch state {
        case .open:
            return .appAccent.opacity(0.55)
        case .forming:
            return .appMomentum
        case .confirmed:
            return .appSafe
        case .active:
            return .appAccent
        case .closed:
            return .secondary.opacity(0.55)
        }
    }
}
