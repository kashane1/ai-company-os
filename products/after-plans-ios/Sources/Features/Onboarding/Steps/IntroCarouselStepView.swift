import SwiftUI

private struct IntroSlide: Identifiable {
    let id: Int
    let title: String
    let body: String
    let accent: String
    let icon: String
}

struct IntroCarouselStepView: View {
    var onContinue: () -> Void
    var onSkip: () -> Void

    @State private var stepIndex = 0
    @State private var direction: Edge = .trailing

    private let slides: [IntroSlide] = [
        IntroSlide(id: 0, title: "Keep the moment going.", body: "After Plans is for the few minutes right after something ends — when people are still nearby and the next move is easiest to make.", accent: "See what happens after", icon: "arrow.forward.circle.fill"),
        IntroSlide(id: 1, title: "Join before you overthink it.", body: "Signal interest with one tap. Soft signals come first, so there's no pressure to commit before the plan takes shape.", accent: "Low-pressure joining", icon: "hand.thumbsup.fill"),
        IntroSlide(id: 2, title: "People you know or are already around.", body: "Shared context, known faces, and past plan partners come first. This is not a public discovery feed or a stranger-matching app.", accent: "Bounded trust", icon: "person.2.fill"),
        IntroSlide(id: 3, title: "Light identity, real trust.", body: "First name and a few context cues are enough to feel human. Block and report are visible from day one.", accent: "Safe by design", icon: "shield.lefthalf.filled"),
        IntroSlide(id: 4, title: "Start with what just ended.", body: "Pick your current context, then see a live feed right away — built around the people you were just with, not a generic crowd.", accent: "Context first", icon: "sparkles.rectangle.stack.fill"),
    ]

    var body: some View {
        let slide = slides[stepIndex]
        VStack(alignment: .leading, spacing: Spacing.xl) {
            Spacer(minLength: 0)
            VStack(alignment: .leading, spacing: Spacing.lg) {
                Image(systemName: slide.icon)
                    .font(.system(size: 36, weight: .semibold))
                    .foregroundStyle(Color.appMomentum)
                    .padding(.bottom, Spacing.xs)
                AppBadge(text: slide.accent, tone: .appMomentum)
                Text(slide.title)
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .fixedSize(horizontal: false, vertical: true)
                Text(slide.body)
                    .font(.title3)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .appSurface(prominent: true)
            .id(slide.id)
            .transition(.asymmetric(
                insertion: .move(edge: direction).combined(with: .opacity),
                removal: .move(edge: direction == .trailing ? .leading : .trailing).combined(with: .opacity)
            ))

            Spacer(minLength: 0)

            VStack(spacing: Spacing.sm) {
                Button(stepIndex == slides.count - 1 ? "Tell us your name" : "Continue") {
                    advance()
                }
                .buttonStyle(ActionPillButtonStyle(prominent: true))

                Button(stepIndex == slides.count - 1 ? "Skip the rest" : "Skip") {
                    onSkip()
                }
                .buttonStyle(ActionPillButtonStyle())
            }

            HStack(spacing: Spacing.xs) {
                ForEach(slides) { current in
                    Capsule()
                        .fill(current.id == slide.id ? Color.appAccent : Color.appBorder)
                        .frame(width: current.id == slide.id ? 22 : 8, height: 8)
                        .animation(.spring(response: 0.3, dampingFraction: 0.8), value: stepIndex)
                }
            }
            .frame(maxWidth: .infinity)
        }
        .padding(Spacing.xl)
        .gesture(
            DragGesture(minimumDistance: 40)
                .onEnded { value in
                    if value.translation.width < 0, stepIndex < slides.count - 1 {
                        advance()
                    } else if value.translation.width > 0, stepIndex > 0 {
                        goBack()
                    }
                }
        )
    }

    private func advance() {
        if stepIndex == slides.count - 1 {
            onContinue()
        } else {
            direction = .trailing
            withAnimation(.spring(response: 0.35, dampingFraction: 0.82)) { stepIndex += 1 }
        }
    }

    private func goBack() {
        guard stepIndex > 0 else { return }
        direction = .leading
        withAnimation(.spring(response: 0.35, dampingFraction: 0.82)) { stepIndex -= 1 }
    }
}
