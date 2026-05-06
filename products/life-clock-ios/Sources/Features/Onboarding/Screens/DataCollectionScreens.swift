import SwiftUI

/// Data-collection screens that populate `OnboardingDraft`. Each is small
/// — title, body, an input control, and a Continue CTA. Each fires
/// `screenAppeared` on appear and `screenAdvanced` on tap-Continue.
///
/// Bucketing rule (load-bearing for privacy): sensitive scores are
/// bucketed before `choiceMade(_:key:valueBucket:)`. Raw PSS / UCLA /
/// parent ages-at-death are NEVER passed to the telemetry sink. See
/// `Sources/Services/OnboardingTelemetry.swift` for the helpers.
///
/// All copy is agency-framed per CLAUDE_HANDOFF.md (no doom default,
/// no medical-claim verbs).

// MARK: - Shared scaffold

/// Common chrome around an onboarding form screen: title, body, slot,
/// Continue button. Keeps each screen tiny.
/// A pinned secondary action that sits above the scaffold's primary
/// Continue button. Used for soft-skip patterns (e.g. HealthKit
/// "Not now") where the secondary affordance must be visually adjacent
/// to the primary CTA, not floating in the content body.
struct OnboardingSecondaryAction {
    let label: String
    let caption: String?
    let identifier: String
    let action: () -> Void
}

struct OnboardingScaffold<Content: View>: View {
    let screenID: String
    let title: String
    let bodyText: String?
    let isContinueEnabled: Bool
    let continueLabel: String
    let secondaryAction: OnboardingSecondaryAction?
    let onContinue: () -> Void
    let content: Content

    init(
        screenID: String,
        title: String,
        bodyText: String? = nil,
        isContinueEnabled: Bool = true,
        continueLabel: String = "Continue",
        secondaryAction: OnboardingSecondaryAction? = nil,
        onContinue: @escaping () -> Void,
        @ViewBuilder content: () -> Content
    ) {
        self.screenID = screenID
        self.title = title
        self.bodyText = bodyText
        self.isContinueEnabled = isContinueEnabled
        self.continueLabel = continueLabel
        self.secondaryAction = secondaryAction
        self.onContinue = onContinue
        self.content = content()
    }

    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @Environment(OnboardingDraft.self) private var draft
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        // The mascot/wordmark live in `OnboardingCoordinator` (above the
        // NavigationStack) so they keep stable view identity across
        // pushes. This scaffold only renders the per-screen body.
        VStack(alignment: .leading, spacing: 24) {
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.title.bold())
                if let bodyText {
                    Text(bodyText)
                        .font(.body)
                        .foregroundStyle(.secondary)
                }
            }
            content
            Spacer()
            Button(action: {
                telemetry.value.screenAdvanced(screenID, durationMs: 0)
                // Recompute the running estimate so the next screen's
                // header mascot reflects this answer's delta. The
                // coordinator-level reactor also recomputes on input
                // mutations; this Continue-time call guarantees the
                // post-answer state is committed before navigation.
                draft.recomputeEstimate(using: ClockEngine(clock: store.clock))
                onContinue()
            }) {
                Text(continueLabel)
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(isContinueEnabled ? Color.accentColor : Color.gray.opacity(0.4))
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .disabled(!isContinueEnabled)
            .accessibilityIdentifier("onboarding.continue")
            if let secondaryAction {
                // Stacked BELOW the primary CTA (visually) but laid out
                // AFTER it in the VStack so the primary stays pinned at
                // the same y as every other screen's Continue. Earlier
                // ordering (secondary above primary) drifted the primary
                // up ~65pt on screens with a soft-skip — broke the
                // muscle-memory tap target.
                VStack(spacing: 4) {
                    Button(secondaryAction.label, action: secondaryAction.action)
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)
                        .font(.callout)
                        .accessibilityIdentifier(secondaryAction.identifier)
                    if let caption = secondaryAction.caption {
                        Text(caption)
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                            .multilineTextAlignment(.center)
                    }
                }
                .frame(maxWidth: .infinity)
            }
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 24)
        // Container ID for screen-existence checks. `children: .contain`
        // keeps inner Continue/option-button identifiers intact — without
        // it, SwiftUI flattens this VStack into a single element and the
        // outer id shadows every interactive child, breaking
        // `app.buttons["onboarding.continue"]` and the per-option ids.
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("onboarding.\(screenID)")
        .onAppear { telemetry.value.screenAppeared(screenID) }
    }
}

// MARK: - Personalize intro

struct GoalPickView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "goalPick",
            title: "What brings you here?",
            bodyText: "Pick the one that fits today.",
            isContinueEnabled: draft.primaryGoal != nil,
            onContinue: onContinue
        ) {
            VStack(spacing: 8) {
                ForEach(OnboardingGoal.allCases) { goal in
                    Button {
                        draft.primaryGoal = goal
                        telemetry.value.choiceMade("goalPick", key: "goal", valueBucket: goal.rawValue)
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(goal.displayName).font(.body.bold())
                                Text(goal.detail).font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            if draft.primaryGoal == goal {
                                Image(systemName: "checkmark.circle.fill").foregroundStyle(.tint)
                            }
                        }
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("onboarding.goal.\(goal.rawValue)")
                }
            }
        }
    }
}

// MARK: - Baseline

struct BaselineDOBView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    @State private var localDate: Date = {
        var components = DateComponents()
        components.year = 1990
        components.month = 6
        components.day = 12
        return Calendar(identifier: .gregorian).date(from: components) ?? Date()
    }()

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "baselineDOB",
            title: "When were you born?",
            bodyText: "Your clock starts here. Stays on this device.",
            onContinue: {
                draft.birthDate = localDate
                onContinue()
            }
        ) {
            DatePicker(
                "Birth date",
                selection: $localDate,
                in: ...Date(),
                displayedComponents: .date
            )
            .datePickerStyle(.wheel)
            .labelsHidden()
            .accessibilityIdentifier("onboarding.baselineDOB.picker")
        }
    }
}

struct BaselineSexView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    private let options: [(rawValue: String, label: String)] = [
        ("female", "Female"),
        ("male", "Male"),
        ("unspecified", "Prefer not to say"),
    ]

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "baselineSex",
            title: "Biological sex",
            bodyText: "Used only for the population baseline (CDC FastStats).",
            isContinueEnabled: draft.biologicalSex != nil,
            onContinue: onContinue
        ) {
            VStack(spacing: 8) {
                ForEach(options, id: \.rawValue) { opt in
                    pickRow(opt: opt, draft: draft)
                }
            }
        }
    }

    @ViewBuilder
    private func pickRow(
        opt: (rawValue: String, label: String),
        draft: OnboardingDraft
    ) -> some View {
        @Bindable var draft = draft
        Button {
            draft.biologicalSex = opt.rawValue
        } label: {
            HStack {
                Text(opt.label)
                Spacer()
                if draft.biologicalSex == opt.rawValue {
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(.tint)
                }
            }
            .padding()
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("onboarding.baselineSex.\(opt.rawValue)")
    }
}

// MARK: - Body composition

struct BodyCompView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    @State private var unitSystem: BodyMeasurementSystem = .standard
    @State private var enabled: Bool = false

    /// Free-form numeric inputs — typing is much faster than +/- 1 stepping
    /// across realistic body-measurement ranges (66–440 lb, 3–7 ft, 0–11
    /// in, 120–220 cm, 30–200 kg).
    @State private var feetString: String = "5"
    @State private var inchesString: String = "8"
    @State private var poundsString: String = "150"
    @State private var cmString: String = "170"
    @State private var kgString: String = "70"

    private static let intFormatter: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.maximumFractionDigits = 0
        f.allowsFloats = false
        return f
    }()

    private func parseInt(_ s: String) -> Int? {
        let trimmed = s.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty,
              let n = Self.intFormatter.number(from: trimmed)?.intValue
        else { return nil }
        return n
    }

    /// Parsed feet+inches → height-cm; nil if either field is invalid or
    /// outside a sane range.
    private var standardHeightCm: Double? {
        guard let ft = parseInt(feetString), (3...7).contains(ft),
              let inch = parseInt(inchesString), (0...11).contains(inch)
        else { return nil }
        return Double(ft * 12 + inch) * 2.54
    }

    private var standardWeightKg: Double? {
        guard let lb = parseInt(poundsString), (66...440).contains(lb)
        else { return nil }
        return Double(lb) / 2.20462
    }

    private var metricHeightCm: Double? {
        guard let cm = parseInt(cmString), (120...220).contains(cm)
        else { return nil }
        return Double(cm)
    }

    private var metricWeightKg: Double? {
        guard let kg = parseInt(kgString), (30...200).contains(kg)
        else { return nil }
        return Double(kg)
    }

    private var resolvedHeightCm: Double? {
        unitSystem == .standard ? standardHeightCm : metricHeightCm
    }

    private var resolvedWeightKg: Double? {
        unitSystem == .standard ? standardWeightKg : metricWeightKg
    }

    /// Continue is enabled if the user opted out (Skip) or if both
    /// height and weight parse to in-range values.
    private var continueEnabled: Bool {
        if !enabled { return true }
        return resolvedHeightCm != nil && resolvedWeightKg != nil
    }

    /// Debounced live commit of parsed height + weight to the draft.
    /// Free-form numeric typing means intermediate strings ("1" mid-typing
    /// "170") would feed the engine garbage; debouncing 400ms after the
    /// last keystroke + gating on `parsesAndInRange` keeps the live
    /// mascot reaction useful without flicker. Cancelled on disappear so
    /// a navigated-away screen can't write stale values.
    @State private var bodyCompCommit: Task<Void, Never>?

    private func scheduleBodyCompCommit() {
        bodyCompCommit?.cancel()
        bodyCompCommit = Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(400))
            guard !Task.isCancelled, enabled else { return }
            if let h = resolvedHeightCm, let w = resolvedWeightKg {
                draft.heightCm = h
                draft.weightKg = w
            }
        }
    }

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "bodyComp",
            title: "Height & weight",
            bodyText: "Optional — drives the BMI lever. Skip if you'd rather not.",
            isContinueEnabled: continueEnabled,
            continueLabel: enabled ? "Continue" : "Skip",
            onContinue: {
                if enabled, let h = resolvedHeightCm, let w = resolvedWeightKg {
                    draft.heightCm = h
                    draft.weightKg = w
                }
                onContinue()
            }
        ) {
            Toggle("Include", isOn: $enabled)
            if enabled {
                Picker("Unit system", selection: $unitSystem) {
                    ForEach(BodyMeasurementSystem.allCases) { system in
                        Text(system.displayName).tag(system)
                    }
                }
                .pickerStyle(.segmented)
                .accessibilityIdentifier("onboarding.bodyComp.unitSystem")

                switch unitSystem {
                case .standard:
                    HStack {
                        Text("Height")
                        Spacer()
                        numericField(text: $feetString,
                                     identifier: "onboarding.bodyComp.feet",
                                     suffix: "ft")
                        numericField(text: $inchesString,
                                     identifier: "onboarding.bodyComp.inches",
                                     suffix: "in")
                    }
                    HStack {
                        Text("Weight")
                        Spacer()
                        numericField(text: $poundsString,
                                     identifier: "onboarding.bodyComp.pounds",
                                     suffix: "lb",
                                     width: 100)
                    }
                case .metric:
                    HStack {
                        Text("Height")
                        Spacer()
                        numericField(text: $cmString,
                                     identifier: "onboarding.bodyComp.cm",
                                     suffix: "cm",
                                     width: 100)
                    }
                    HStack {
                        Text("Weight")
                        Spacer()
                        numericField(text: $kgString,
                                     identifier: "onboarding.bodyComp.kg",
                                     suffix: "kg",
                                     width: 100)
                    }
                }
            }
        }
        .onChange(of: feetString) { _, _ in scheduleBodyCompCommit() }
        .onChange(of: inchesString) { _, _ in scheduleBodyCompCommit() }
        .onChange(of: poundsString) { _, _ in scheduleBodyCompCommit() }
        .onChange(of: cmString) { _, _ in scheduleBodyCompCommit() }
        .onChange(of: kgString) { _, _ in scheduleBodyCompCommit() }
        .onChange(of: enabled) { _, _ in scheduleBodyCompCommit() }
        .onChange(of: unitSystem) { _, _ in scheduleBodyCompCommit() }
        .onDisappear { bodyCompCommit?.cancel() }
    }

    @ViewBuilder
    private func numericField(
        text: Binding<String>,
        identifier: String,
        suffix: String,
        width: CGFloat = 80
    ) -> some View {
        HStack(spacing: 4) {
            TextField("", text: text)
                .keyboardType(.numberPad)
                .multilineTextAlignment(.trailing)
                .frame(maxWidth: width)
                .textFieldStyle(.roundedBorder)
                .accessibilityIdentifier(identifier)
            Text(suffix)
                .font(.callout)
                .foregroundStyle(.secondary)
        }
    }
}

enum BodyMeasurementSystem: String, CaseIterable, Identifiable {
    case standard
    case metric

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .standard: return "Standard"
        case .metric: return "Metric"
        }
    }
}

// MARK: - Existing lifestyle (smoking / alcohol / strength / cardio / sleep / diet)

struct SmokingView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    private let options: [(value: String, label: String)] = [
        ("none", "Never"),
        ("former", "Former"),
        ("light", "Occasional"),
        ("heavy", "Daily"),
    ]

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "smoking",
            title: "Smoking",
            isContinueEnabled: draft.smokingStatus != nil,
            onContinue: onContinue
        ) {
            optionList(
                screenID: "smoking",
                key: "status",
                options: options,
                selection: $draft.smokingStatus
            )
        }
    }
}

struct AlcoholView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    private let options: [(value: String, label: String)] = [
        ("rare", "Rarely or never"),
        ("frequent", "A few times a week"),
        ("heavy", "Most days"),
    ]

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "alcohol",
            title: "Alcohol",
            isContinueEnabled: draft.alcoholFrequency != nil,
            onContinue: onContinue
        ) {
            optionList(
                screenID: "alcohol",
                key: "frequency",
                options: options,
                selection: $draft.alcoholFrequency
            )
        }
    }
}

struct StrengthView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    @State private var perWeek: Int = 0

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "strength",
            title: "Strength training",
            bodyText: "How many times a week, on average?",
            onContinue: {
                draft.strengthFrequencyPerWeek = perWeek
                onContinue()
            }
        ) {
            Stepper("\(perWeek) sessions per week", value: $perWeek, in: 0...7)
                // Mirror to the draft live so the header mascot reacts to
                // each step, not just to Continue. The coordinator's 80ms
                // debounce coalesces rapid taps.
                .onChange(of: perWeek) { _, new in
                    draft.strengthFrequencyPerWeek = new
                }
        }
    }
}

struct CardioView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    @State private var minsPerWeek: Int = 0

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "cardio",
            title: "Cardio",
            bodyText: "Minutes per week of walking, running, cycling, or similar.",
            onContinue: {
                draft.cardioMinsPerWeek = minsPerWeek
                onContinue()
            }
        ) {
            Stepper("\(minsPerWeek) min/week", value: $minsPerWeek, in: 0...600, step: 30)
                .onChange(of: minsPerWeek) { _, new in
                    draft.cardioMinsPerWeek = new
                }
        }
    }
}

struct SleepView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    @State private var hours: Double = 7.5

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "sleep",
            title: "Sleep target",
            bodyText: "How many hours do you aim for most nights?",
            onContinue: {
                draft.sleepGoalHours = hours
                onContinue()
            }
        ) {
            Stepper(value: $hours, in: 4...12, step: 0.5) {
                Text(String(format: "%.1f hours", hours))
            }
            .onChange(of: hours) { _, new in
                draft.sleepGoalHours = new
            }
        }
    }
}

struct DietView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    private let options: [(value: String, label: String)] = [
        ("great", "Great"),
        ("okay", "Okay"),
        ("rough", "Rough"),
    ]

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "diet",
            title: "Your typical diet",
            bodyText: "Pick the bucket your typical week falls into.",
            isContinueEnabled: draft.dietQualityBaseline != nil,
            onContinue: onContinue
        ) {
            optionList(
                screenID: "diet",
                key: "quality",
                options: options,
                selection: $draft.dietQualityBaseline
            )
        }
    }
}

// MARK: - Sensitive consent + family longevity

struct SensitiveConsentView: View {
    let onContinue: () -> Void
    let onSkip: () -> Void

    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            VStack(alignment: .leading, spacing: 8) {
                Text("A few sensitive questions.")
                    .font(.title.bold())
                Text("These help calibrate your clock — covering family history, stress, and connection. Stored only on your device, never sent off.")
                    .font(.body)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button(action: {
                telemetry.value.choiceMade("sensitiveConsent", key: "consent", valueBucket: "yes")
                telemetry.value.screenAdvanced("sensitiveConsent", durationMs: 0)
                onContinue()
            }) {
                Text("Continue")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .accessibilityIdentifier("onboarding.continue")

            Button(action: {
                telemetry.value.choiceMade("sensitiveConsent", key: "consent", valueBucket: "skip")
                telemetry.value.screenAdvanced("sensitiveConsent", durationMs: 0)
                onSkip()
            }) {
                Text("Skip these")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .foregroundStyle(.secondary)
            }
            .accessibilityIdentifier("onboarding.skipSensitive")
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 24)
        .onAppear { telemetry.value.screenAppeared("sensitiveConsent") }
        .accessibilityIdentifier("onboarding.sensitiveConsent")
    }
}

struct FamilyMotherView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    var body: some View {
        familyView(
            screenID: "familyMother",
            title: "Your mother",
            aliveBinding: { draft.parentMotherAlive = $0 },
            ageBinding: { draft.parentMotherAgeAtDeath = $0 },
            onContinue: onContinue
        )
    }
}

struct FamilyFatherView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    var body: some View {
        familyView(
            screenID: "familyFather",
            title: "Your father",
            aliveBinding: { draft.parentFatherAlive = $0 },
            ageBinding: { draft.parentFatherAgeAtDeath = $0 },
            onContinue: onContinue
        )
    }
}

private func familyView(
    screenID: String,
    title: String,
    aliveBinding: @escaping (Bool?) -> Void,
    ageBinding: @escaping (Int?) -> Void,
    onContinue: @escaping () -> Void
) -> some View {
    FamilyLongevityForm(
        screenID: screenID,
        title: title,
        aliveBinding: aliveBinding,
        ageBinding: ageBinding,
        onContinue: onContinue
    )
}

private struct FamilyLongevityForm: View {
    let screenID: String
    let title: String
    let aliveBinding: (Bool?) -> Void
    let ageBinding: (Int?) -> Void
    let onContinue: () -> Void

    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @State private var alive: Bool? = nil
    @State private var ageString: String = ""
    @State private var preferNotToSay = false
    /// Debounced live commit so the header mascot reacts to the parental-
    /// longevity answer during input rather than only on Continue. 400ms
    /// after the last keystroke avoids the "user typing 120 hits 1 first
    /// → engine sees age=1 → estimate dives → 30ms later sees 12 → estimate
    /// dives more" flicker.
    @State private var commitTask: Task<Void, Never>?

    private func scheduleCommit() {
        commitTask?.cancel()
        commitTask = Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(400))
            guard !Task.isCancelled else { return }
            if preferNotToSay {
                aliveBinding(nil)
                ageBinding(nil)
                return
            }
            aliveBinding(alive)
            if alive == false, let age = parsedAge {
                ageBinding(age)
            } else if alive != false {
                ageBinding(nil)
            }
        }
    }

    /// Parsed age, or nil if the field is empty / out of range. The
    /// 0…120 bound covers every plausible age-at-death; the lower bound
    /// is permissive (perinatal loss) by deliberate UX choice — the
    /// stepper's 20-floor was wrong for that case.
    /// Parse the user's typed age, accepting locale-shaped numerals
    /// (Arabic-Indic, Devanagari, Latin) via `NumberFormatter` rather
    /// than the ASCII-only `Int(_:)` initializer. Empty / unparseable /
    /// out-of-range returns nil.
    private static let ageFormatter: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.maximumFractionDigits = 0
        f.allowsFloats = false
        return f
    }()

    private var parsedAge: Int? {
        let trimmed = ageString.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty,
              let n = Self.ageFormatter.number(from: trimmed)?.intValue,
              (0...120).contains(n) else { return nil }
        return n
    }

    private var continueEnabled: Bool {
        if preferNotToSay { return true }
        if alive == true || alive == nil { return alive != nil }
        // alive == false → require a parsed age.
        return parsedAge != nil
    }

    var body: some View {
        OnboardingScaffold(
            screenID: screenID,
            title: title,
            bodyText: "Helps calibrate the genetic-anchor signal. Skip if difficult.",
            isContinueEnabled: continueEnabled,
            onContinue: {
                if preferNotToSay {
                    aliveBinding(nil)
                    ageBinding(nil)
                } else {
                    aliveBinding(alive)
                    if alive == false, let age = parsedAge {
                        ageBinding(age)
                        telemetry.value.choiceMade(screenID, key: "ageBucket",
                            valueBucket: ParentLongevityBucket.bucket(for: age))
                    }
                }
                onContinue()
            }
        ) {
            VStack(alignment: .leading, spacing: 12) {
                Toggle("Prefer not to say", isOn: $preferNotToSay)
                if !preferNotToSay {
                    Picker("Status", selection: Binding(
                        get: { alive },
                        set: { alive = $0 }
                    )) {
                        Text("Living").tag(Bool?.some(true))
                        Text("Passed away").tag(Bool?.some(false))
                        Text("Don't know").tag(Bool?.none)
                    }
                    .pickerStyle(.segmented)

                    if alive == false {
                        // Numeric TextField (no placeholder — the
                        // screen's title carries the prompt; an "e.g.
                        // 62" example would anchor the answer on a
                        // sensitive value).
                        HStack {
                            Text("Age at passing")
                            Spacer()
                            TextField("", text: $ageString)
                                .keyboardType(.numberPad)
                                .multilineTextAlignment(.trailing)
                                .frame(maxWidth: 80)
                                .textFieldStyle(.roundedBorder)
                                .accessibilityIdentifier("onboarding.familyAgeAtDeath")
                        }
                    }
                }
            }
            .onChange(of: alive) { _, _ in scheduleCommit() }
            .onChange(of: ageString) { _, _ in scheduleCommit() }
            .onChange(of: preferNotToSay) { _, _ in scheduleCommit() }
            .onDisappear { commitTask?.cancel() }
        }
    }
}

// MARK: - Stress + social

struct StressView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @State private var score: Double = 14

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "stress",
            title: "Stress, in general",
            bodyText: "Where would you place yourself, on average, over the past month?",
            onContinue: {
                let intScore = Int(score.rounded())
                draft.perceivedStressScore = intScore
                telemetry.value.choiceMade("stress", key: "pss",
                    valueBucket: PerceivedStressBucket.bucket(for: intScore))
                onContinue()
            }
        ) {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("Calm").font(.caption2).foregroundStyle(.secondary)
                    Slider(value: $score, in: 0...40, step: 1)
                        .accessibilityIdentifier("onboarding.stress.slider")
                    Text("Stretched").font(.caption2).foregroundStyle(.secondary)
                }
            }
            .onChange(of: score) { _, new in
                draft.perceivedStressScore = Int(new.rounded())
            }
        }
    }
}

struct SocialView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @State private var score: Double = 4

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "social",
            title: "Connection",
            bodyText: "Most days, do you feel surrounded by people who get you?",
            onContinue: {
                let intScore = Int(score.rounded())
                draft.lonelinessScore = intScore
                telemetry.value.choiceMade("social", key: "ucla",
                    valueBucket: LonelinessBucket.bucket(for: intScore))
                onContinue()
            }
        ) {
            HStack {
                Text("Often").font(.caption2).foregroundStyle(.secondary)
                Slider(value: $score, in: 3...9, step: 1)
                    .accessibilityIdentifier("onboarding.social.slider")
                Text("Rarely").font(.caption2).foregroundStyle(.secondary)
            }
            .onChange(of: score) { _, new in
                draft.lonelinessScore = Int(new.rounded())
            }
        }
    }
}

// MARK: - Tone + prior attempts

struct ToneView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "tone",
            title: "Voice",
            bodyText: "How should your clock talk to you?",
            isContinueEnabled: draft.toneMode != nil,
            onContinue: onContinue
        ) {
            VStack(spacing: 8) {
                ForEach(ToneMode.allCases) { tone in
                    Button {
                        draft.toneMode = tone
                    } label: {
                        HStack {
                            Text(tone.displayName)
                            Spacer()
                            if draft.toneMode == tone {
                                Image(systemName: "checkmark.circle.fill").foregroundStyle(.tint)
                            }
                        }
                        .padding()
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("onboarding.tone.\(tone.rawValue)")
                }
            }
        }
    }
}

struct PriorAttemptsView: View {
    let onContinue: () -> Void
    @Environment(OnboardingDraft.self) private var draft

    var body: some View {
        @Bindable var draft = draft
        return OnboardingScaffold(
            screenID: "priorAttempts",
            title: "Have you tried tracking before?",
            isContinueEnabled: draft.priorAttempts != nil,
            onContinue: onContinue
        ) {
            VStack(spacing: 8) {
                ForEach(PriorAttempts.allCases) { attempt in
                    Button {
                        draft.priorAttempts = attempt
                    } label: {
                        HStack {
                            Text(attempt.displayName)
                            Spacer()
                            if draft.priorAttempts == attempt {
                                Image(systemName: "checkmark.circle.fill").foregroundStyle(.tint)
                            }
                        }
                        .padding()
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("onboarding.priorAttempts.\(attempt.rawValue)")
                }
            }
        }
    }
}

// MARK: - HealthKit auth

struct HealthKitAuthView: View {
    let onContinue: () -> Void
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @State private var hasRequested = false
    @State private var isRequesting = false

    /// Soft-skip handler — used by the scaffold's secondary action slot
    /// so the "Not now" affordance sits visually adjacent to the
    /// primary Connect button at the bottom of the screen, not adrift
    /// in the content body. Skip path must NOT call
    /// `requestHealthAuthorization` (a denied system prompt persists
    /// until the user digs into iOS Settings → Health).
    private func softSkip() {
        telemetry.value.choiceMade("healthKitAuth", key: "decision",
                                   valueBucket: "skipped")
        telemetry.value.screenAdvanced("healthKitAuth", durationMs: 0)
        onContinue()
    }

    var body: some View {
        OnboardingScaffold(
            screenID: "healthKitAuth",
            title: "Let your clock learn from your body.",
            bodyText: "Read steps, exercise, sleep, and resting heart rate from Apple Health. You can change this any time in Settings.",
            continueLabel: hasRequested ? "Continue" : "Connect",
            secondaryAction: hasRequested ? nil : OnboardingSecondaryAction(
                label: "Not now",
                caption: "You can connect Apple Health any time from Profile.",
                identifier: "onboarding.healthKitAuth.skip",
                action: softSkip
            ),
            onContinue: {
                if !hasRequested {
                    Task {
                        isRequesting = true
                        await store.requestHealthAuthorization()
                        isRequesting = false
                        hasRequested = store.lastHealthAuthError == nil || store.healthAuthorizationKnown
                    }
                } else {
                    // HealthKit deliberately hides the actual grant /
                    // deny outcome from the calling app — `healthAuthorizationKnown`
                    // is true for both. Record `prompted` and let
                    // downstream sample-read success / failure tell us
                    // what they actually picked.
                    telemetry.value.choiceMade("healthKitAuth", key: "decision",
                                               valueBucket: "prompted")
                    telemetry.value.screenAdvanced("healthKitAuth", durationMs: 0)
                    onContinue()
                }
            }
        ) {
            VStack(alignment: .leading, spacing: 12) {
                if isRequesting {
                    ProgressView()
                }
                if let error = store.lastHealthAuthError {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                }
            }
        }
    }
}

// MARK: - Helpers

@ViewBuilder
private func optionList(
    screenID: String,
    key: String,
    options: [(value: String, label: String)],
    selection: Binding<String?>
) -> some View {
    OptionListView(screenID: screenID, key: key, options: options, selection: selection)
}

private struct OptionListView: View {
    let screenID: String
    let key: String
    let options: [(value: String, label: String)]
    @Binding var selection: String?
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        VStack(spacing: 8) {
            ForEach(options, id: \.value) { opt in
                Button {
                    selection = opt.value
                    telemetry.value.choiceMade(screenID, key: key, valueBucket: opt.value)
                } label: {
                    HStack {
                        Text(opt.label)
                        Spacer()
                        if selection == opt.value {
                            Image(systemName: "checkmark.circle.fill").foregroundStyle(.tint)
                        }
                    }
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("onboarding.\(screenID).\(opt.value)")
            }
        }
    }
}
