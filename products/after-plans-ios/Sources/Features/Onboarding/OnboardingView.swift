import SwiftUI

private struct OnboardingStep: Identifiable {
    let id: Int
    let title: String
    let body: String
    let accent: String
    let icon: String
}

struct OnboardingView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @State private var stepIndex = 0
    @State private var direction: Edge = .trailing  // tracks swipe direction for transitions

    private let steps = [
        OnboardingStep(
            id: 0,
            title: "Keep the moment going.",
            body: "After Plans is for the few minutes right after something ends — when people are still nearby and the next move is easiest to make.",
            accent: "See what happens after",
            icon: "arrow.forward.circle.fill"
        ),
        OnboardingStep(
            id: 1,
            title: "Join before you overthink it.",
            body: "Signal interest with one tap. Soft signals come first, so there's no pressure to commit before the plan takes shape.",
            accent: "Low-pressure joining",
            icon: "hand.thumbsup.fill"
        ),
        OnboardingStep(
            id: 2,
            title: "People you know or are already around.",
            body: "Shared context, known faces, and past plan partners come first. This is not a public discovery feed or a stranger-matching app.",
            accent: "Bounded trust",
            icon: "person.2.fill"
        ),
        OnboardingStep(
            id: 3,
            title: "Light identity, real trust.",
            body: "First name and a few context cues are enough to feel human. Block and report are visible from day one.",
            accent: "Safe by design",
            icon: "shield.lefthalf.filled"
        ),
        OnboardingStep(
            id: 4,
            title: "Start with what just ended.",
            body: "Pick your current context, then see a live feed right away. Location is only used when it helps you find the right plans.",
            accent: "Context first",
            icon: "sparkles.rectangle.stack.fill"
        ),
    ]

    var body: some View {
        let step = steps[stepIndex]

        VStack(alignment: .leading, spacing: Spacing.xl) {
            Spacer(minLength: 0)

            // Card animates on step change via .id — each new stepIndex is a new view identity
            VStack(alignment: .leading, spacing: Spacing.lg) {
                Image(systemName: step.icon)
                    .font(.system(size: 36, weight: .semibold))
                    .foregroundStyle(Color.appMomentum)
                    .padding(.bottom, Spacing.xs)

                AppBadge(text: step.accent, tone: .appMomentum)

                Text(step.title)
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .fixedSize(horizontal: false, vertical: true)

                Text(step.body)
                    .font(.title3)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .appSurface(prominent: true)
            .id(step.id)
            .transition(.asymmetric(
                insertion: .move(edge: direction).combined(with: .opacity),
                removal: .move(edge: direction == .trailing ? .leading : .trailing).combined(with: .opacity)
            ))

            Spacer(minLength: 0)

            // CTAs
            VStack(spacing: Spacing.sm) {
                Button(stepIndex == steps.count - 1 ? "Show me what's next" : "Continue") {
                    advance()
                }
                .buttonStyle(ActionPillButtonStyle(prominent: true))

                Button(stepIndex == steps.count - 1 ? "Review later" : "Skip") {
                    store.finishOnboarding()
                }
                .buttonStyle(ActionPillButtonStyle())
            }

            // Step indicator
            HStack(spacing: Spacing.xs) {
                ForEach(steps) { current in
                    Capsule()
                        .fill(current.id == step.id ? Color.appAccent : Color.appBorder)
                        .frame(width: current.id == step.id ? 22 : 8, height: 8)
                        .animation(.spring(response: 0.3, dampingFraction: 0.8), value: stepIndex)
                }
            }
            .frame(maxWidth: .infinity)
        }
        .padding(Spacing.xl)
        .background(
            LinearGradient(
                colors: [Color.appBackground, Color.appMomentum.opacity(0.10)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
        )
        .gesture(
            DragGesture(minimumDistance: 40)
                .onEnded { value in
                    if value.translation.width < 0, stepIndex < steps.count - 1 {
                        // Swipe left → advance
                        advance()
                    } else if value.translation.width > 0, stepIndex > 0 {
                        // Swipe right → go back
                        goBack()
                    }
                }
        )
    }

    private func advance() {
        if stepIndex == steps.count - 1 {
            store.finishOnboarding()
        } else {
            direction = .trailing
            withAnimation(.spring(response: 0.35, dampingFraction: 0.82)) {
                stepIndex += 1
            }
        }
    }

    private func goBack() {
        guard stepIndex > 0 else { return }
        direction = .leading
        withAnimation(.spring(response: 0.35, dampingFraction: 0.82)) {
            stepIndex -= 1
        }
    }
}
