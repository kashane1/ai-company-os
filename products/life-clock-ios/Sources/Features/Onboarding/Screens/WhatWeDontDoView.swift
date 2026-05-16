import SwiftUI

/// Credibility beat between `analyzing` and `archetypeReveal`. Three
/// bullet lines pre-empt the doom-app suspicion right at the moment the
/// user is bracing for it: no death date, no streak shame, no verdicts.
///
/// Tone-aware copy comes from `RevealCopy.whatWeDontDo*`. The user-tier
/// softened register isn't applied here on purpose — the message is the
/// same regardless of how stressed/lonely the user is. The voice
/// register varies; the differentiation doesn't.
struct WhatWeDontDoView: View {
    let onContinue: () -> Void

    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// One-shot stagger so the bullets land like a beat, not a wall of
    /// text. `0` = nothing visible yet, `3` = all visible. Reduce Motion
    /// short-circuits to all visible immediately.
    @State private var visibleCount: Int = 0

    private var tone: ToneMode {
        draft.toneMode ?? .coach
    }

    var body: some View {
        let bullets = RevealCopy.whatWeDontDoBullets(tone: tone)
        return OnboardingScaffold(
            screenID: "whatWeDontDo",
            title: RevealCopy.whatWeDontDoTitle(tone: tone),
            onContinue: onContinue
        ) {
            VStack(alignment: .leading, spacing: 16) {
                ForEach(Array(bullets.enumerated()), id: \.offset) { idx, line in
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        Image(systemName: "xmark")
                            .font(.body.weight(.semibold))
                            .foregroundStyle(.secondary)
                            .frame(width: 20)
                        Text(line)
                            .font(.body)
                    }
                    .opacity(idx < visibleCount ? 1 : 0)
                    .offset(x: idx < visibleCount ? 0 : -12)
                    .animation(
                        reduceMotion ? nil : .easeOut(duration: Motion.Duration.beat),
                        value: visibleCount
                    )
                    .accessibilityIdentifier("onboarding.whatWeDontDo.bullet.\(idx)")
                }

                // Footer reframes the negative bullets as a positive
                // stance, so the screen doesn't end on three "no"s.
                Text(RevealCopy.whatWeDontDoFooter(tone: tone))
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .padding(.top, 4)
                    .opacity(visibleCount >= bullets.count ? 1 : 0)
                    .animation(
                        reduceMotion ? nil : .easeOut(duration: Motion.Duration.beat),
                        value: visibleCount
                    )
                    .accessibilityIdentifier("onboarding.whatWeDontDo.footer")
            }
        }
        .onAppear {
            telemetry.value.screenAppeared("whatWeDontDo")
            staggerBullets(count: bullets.count)
        }
    }

    private func staggerBullets(count: Int) {
        if reduceMotion {
            visibleCount = count
            return
        }
        for idx in 0..<count {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.14 * Double(idx + 1)) {
                visibleCount = idx + 1
            }
        }
    }
}
