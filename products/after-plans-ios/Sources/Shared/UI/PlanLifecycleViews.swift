import SwiftUI

// MARK: - Lifecycle badge

struct LifecycleBadgeView: View {
    let lifecycle: PlanLifecycleState

    var body: some View {
        AppBadge(text: lifecycle.title, tone: tone)
    }

    private var tone: Color {
        switch lifecycle {
        case .open:      .appAccent
        case .forming:   .appMomentum
        case .confirmed: .appSafe
        case .active:    .appAccent
        case .closed:    .secondary
        }
    }
}

// MARK: - Lifecycle progress

struct LifecycleProgressView: View {
    let lifecycle: PlanLifecycleState
    var compact: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 4 : Spacing.xs) {
            if !compact {
                Text(lifecycle.progressLabel)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: compact ? 3 : 5) {
                ForEach(Array(PlanLifecycleState.allCases.enumerated()), id: \.offset) { index, state in
                    RoundedRectangle(cornerRadius: 3, style: .continuous)
                        .fill(fillColor(for: index, state: state))
                        .frame(height: compact ? 4 : 6)
                        .animation(.easeInOut(duration: 0.25), value: lifecycle)
                }
            }

            if compact {
                Text(lifecycle.progressLabel)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
        }
    }

    private func fillColor(for index: Int, state: PlanLifecycleState) -> Color {
        let activeIndex = PlanLifecycleState.allCases.firstIndex(of: lifecycle) ?? 0
        guard index <= activeIndex else {
            return Color.appBorder
        }

        switch state {
        case .open:      return .appAccent.opacity(0.45)
        case .forming:   return .appMomentum.opacity(0.85)
        case .confirmed: return .appSafe
        case .active:    return .appAccent
        case .closed:    return .secondary.opacity(0.4)
        }
    }
}
