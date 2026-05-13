import SwiftUI

/// The reveal escalator: analyzing → archetype → concrete-this-year →
/// dot-grid sequence → engine reveal+dial (Phase 5) → recovery preview.
///
/// All copy is agency-framed (no doom default, no medical-claim verbs).

// MARK: - Reveal-escalator inferred-softer register
//
// Vision-question #9 resolved 2026-05-12 — option (c): the reveal escalator
// softens its register when the user's just-collected stress + connection
// signals say they may not be in a state to receive the dramatic default.
// Thresholds match the existing telemetry buckets: PSS ≥ 27 (Stretched) and
// UCLA ≥ 6 (low connection). When both fire, the two screens that carry
// the most dramatic copy (`LifeGridRemainingView`, `BigNumberPenaltyView`)
// render the gentle-register variant and show an inline affordance pointing
// the user to Profile to switch back to a sharper voice. Median user still
// gets the original dramatic register; only the subset flagged by SafetyNet's
// target population sees the softened reveal. See
// `docs/products/life-clock/polish-2026-05-12-vision-q9-reveal-escalator-tone-mocks.md`.

/// Whether the reveal escalator should render the gentle-register copy
/// based on the user's PSS + UCLA inputs from the consent screens.
@MainActor
func revealUsesSofterRegister(draft: OnboardingDraft) -> Bool {
    let stressed = (draft.perceivedStressScore ?? 0) >= 27
    let lonely = (draft.lonelinessScore ?? 0) >= 6
    return stressed && lonely
}

/// Gentle-register copy for the two reveal screens whose default voice is
/// most dramatic. Coach copy stays in the views as the literal default.
enum RevealEscalatorGentleCopy {
    static let lifeGridTitle = "These weeks are still yours."
    static let lifeGridBody = "Each dot is a week your habits help shape."

    static func bigNumberTitle(yearsAtRisk: Int) -> String {
        "About \(yearsAtRisk) years to shape."
    }
    static let bigNumberBody = "These are years your everyday choices can lift. Small steps add up; today is a fine place to start."

    /// Inline affordance shown beneath the softened body so the inferred
    /// behavior is visible and reversible.
    static let toneSwitchAffordance = "Prefer a sharper read? Switch tone in Profile anytime."
}

// MARK: - Analyzing

/// Three sequential progress bars (~0.8s each, 2.4s total) showing
/// "computation" before the archetype reveal. Builds anticipation;
/// dropped in Reduce Motion to a single 1.5s gate per /deepen-plan
/// performance review. Earlier 1.5s/stage felt like filler — the
/// archetype is the payoff, not the loading bar.
struct AnalyzingView: View {
    let onContinue: () -> Void
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var stage: Int = 0

    private let labels = [
        "Reading your inputs…",
        "Calibrating against population data…",
        "Generating your timeline…",
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Spacer()
            ForEach(0..<3, id: \.self) { idx in
                VStack(alignment: .leading, spacing: 6) {
                    Text(labels[idx])
                        .font(.body.bold())
                        .foregroundStyle(idx <= stage ? .primary : .tertiary)
                    ProgressView(
                        value: idx < stage ? 1.0 : (idx == stage ? 0.5 : 0.0),
                        total: 1.0
                    )
                    .tint(idx <= stage ? .accentColor : .gray)
                }
            }
            Spacer()
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 24)
        .accessibilityIdentifier("onboarding.analyzing")
        .onAppear {
            telemetry.value.screenAppeared("analyzing")
            // Compute the archetype before advancing so the next screen
            // can read from the draft. Engine call is rules-based and
            // cheap.
            let snapshot = draft.materialize()
            let result = ClockEngine(clock: store.clock)
                .computeArchetype(profile: snapshot)
            draft.recomputeEstimate(using: ClockEngine(clock: store.clock))

            // Persist archetype back to the draft so the reveal screen
            // can read it.
            draft.materialize()  // no-op extraction; fields stay on draft
            // Update the draft's archetype directly via materialize-style
            // mirror.
            persistArchetypeOnDraft(result.archetype)

            advanceStages()
        }
    }

    private func persistArchetypeOnDraft(_ archetype: Archetype) {
        // Stash on the materialize path: write into the draft as a
        // late-bound field. Simpler: surface via a dedicated property
        // on OnboardingDraft. We store on UserProfile at completion;
        // the reveal screen recomputes from the profile then.
        //
        // For now, stash on a holder we attach via task-local storage.
        // The archetype reveal screen recomputes itself from the same
        // engine call — deterministic, identical inputs → identical
        // result.
    }

    private func advanceStages() {
        if reduceMotion {
            stage = 3
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { advance() }
            return
        }
        let perStage = 0.8
        DispatchQueue.main.asyncAfter(deadline: .now() + perStage) {
            stage = 1
            DispatchQueue.main.asyncAfter(deadline: .now() + perStage) {
                stage = 2
                DispatchQueue.main.asyncAfter(deadline: .now() + perStage) {
                    stage = 3
                    advance()
                }
            }
        }
    }

    private func advance() {
        telemetry.value.screenAdvanced("analyzing", durationMs: 0)
        onContinue()
    }
}

// MARK: - Archetype reveal

struct ArchetypeRevealView: View {
    let onContinue: () -> Void
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft
    @Environment(MascotOverride.self) private var mascotOverride
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    private var result: ClockEngine.ArchetypeResult {
        let snapshot = draft.materialize()
        return ClockEngine(clock: store.clock).computeArchetype(profile: snapshot)
    }

    /// Pulse magnitude scales with recovery capacity so a "Marathoner"
    /// (high recovery) gets a brighter forward swing than someone with
    /// slow recovery — the mascot signals the archetype, not just
    /// movement. Capped at ±120 min so it stays in "breath" territory.
    private var pulseMinutes: Int {
        let signed = (result.recoveryCapacity * 2 - 1)  // [-1, 1]
        return Int((signed * 120).rounded())
    }

    var body: some View {
        OnboardingScaffold(
            screenID: "archetypeReveal",
            title: result.archetype.displayName,
            bodyText: result.archetype.description,
            continueLabel: "Got it",
            onContinue: {
                // No persistence here — archetype writes to UserProfile
                // at completeOnboarding via materialize().
                onContinue()
            }
        ) {
            VStack(alignment: .leading, spacing: 16) {
                meterRow(
                    label: "Behavioral risk",
                    value: result.behavioralRisk,
                    leading: "Low",
                    trailing: "High"
                )
                meterRow(
                    label: "Recovery capacity",
                    value: result.recoveryCapacity,
                    leading: "Slow",
                    trailing: "Strong"
                )
            }
        }
        .onAppear { runArchetypePulse() }
        .onDisappear { mascotOverride.minutes = nil }
    }

    /// Brief reactivity beat tied to the archetype: pulse, settle to a
    /// recovery-capacity-shaped value, then release back to the
    /// per-answer running estimate. Reads as "the clock noticed you".
    private func runArchetypePulse() {
        mascotOverride.minutes = pulseMinutes
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            mascotOverride.minutes = pulseMinutes / 2
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                mascotOverride.minutes = nil
            }
        }
    }

    @ViewBuilder
    private func meterRow(
        label: String,
        value: Double,
        leading: String,
        trailing: String
    ) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            ProgressView(value: value, total: 1.0).tint(.accentColor)
            HStack {
                Text(leading).font(.caption2).foregroundStyle(.tertiary)
                Spacer()
                Text(trailing).font(.caption2).foregroundStyle(.tertiary)
            }
        }
    }
}

// MARK: - Life grid remaining
//
// Absorbs the former `lifeGridFull` intro (removed 2026-05-03 — see
// `OnboardingScreen.deprecatedScreens`). Single title, no two-beat
// auto-advance.

struct LifeGridRemainingView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    private var livedWeeks: Int {
        guard let dob = draft.birthDate else { return 0 }
        let weeks = Calendar.current.dateComponents([.weekOfYear], from: dob, to: Date()).weekOfYear ?? 0
        return max(0, weeks)
    }

    private var softened: Bool { revealUsesSofterRegister(draft: draft) }

    private var copy: (title: String, body: String) {
        if softened {
            return (RevealEscalatorGentleCopy.lifeGridTitle,
                    RevealEscalatorGentleCopy.lifeGridBody)
        }
        return ("This is what's still ahead.",
                "Each dot is a week your habits get to shape.")
    }

    var body: some View {
        OnboardingScaffold(
            screenID: "lifeGridRemaining",
            title: copy.title,
            bodyText: copy.body,
            onContinue: onContinue
        ) {
            VStack(spacing: 8) {
                LifeGridDotView(
                    totalWeeks: 4160,
                    livedWeeks: livedWeeks,
                    lostWeeks: 0,
                    mode: .remainingHighlighted
                )
                .frame(height: 280)
                // Single-color screen: inline caption, no full legend
                // block (it'd be two-thirds redundant). Full legend
                // appears on the next colored screen.
                Text("Filled green = lived. Outlined = still ahead.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if softened {
                    Text(RevealEscalatorGentleCopy.toneSwitchAffordance)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .padding(.top, 8)
                        .accessibilityIdentifier("onboarding.lifeGridRemaining.toneSwitchAffordance")
                }
            }
        }
    }
}

// MARK: - Big number penalty

struct BigNumberPenaltyView: View {
    let onContinue: () -> Void
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft

    private var lostWeeks: Int {
        // Approximate "years at risk" from the lifestyle penalty.
        let snapshot = draft.materialize()
        let baselineYears = baseline(for: snapshot.biologicalSex)
        let projected = ClockEngine(clock: store.clock)
            .calculateBaseline(profile: snapshot)
            .projectedAgeYears
        let delta = baselineYears - projected
        return max(0, Int((delta * 52.0).rounded()))
    }

    private var livedWeeks: Int {
        guard let dob = draft.birthDate else { return 0 }
        return max(0, Calendar.current.dateComponents([.weekOfYear], from: dob, to: Date()).weekOfYear ?? 0)
    }

    private func baseline(for sex: String) -> Double {
        switch sex.lowercased() {
        case "male", "m": return 76.5
        case "female", "f": return 81.4
        default: return 79.0
        }
    }

    private var softened: Bool { revealUsesSofterRegister(draft: draft) }

    private func copy(yearsAtRisk: Int) -> (title: String, body: String) {
        if softened {
            return (RevealEscalatorGentleCopy.bigNumberTitle(yearsAtRisk: yearsAtRisk),
                    RevealEscalatorGentleCopy.bigNumberBody)
        }
        return ("~\(yearsAtRisk) years on the table.",
                "These are the years your current habits put within reach to win or lose. The clock follows what you do next.")
    }

    var body: some View {
        let yearsAtRisk = max(0, Int((Double(lostWeeks) / 52.0).rounded()))
        let c = copy(yearsAtRisk: yearsAtRisk)
        return OnboardingScaffold(
            screenID: "bigNumberPenalty",
            title: c.title,
            bodyText: c.body,
            onContinue: onContinue
        ) {
            VStack(spacing: 12) {
                LifeGridDotView(
                    totalWeeks: 4160,
                    livedWeeks: livedWeeks,
                    lostWeeks: lostWeeks,
                    mode: .bigNumberPenalty
                )
                .frame(height: 280)
                // First multi-color screen — full legend introduces the
                // green/red/gray triad. Subsequent recovery screen falls
                // back to an info-popover (progressive disclosure).
                LifeGridDotLegend(mode: .bigNumberPenalty)
                if softened {
                    Text(RevealEscalatorGentleCopy.toneSwitchAffordance)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .padding(.top, 4)
                        .accessibilityIdentifier("onboarding.bigNumberPenalty.toneSwitchAffordance")
                }
            }
        }
    }
}

// MARK: - Recovery preview

struct RecoveryPreviewView: View {
    let onContinue: () -> Void
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var cyclingIndex: Int = 0

    private var goal: OnboardingGoal {
        draft.primaryGoal ?? .justCurious
    }

    private var cyclingWords: [String] {
        switch goal {
        case .liveLonger: return ["living", "loving", "exploring"]
        case .moreEnergy: return ["feeling alive", "on the trail", "awake at dawn"]
        case .beThereForFamily: return ["with your kids", "showing up", "at the dinner table"]
        case .beatFamilyHistory: return ["outliving the odds", "rewriting the story"]
        case .justCurious: return ["showing up", "noticing", "being here"]
        }
    }

    private var lostWeeks: Int {
        let snapshot = draft.materialize()
        let baselineYears = ClockEngine(clock: store.clock).calculateBaseline(profile: snapshot).projectedAgeYears
        let basePop: Double
        switch snapshot.biologicalSex.lowercased() {
        case "male", "m": basePop = 76.5
        case "female", "f": basePop = 81.4
        default: basePop = 79.0
        }
        let delta = basePop - baselineYears
        return max(0, Int((delta * 52.0).rounded()))
    }

    private var livedWeeks: Int {
        guard let dob = draft.birthDate else { return 0 }
        return max(0, Calendar.current.dateComponents([.weekOfYear], from: dob, to: Date()).weekOfYear ?? 0)
    }

    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        // Custom layout (not via OnboardingScaffold) because this
        // screen wants a centered hero and a stable, fixed-height
        // cycling phrase line. Previously the cycling word was
        // concatenated into the scaffold's left-aligned title, which
        // pushed the whole page up/down each tick as the title wrapped
        // 1↔2 lines. Now the first line is fixed copy ("N more years")
        // and only the second line cycles inside a height-clamped frame.
        let yearsBack = max(0, Int((Double(lostWeeks) / 52.0).rounded()))
        return VStack(alignment: .leading, spacing: 24) {
            VStack(spacing: 6) {
                Text(RecoveryPreviewCopy.headline(yearsBack: yearsBack))
                    .font(.title.bold())
                    .multilineTextAlignment(.center)
                    .accessibilityIdentifier("onboarding.recoveryPreview.headline")
                Text(RecoveryPreviewCopy.phrase(
                    goal: goal,
                    phrase: cyclingWords[cyclingIndex]
                ))
                    .font(.title3)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity, minHeight: 56, alignment: .center)
                    .contentTransition(.opacity)
                    .animation(reduceMotion ? nil : .easeInOut(duration: Motion.Duration.beat), value: cyclingIndex)
                    .accessibilityIdentifier("onboarding.recoveryPreview.cyclingPhrase")
            }
            .frame(maxWidth: .infinity)

            VStack(spacing: 8) {
                LifeGridDotView(
                    totalWeeks: 4160,
                    livedWeeks: livedWeeks,
                    lostWeeks: lostWeeks,
                    mode: .recoveryHighlighted
                )
                .frame(height: 240)
                LifeGridDotLegend(mode: .recoveryHighlighted)
            }

            Spacer()

            Button(action: onContinue) {
                Text("Continue")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .accessibilityIdentifier("onboarding.continue")
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 24)
        // `children: .contain` keeps inner identifiers (the Continue
        // button's `onboarding.continue`, the cycling-phrase id, the
        // headline id) intact. Without it, SwiftUI flattens this VStack
        // into a single accessibility element and the outer screen id
        // shadows every child — `app.buttons["onboarding.continue"]`
        // returns nothing. OnboardingScaffold takes the same approach;
        // matching it here avoids the asymmetry.
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("onboarding.recoveryPreview")
        .onAppear {
            telemetry.value.screenAppeared("recoveryPreview")
            Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { _ in
                Task { @MainActor in
                    cyclingIndex = (cyclingIndex + 1) % cyclingWords.count
                }
            }
        }
    }
}

struct RecoveryPreviewCopy {
    /// Fixed first line of the recovery hero — never reflows.
    static func headline(yearsBack: Int) -> String {
        guard yearsBack > 0 else { return "More years ahead" }
        return "\(yearsBack) more years"
    }

    /// Second line — the cycling phrase. The connector ("of " vs " ")
    /// matches the goal so the line reads naturally even when the cycle
    /// hits a "with your kids" / "at the dinner table" phrase that
    /// already starts with a preposition.
    static func phrase(goal: OnboardingGoal, phrase: String) -> String {
        if phrase.hasPrefix("with ") || phrase.hasPrefix("at ") {
            return phrase
        }
        return "of \(phrase)"
    }
}
