import SwiftUI

private struct OnboardingStep: Identifiable {
    let id: Int
    let title: String
    let body: String
    let accent: String
}

struct OnboardingView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @State private var stepIndex = 0

    private let steps = [
        OnboardingStep(
            id: 0,
            title: "Keep the moment going.",
            body: "After Plans is for the few minutes right after something ends, when people are still nearby and the next move is easiest to lose.",
            accent: "See what is happening after"
        ),
        OnboardingStep(
            id: 1,
            title: "Join before you overthink it.",
            body: "The product is built for low-pressure joining, not heavy event planning. Soft signals come first, then the plan firms up.",
            accent: "Join with one tap"
        ),
        OnboardingStep(
            id: 2,
            title: "People you know or are already around.",
            body: "Shared context, known people, and past plan partners outrank stranger discovery. No anonymous random-chat posture.",
            accent: "Bounded context first"
        ),
        OnboardingStep(
            id: 3,
            title: "Light identity, real trust.",
            body: "First name, visible identity cues, and explicit safety hooks help the app feel human without turning setup into homework.",
            accent: "Identity-light, not anonymous"
        ),
        OnboardingStep(
            id: 4,
            title: "Start with the current context.",
            body: "Pick what just ended, then we will show a first feed right away. Location stays `When In Use` and only when it helps the flow.",
            accent: "Show what's next"
        ),
    ]

    var body: some View {
        let step = steps[stepIndex]

        VStack(alignment: .leading, spacing: Spacing.xl) {
            Spacer(minLength: 0)

            VStack(alignment: .leading, spacing: Spacing.lg) {
                AppBadge(text: step.accent, tone: .appMomentum)

                Text(step.title)
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .fixedSize(horizontal: false, vertical: true)

                Text(step.body)
                    .font(.title3)
                    .foregroundStyle(.secondary)

                VStack(alignment: .leading, spacing: Spacing.md) {
                    InfoRow(icon: "bolt.fill", text: "Fast setup before the feed")
                    InfoRow(icon: "person.2.fill", text: "People you know or are already around")
                    InfoRow(icon: "shield.lefthalf.filled", text: "Report and block hooks stay visible from day one")
                }
            }
            .appSurface(prominent: true)

            Spacer(minLength: 0)

            VStack(spacing: Spacing.sm) {
                Button(stepIndex == steps.count - 1 ? "Show what is next" : "Continue") {
                    if stepIndex == steps.count - 1 {
                        store.finishOnboarding()
                    } else {
                        stepIndex += 1
                    }
                }
                .buttonStyle(ActionPillButtonStyle(prominent: true))

                Button(stepIndex == steps.count - 1 ? "Review later" : "Skip ahead") {
                    store.finishOnboarding()
                }
                .buttonStyle(ActionPillButtonStyle())
            }

            HStack(spacing: Spacing.xs) {
                ForEach(steps) { current in
                    Capsule()
                        .fill(current.id == step.id ? Color.appAccent : Color.appBorder)
                        .frame(width: current.id == step.id ? 22 : 8, height: 8)
                }
            }
            .frame(maxWidth: .infinity)
        }
        .padding(Spacing.xl)
        .background(
            LinearGradient(
                colors: [Color.appBackground, Color.appMomentum.opacity(0.12)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
        )
    }
}
