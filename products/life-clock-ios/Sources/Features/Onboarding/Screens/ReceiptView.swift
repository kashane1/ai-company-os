import SwiftUI

/// "What you taught the clock" — input receipt shown between
/// `healthKitAuth` and `paywallPrimary`. Confirms what the user has
/// already invested, so the paywall reads as the natural way to keep
/// that investment paying off rather than a wall.
///
/// **What it shows:** a grid of small chips, each labelling one of the
/// signals the user actually answered. Skipped fields aren't shown —
/// the count in the title reflects real answers only. Tone-aware
/// footer (keyed off `habitFailureMode`) adds a one-line coaching
/// frame for the paywall they're about to see.
///
/// **What it doesn't do:** no value-prop language ("Pro adds..."), no
/// upgrade CTA, no feature comparison. The receipt is a thank-you
/// beat, not a soft pitch. The pitch comes on the next screen.
struct ReceiptView: View {
    let onContinue: () -> Void

    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    private var tone: ToneMode {
        draft.toneMode ?? .coach
    }

    private var failureMode: HabitFailureMode {
        draft.habitFailureMode ?? .unanswered
    }

    /// All non-empty signals — order is meaningful (presentation flows
    /// from identity → lifestyle → sensitive → onboarding-only). Each
    /// entry is a (label, value) pair where the label is a noun phrase
    /// the user will recognize from the screen they answered it on.
    private var receiptChips: [(label: String, value: String)] {
        var chips: [(label: String, value: String)] = []

        if let goal = draft.primaryGoal {
            chips.append(("Why", goal.displayName.lowercased()))
        }
        if let dob = draft.birthDate {
            let years = Calendar.current.dateComponents([.year], from: dob, to: Date()).year ?? 0
            chips.append(("Age", "\(years)"))
        }
        if let sex = draft.biologicalSex, sex != "unspecified" {
            chips.append(("Sex", sex.capitalized))
        }
        if draft.heightCm != nil || draft.weightKg != nil {
            chips.append(("Body", "shared"))
        }
        if let smoking = draft.smokingStatus {
            chips.append(("Smoking / nicotine", smoking.capitalized))
        }
        if let alcohol = draft.alcoholFrequency {
            chips.append(("Drinking", alcohol.capitalized))
        }
        if let strength = draft.strengthFrequencyPerWeek {
            chips.append(("Strength", "\(strength)×/wk"))
        }
        if let cardio = draft.cardioMinsPerWeek {
            chips.append(("Cardio", "\(cardio)m/wk"))
        }
        if let sleep = draft.sleepGoalHours {
            chips.append(("Sleep", String(format: "%.0fh", sleep)))
        }
        if let diet = draft.dietQualityBaseline {
            chips.append(("Food", diet.capitalized))
        }
        if draft.parentMotherAlive != nil || draft.parentFatherAlive != nil {
            chips.append(("Family", "shared"))
        }
        if draft.perceivedStressScore != nil {
            chips.append(("Stress", "shared"))
        }
        if draft.lonelinessScore != nil {
            chips.append(("Connection", "shared"))
        }
        if let tone = draft.toneMode {
            chips.append(("Voice", tone.displayName))
        }
        if let attempts = draft.priorAttempts {
            chips.append(("History", attempts.displayName))
        }
        if let mode = draft.habitFailureMode {
            chips.append(("Sticking point", mode.displayName))
        }
        if let guess = draft.leverGuess {
            chips.append(("Your guess", guess.displayName))
        }
        return chips
    }

    var body: some View {
        let chips = receiptChips
        return OnboardingScaffold(
            screenID: "receipt",
            title: RevealCopy.receiptTitle(tone: tone, signalCount: chips.count),
            bodyText: nil,
            onContinue: onContinue
        ) {
            VStack(alignment: .leading, spacing: 16) {
                ReceiptChipGrid(chips: chips)
                Text(RevealCopy.receiptFooter(tone: tone, failureMode: failureMode))
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .padding(.top, 4)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("onboarding.receipt.footer")
            }
        }
    }
}

/// Flowing chip grid — wraps to as many rows as needed. Each chip
/// renders the label muted and the value emphasized so the screen
/// reads as "the data the clock has, at a glance," not as a form
/// rendering of every answer.
private struct ReceiptChipGrid: View {
    let chips: [(label: String, value: String)]

    /// Adaptive grid lets the chips wrap naturally on any device width.
    /// 110pt minimum lines up with the longest label ("Sticking point")
    /// at default text size; longer values truncate to the second line.
    private let columns: [GridItem] = [
        GridItem(.adaptive(minimum: 110), spacing: 8),
    ]

    var body: some View {
        LazyVGrid(columns: columns, alignment: .leading, spacing: 8) {
            ForEach(Array(chips.enumerated()), id: \.offset) { idx, chip in
                VStack(alignment: .leading, spacing: 2) {
                    Text(chip.label.uppercased())
                        .font(.caption2.weight(.semibold))
                        .tracking(0.5)
                        .foregroundStyle(.tertiary)
                    Text(chip.value)
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                        .minimumScaleFactor(0.85)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .accessibilityIdentifier("onboarding.receipt.chip.\(idx)")
            }
        }
    }
}
