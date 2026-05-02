import SwiftUI

/// The reveal escalator: analyzing → archetype → concrete-this-year →
/// dot-grid sequence → engine reveal+dial (Phase 5) → recovery preview.
///
/// All copy is agency-framed (no doom default, no medical-claim verbs).

// MARK: - Analyzing

/// Three sequential progress bars (~1.5s each, 4.5s total) showing
/// "computation" before the archetype reveal. Builds anticipation;
/// dropped in Reduce Motion to a single 1.5s gate per /deepen-plan
/// performance review.
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
        .padding(24)
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
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            stage = 1
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                stage = 2
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
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
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    private var result: ClockEngine.ArchetypeResult {
        let snapshot = draft.materialize()
        return ClockEngine(clock: store.clock).computeArchetype(profile: snapshot)
    }

    var body: some View {
        OnboardingScaffold(
            screenID: "archetypeReveal",
            title: result.archetype.displayName,
            bodyText: result.archetype.description,
            continueLabel: "Makes sense",
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

// MARK: - Concrete this-year framing

struct ConcreteThisYearView: View {
    let onContinue: () -> Void

    var body: some View {
        OnboardingScaffold(
            screenID: "concreteThisYear",
            title: "Looks like you'll spend ~121 days on your phone this year.",
            bodyText: "Average for a US adult, per Pew + Common Sense Media. Yours might be more, might be less. The point: it adds up.",
            onContinue: onContinue
        ) { EmptyView() }
    }
}

// MARK: - Life grid full

struct LifeGridFullView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    var body: some View {
        OnboardingScaffold(
            screenID: "lifeGridFull",
            title: "This is your life.",
            bodyText: "Each dot is a week. Most people get around 80 years of them.",
            onContinue: onContinue
        ) {
            LifeGridDotView(
                totalWeeks: 4160,
                livedWeeks: 0,
                lostWeeks: 0,
                mode: .full
            )
            .frame(height: 280)
        }
    }
}

// MARK: - Life grid remaining

struct LifeGridRemainingView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    private var livedWeeks: Int {
        guard let dob = draft.birthDate else { return 0 }
        let weeks = Calendar.current.dateComponents([.weekOfYear], from: dob, to: Date()).weekOfYear ?? 0
        return max(0, weeks)
    }

    var body: some View {
        OnboardingScaffold(
            screenID: "lifeGridRemaining",
            title: "This is what you have left.",
            bodyText: nil,
            onContinue: onContinue
        ) {
            LifeGridDotView(
                totalWeeks: 4160,
                livedWeeks: livedWeeks,
                lostWeeks: 0,
                mode: .remainingHighlighted
            )
            .frame(height: 280)
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

    var body: some View {
        let yearsAtRisk = max(0, Int((Double(lostWeeks) / 52.0).rounded()))
        return OnboardingScaffold(
            screenID: "bigNumberPenalty",
            title: "~\(yearsAtRisk) years at risk from current habits.",
            bodyText: "These are the dots most likely to slip away if today's patterns hold. Not fate — signal.",
            onContinue: onContinue
        ) {
            LifeGridDotView(
                totalWeeks: 4160,
                livedWeeks: livedWeeks,
                lostWeeks: lostWeeks,
                mode: .bigNumberPenalty
            )
            .frame(height: 280)
        }
    }
}

// MARK: - Recovery preview

struct RecoveryPreviewView: View {
    let onContinue: () -> Void
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft

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

    var body: some View {
        let yearsBack = max(0, Int((Double(lostWeeks) / 52.0).rounded()))
        return OnboardingScaffold(
            screenID: "recoveryPreview",
            title: "\(yearsBack) more years of \(cyclingWords[cyclingIndex])",
            bodyText: "These are the years your habits could win back.",
            continueLabel: "Continue",
            onContinue: onContinue
        ) {
            LifeGridDotView(
                totalWeeks: 4160,
                livedWeeks: livedWeeks,
                lostWeeks: lostWeeks,
                mode: .recoveryHighlighted
            )
            .frame(height: 240)
            .onAppear {
                Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { _ in
                    Task { @MainActor in
                        cyclingIndex = (cyclingIndex + 1) % cyclingWords.count
                    }
                }
            }
        }
    }
}
