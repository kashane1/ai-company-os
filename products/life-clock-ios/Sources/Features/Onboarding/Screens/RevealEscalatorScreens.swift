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
// UCLA ≥ 6 (low connection). When both fire, the reveal-tier screens render
// the softer copy variant (now via `RevealCopy.healthspanRevealTitle(... softened:)`).
// Median user still gets the original register; only the subset flagged by
// SafetyNet's target population sees the softened reveal.
//
// 2026-05-14: the old `RevealEscalatorGentleCopy` constants were removed
// alongside the dot-grid screens they served. Softened-register copy
// now lives in `RevealCopy.swift` keyed on `(tone, softened)`.

/// Whether the reveal escalator should render the gentle-register copy
/// based on the user's PSS + UCLA inputs from the consent screens.
@MainActor
func revealUsesSofterRegister(draft: OnboardingDraft) -> Bool {
    let stressed = (draft.perceivedStressScore ?? 0) >= 27
    let lonely = (draft.lonelinessScore ?? 0) >= 6
    return stressed && lonely
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

    /// Whether the uncertainty detail modal is open (tap on the "first
    /// read" chip beneath the meters). Surfacing the "confidence shipped
    /// not hidden" principle in-flow rather than burying it in Profile.
    @State private var showingUncertaintyDetail = false

    private var result: ClockEngine.ArchetypeResult {
        let snapshot = draft.materialize()
        return ClockEngine(clock: store.clock).computeArchetype(profile: snapshot)
    }

    /// Engine-computed top lever for the current draft. The lever-guess
    /// payoff block reads this and `draft.leverGuess` together to decide
    /// whether to render the "called it" or "most guess wrong" prefix.
    private var engineTopLever: LifeClockLever {
        let snapshot = draft.materialize()
        return ClockEngine(clock: store.clock).topLever(profile: snapshot)
    }

    private var tone: ToneMode {
        draft.toneMode ?? .coach
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
                // Lever-guess payoff: only rendered when the user
                // answered `leverGuess` (the screen right before
                // analyzing). Confirms or surprises depending on whether
                // their guess matches the engine's top lever.
                if let guess = draft.leverGuess {
                    leverPayoffBlock(guess: guess)
                }
                // Uncertainty chip — tappable, opens a detail sheet
                // explaining how the first read is computed. Honors
                // the "confidence shipped, not hidden" repo principle.
                uncertaintyChip
            }
        }
        .onAppear { runArchetypePulse() }
        .onDisappear { mascotOverride.minutes = nil }
        .sheet(isPresented: $showingUncertaintyDetail) {
            uncertaintyDetailSheet
        }
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

    @ViewBuilder
    private func leverPayoffBlock(guess: LifeClockLever) -> some View {
        let top = engineTopLever
        VStack(alignment: .leading, spacing: 4) {
            Text(RevealCopy.leverPayoffPrefix(tone: tone, guess: guess, top: top))
                .font(.caption.bold())
                .foregroundStyle(.secondary)
            Text(RevealCopy.leverPayoffBody(tone: tone, top: top))
                .font(.callout)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.accentColor.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .accessibilityIdentifier("onboarding.archetypeReveal.leverPayoff")
    }

    @ViewBuilder
    private var uncertaintyChip: some View {
        Button { showingUncertaintyDetail = true } label: {
            HStack(spacing: 6) {
                Image(systemName: "info.circle")
                    .font(.caption.weight(.semibold))
                Text(RevealCopy.uncertaintyChip(tone: tone))
                    .font(.caption)
                    .multilineTextAlignment(.leading)
                Spacer()
            }
            .foregroundStyle(.secondary)
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("onboarding.archetypeReveal.uncertaintyChip")
    }

    @ViewBuilder
    private var uncertaintyDetailSheet: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("How we got this")
                    .font(.title3.bold())
                Spacer()
                Button {
                    showingUncertaintyDetail = false
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .accessibilityIdentifier("onboarding.archetypeReveal.uncertaintyClose")
            }
            Text(RevealCopy.uncertaintyDetail(tone: tone))
                .font(.body)
            Spacer()
        }
        .padding(24)
        .presentationDetents([.medium])
    }
}

// MARK: - Recovery preview
//
// 2026-05-14 onboarding revamp: dot-grid recovery preview replaced by
// an interactive slider screen. The user's *top lever* is unlocked;
// dragging it up ticks the big year-count up and triggers the mascot
// reaction. Same component as `ReactiveSliderView` (lead-in demo) and
// `HealthspanRevealView` (read-only reveal) — the visual is now
// load-bearing across all three reveal moments.
//
// The forward-looking framing (a goal-keyed cycling phrase) is preserved
// because that was the only piece of the dot-grid version that earned
// its place — it personalized the future the user is about to drag
// toward. Headline still cycles, just below the slider instead of above
// a dot wall.

struct RecoveryPreviewView: View {
    let onContinue: () -> Void
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @Environment(MascotOverride.self) private var mascotOverride
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var cyclingIndex: Int = 0
    /// Engine baseline projection cached on appear. Same caching shape
    /// as `EngineRevealAndDialView` — the snapshot inputs don't mutate
    /// while this screen is visible, so a single computation is enough.
    @State private var engineYears: Double = 0
    /// Engine-computed top lever, cached on appear. `.unanswered` ⇒
    /// the dragger falls back to neutral copy and binds against
    /// `.sleep` as a visual placeholder.
    @State private var topLever: LifeClockLever = .unanswered
    /// User's current drag position for the unlocked lever, 0..1.
    /// Initialized from the engine's normalized driver position so
    /// the slider lands at the user's current value, not 0.5.
    @State private var leverValue: Double = 0.5
    /// Baseline driver position (the user's actual answer for the top
    /// lever). Used to compute "earned years" = (current − baseline) ×
    /// gain factor — so dragging back down to the baseline returns
    /// `+0 years`, not a negative number.
    @State private var baselineLeverValue: Double = 0.5

    private var goal: OnboardingGoal {
        draft.primaryGoal ?? .justCurious
    }

    private var tone: ToneMode {
        draft.toneMode ?? .coach
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

    /// Max years a user can "earn" by dragging the unlocked lever from
    /// their current answer all the way to the best extreme. Chosen so
    /// the headline reads as meaningful (1..5 years) without exceeding
    /// the engine's actual single-lever bound. Coefficients in
    /// `lifestyleAdjustmentYears` mean the strongest single lever
    /// (smoking → never smoked) is worth ~8y; we cap user-facing
    /// recovery gain at 5y because the lever guess is one of five and
    /// we want the chip to feel earned, not arbitrary.
    private static let maxEarnableYears: Double = 5.0

    /// Years currently earned vs the user's baseline answer. Negative
    /// values clamp at zero (dragging worse than baseline doesn't
    /// register as "earned" — it'd contradict the screen's intent).
    private var earnedYears: Int {
        let delta = max(0.0, leverValue - baselineLeverValue)
        let raw = delta * Self.maxEarnableYears
        return Int(raw.rounded())
    }

    /// Projected total when the user is at the current slider position.
    /// Engine-computed baseline + the same per-lever gain math we use
    /// for the chip. Renders as the big number.
    private var projectedTotalYears: Double {
        engineYears + (max(0.0, leverValue - baselineLeverValue) * Self.maxEarnableYears)
    }

    /// Mascot kick scales with earned years so dragging up reads as a
    /// gain. Linear, capped so the dial-screen settle behavior isn't
    /// overshadowed.
    private var mascotDelta: Int {
        let years = projectedTotalYears - engineYears
        let bounded = max(-1.5, min(Self.maxEarnableYears, years))
        return Int((bounded / Self.maxEarnableYears * 90.0).rounded())
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Headline + cycling sub-phrase: forward-looking framing
            // preserved from the dot-grid version. The headline cycles
            // tone-aware copy under it.
            VStack(spacing: 6) {
                Text(RevealCopy.recoveryPreviewHeadline(tone: tone))
                    .font(.title.bold())
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("onboarding.recoveryPreview.headline")
                Text(RevealCopy.recoveryPreviewSubline(tone: tone, lever: topLever))
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("onboarding.recoveryPreview.subline")
            }
            .frame(maxWidth: .infinity)

            // Big number — engine baseline + earned years.
            Text(String(format: "%.0f years", projectedTotalYears))
                .font(.system(size: 56, weight: .semibold, design: .rounded))
                .contentTransition(.numericText(value: projectedTotalYears))
                .animation(reduceMotion ? nil : .snappy, value: leverValue)
                .frame(maxWidth: .infinity)
                .accessibilityIdentifier("onboarding.recoveryPreview.years")

            // Unlocked slider for the top lever.
            LifeClockSliderRow(
                label: leverLabel,
                leadingExtremeLabel: leadingExtremeLabel,
                trailingExtremeLabel: trailingExtremeLabel,
                value: $leverValue,
                mode: .interactive,
                identifierSuffix: "recoveryPreview.lever"
            )

            // Goal-keyed cycling phrase keeps the destination personal.
            Text(cyclingPhrase)
                .font(.title3)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, minHeight: 56, alignment: .center)
                .contentTransition(.opacity)
                .animation(reduceMotion ? nil : .easeInOut(duration: Motion.Duration.beat), value: cyclingIndex)
                .accessibilityIdentifier("onboarding.recoveryPreview.cyclingPhrase")

            // Earned-years chip — only visible when the user has dragged
            // above their baseline. Reads as "+N years available."
            if earnedYears > 0 {
                Text(earnedChipCopy)
                    .font(.caption.bold())
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.accentColor.opacity(0.15))
                    .clipShape(Capsule())
                    .frame(maxWidth: .infinity)
                    .accessibilityIdentifier("onboarding.recoveryPreview.earnedChip")
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
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("onboarding.recoveryPreview")
        .onAppear { configureOnAppear() }
        .onChange(of: leverValue) { _, _ in
            mascotOverride.minutes = mascotDelta
        }
        .onDisappear {
            mascotOverride.minutes = nil
        }
    }

    private func configureOnAppear() {
        telemetry.value.screenAppeared("recoveryPreview")
        let snapshot = draft.materialize()
        let engine = ClockEngine(clock: store.clock)
        engineYears = engine.calculateBaseline(profile: snapshot).projectedAgeYears
        // Top lever drives which row unlocks. Fallback to `.sleep` when
        // the engine returns `.unanswered` so we never render a blank
        // lever label.
        let computed = engine.topLever(profile: snapshot)
        topLever = (computed == .unanswered) ? .sleep : computed
        let positions = engine.normalizedDriverPositions(profile: snapshot)
        baselineLeverValue = positions[topLever] ?? 0.5
        leverValue = baselineLeverValue
        mascotOverride.minutes = mascotDelta

        // Goal-keyed cycling phrase animation.
        Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { _ in
            Task { @MainActor in
                cyclingIndex = (cyclingIndex + 1) % cyclingWords.count
            }
        }
    }

    private var leverLabel: String { topLever.displayName }

    private var cyclingPhrase: String {
        let phrase = cyclingWords[cyclingIndex]
        if phrase.hasPrefix("with ") || phrase.hasPrefix("at ") {
            return phrase
        }
        return "of \(phrase)"
    }

    private var earnedChipCopy: String {
        switch tone {
        case .gentle: return "+\(earnedYears) years available"
        case .coach: return "+\(earnedYears) years available"
        case .firmDirect: return "+\(earnedYears)y on the table"
        }
    }

    // Lever-extreme labels mirror those on `HealthspanRevealView` so a
    // user sees the same anchors on both screens. Single source of
    // truth could pull this from `LifeClockLever`; leaving local for
    // now because the recovery screen may diverge (e.g. softer
    // "rested" wording).
    private var leadingExtremeLabel: String {
        switch topLever {
        case .sleep: return "Short"
        case .movement: return "Sedentary"
        case .food: return "Rough"
        case .drinking: return "Heavy"
        case .stressRecovery: return "Stretched"
        case .unanswered: return ""
        }
    }

    private var trailingExtremeLabel: String {
        switch topLever {
        case .sleep: return "Rested"
        case .movement: return "Active"
        case .food: return "Whole foods"
        case .drinking: return "Rare"
        case .stressRecovery: return "Steady"
        case .unanswered: return ""
        }
    }
}
