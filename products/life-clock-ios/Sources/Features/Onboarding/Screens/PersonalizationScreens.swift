import SwiftUI

/// Two new selection screens added 2026-05-14:
///
/// - `HabitFailureModeView` — sits right after `tone`. One question
///   ("What usually breaks your habits?") with five chips. Drives the
///   personalized paywall headline and the receipt screen's coaching
///   line. Doesn't change the engine's clock estimate at all — pure
///   copy personalization.
///
/// - `LeverGuessView` — sits between `priorAttempts` and `analyzing`.
///   "Which habit do you think moves your clock most?" The archetype
///   reveal will compare this guess against the engine's computed top
///   lever to either confirm or surprise the user.
///
/// Both screens use the standard `OnboardingScaffold` so they pick up
/// the persistent header mascot, telemetry hooks, and Continue button
/// behavior automatically.

// MARK: - HabitFailureMode

struct HabitFailureModeView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "habitFailureMode",
            title: "What usually breaks your habits?",
            bodyText: "Pick the one that feels closest. We'll keep this in mind.",
            isContinueEnabled: draft.habitFailureMode != nil,
            onContinue: onContinue
        ) {
            VStack(spacing: 8) {
                ForEach(HabitFailureMode.selectableCases) { mode in
                    Button {
                        draft.habitFailureMode = mode
                        telemetry.value.choiceMade(
                            "habitFailureMode",
                            key: "mode",
                            valueBucket: mode.rawValue
                        )
                    } label: {
                        HStack {
                            Text(mode.displayName)
                                .font(.body)
                            Spacer()
                            if draft.habitFailureMode == mode {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.tint)
                            }
                        }
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("onboarding.habitFailureMode.\(mode.rawValue)")
                }
            }
        }
    }
}

// MARK: - LeverGuess

struct LeverGuessView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "leverGuess",
            title: "Which habit moves your clock most?",
            bodyText: "Your best guess — we'll show you what the data says next.",
            isContinueEnabled: draft.leverGuess != nil,
            onContinue: onContinue
        ) {
            VStack(spacing: 8) {
                ForEach(LifeClockLever.selectableCases) { lever in
                    Button {
                        draft.leverGuess = lever
                        telemetry.value.choiceMade(
                            "leverGuess",
                            key: "lever",
                            valueBucket: lever.rawValue
                        )
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(lever.displayName).font(.body.bold())
                                Text(lever.detail)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if draft.leverGuess == lever {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.tint)
                            }
                        }
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("onboarding.leverGuess.\(lever.rawValue)")
                }
            }
        }
    }
}
