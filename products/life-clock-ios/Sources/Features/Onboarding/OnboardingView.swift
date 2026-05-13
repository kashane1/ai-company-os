import SwiftUI

struct OnboardingView: View {
    @Environment(LifeClockStore.self) private var store
    @State private var step: Int = 0
    @State private var birthDate: Date = {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "UTC")!
        return cal.date(from: DateComponents(year: 1990, month: 6, day: 12)) ?? Date(timeIntervalSince1970: 0)
    }()
    @State private var biologicalSex: String = "unspecified"
    @State private var smokingStatus: String = "none"
    @State private var alcoholFrequency: String = "rare"
    @State private var dietQualityBaseline: String = "okay"
    @State private var sleepGoalHours: Double = 7.5
    @State private var strengthFrequency: Int = 2
    @State private var toneMode: ToneMode = .coach
    @State private var disclaimerAccepted: Bool = false
    @State private var permissionRequestInFlight: Bool = false

    private let totalSteps = 7
    @State private var reminderRequestInFlight: Bool = false
    @State private var reminderDecisionMade: Bool = false

    /// True iff the picked birthDate makes the user ≥18 today. Drives the
    /// age-gate on smoking/alcohol baseline pickers (Q12 — 12+ rating with
    /// in-app gating). Uses the store's injected clock so this stays
    /// deterministic under test.
    private var isAdultBirthDate: Bool {
        AgeGate.isAdult(
            birthDate: birthDate,
            asOf: store.clock.now(),
            calendar: store.clock.calendar
        )
    }

    var body: some View {
        VStack(spacing: 0) {
            ProgressView(value: Double(step + 1), total: Double(totalSteps))
                .padding(.horizontal, DesignTokens.Spacing.lg)
                .padding(.top, DesignTokens.Spacing.md)

            ScrollView {
                Group {
                    switch step {
                    case 0: valueScreen
                    case 1: safetyScreen
                    case 2: baselineScreen
                    case 3: toneScreen
                    case 4: permissionEducationScreen
                    case 5: dailyReminderScreen
                    case 6: revealScreen
                    default: revealScreen
                    }
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }

            footer
        }
    }

    // MARK: - Steps

    private var valueScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Build health-supporting momentum.")
                .font(.largeTitle.bold())
            Text("Life Clock helps you notice how daily habits influence your health trajectory. Food choices, sleep, movement, and consistency can add visible progress over time.")
                .foregroundStyle(.secondary)
            Text("You do not need calorie counting or perfect tracking. A short daily check-in and Apple Health data are enough to start seeing patterns.")
                .foregroundStyle(.secondary)
            Text("This is a habit tracker and motivation tool, not a medical prediction.")
                .foregroundStyle(.secondary)
        }
        .accessibilityIdentifier("onboarding.value")
    }

    private var safetyScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Your clock is an estimate, not fate.")
                .font(.title2.bold())
            DisclaimerBanner()
            Toggle(isOn: $disclaimerAccepted) {
                Text("I understand Life Clock provides educational estimates — not medical advice or a lifespan prediction.")
                    .font(.callout)
            }
            .padding(.top, DesignTokens.Spacing.sm)
            .accessibilityIdentifier("onboarding.disclaimerToggle")
        }
        .accessibilityIdentifier("onboarding.safety")
    }

    private var baselineScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("A few quick baselines")
                .font(.title2.bold())
            Text("These help us tailor your starting progress view. You can update them later.")
                .foregroundStyle(.secondary)
            DatePicker("Date of birth", selection: $birthDate, displayedComponents: .date)
                .accessibilityIdentifier("onboarding.birthDate")
            Picker("Biological sex (optional)", selection: $biologicalSex) {
                Text("Prefer not to say").tag("unspecified")
                Text("Female").tag("female")
                Text("Male").tag("male")
            }
            .accessibilityIdentifier("onboarding.biologicalSex")
            .accessibilityValue(biologicalSex)
            if isAdultBirthDate {
                Picker("Smoking", selection: $smokingStatus) {
                    Text("Never").tag("none")
                    Text("Former").tag("former")
                    Text("Light").tag("light")
                    Text("Heavy").tag("heavy")
                }
                .accessibilityIdentifier("onboarding.smokingStatus")
                .accessibilityValue(smokingStatus)
                Picker("Alcohol", selection: $alcoholFrequency) {
                    Text("Rare").tag("rare")
                    Text("Weekly").tag("weekly")
                    Text("Daily").tag("daily")
                }
                .accessibilityIdentifier("onboarding.alcoholFrequency")
                .accessibilityValue(alcoholFrequency)
            }
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Picker("Typical diet quality", selection: $dietQualityBaseline) {
                    Text("Great").tag("great")
                    Text("Okay").tag("okay")
                    Text("Rough").tag("rough")
                }
                .pickerStyle(.segmented)
                .accessibilityIdentifier("onboarding.dietQualityBaseline")
                .accessibilityValue(dietQualityBaseline)
                Text("How would you describe most of your meals — coarse on purpose. No counting required.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Stepper("Strength sessions per week: \(strengthFrequency)", value: $strengthFrequency, in: 0...7)
                .accessibilityIdentifier("onboarding.strengthFrequency")
                .accessibilityValue("\(strengthFrequency)")
            VStack(alignment: .leading) {
                Text("Sleep goal: \(String(format: "%.1f", sleepGoalHours)) hours")
                Slider(value: $sleepGoalHours, in: 5.0...10.0, step: 0.5)
                    .accessibilityIdentifier("onboarding.sleepGoalHours")
                    .accessibilityValue(String(format: "%.1f hours", sleepGoalHours))
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("onboarding.baseline")
    }

    private var toneScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Pick a tone").font(.title2.bold())
            Text("You can change this any time in Profile.")
                .foregroundStyle(.secondary)
            ForEach(ToneMode.allCases) { mode in
                Button {
                    toneMode = mode
                } label: {
                    HStack {
                        VStack(alignment: .leading) {
                            Text(mode.displayName).font(.headline)
                            Text(mode.description).font(.caption).foregroundStyle(.secondary)
                                .multilineTextAlignment(.leading)
                        }
                        Spacer()
                        if toneMode == mode {
                            Image(systemName: "checkmark.circle.fill").foregroundStyle(.tint)
                        }
                    }
                    .padding(DesignTokens.Spacing.md)
                    .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("onboarding.tone.\(mode.rawValue)")
            }
        }
        .accessibilityIdentifier("onboarding.tone")
    }

    private var permissionEducationScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Connect Apple Health").font(.title2.bold())
            Text(LifeClockConfiguration.healthKitRationale)
                .foregroundStyle(.secondary)
            Text("Apple controls the prompt. You can grant or deny each data type separately, and you can change your mind later in iOS Settings → Health.")
                .foregroundStyle(.secondary)
            HStack {
                if permissionRequestInFlight {
                    LifeClockSpinner()
                }
                Button(store.healthAuthorizationKnown ? "Check Apple Health again" : "Connect Apple Health") {
                    requestHealthAuthorization()
                }
                .buttonStyle(.borderedProminent)
                .disabled(permissionRequestInFlight)
                .accessibilityIdentifier("onboarding.connectHealth")

                if store.healthAuthorizationKnown {
                    Text("Request sent").font(.caption).foregroundStyle(.secondary)
                }
            }
            Text("You can skip this and connect later from Profile.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .accessibilityIdentifier("onboarding.health")
    }

    private func requestHealthAuthorization() {
        permissionRequestInFlight = true
        Task {
            await store.requestHealthAuthorization()
            permissionRequestInFlight = false
        }
    }

    private var dailyReminderScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Daily reminder?").font(.title2.bold())
            Text("Want a one-tap nudge if you haven't logged by 8 PM? Off by default — turn on here, or change it any time in Profile.")
                .foregroundStyle(.secondary)
            HStack {
                if reminderRequestInFlight {
                    LifeClockSpinner()
                }
                Button("Yes, remind me") {
                    requestDailyReminder()
                }
                .buttonStyle(.borderedProminent)
                .disabled(reminderRequestInFlight || reminderDecisionMade)

                Button("No thanks") {
                    reminderDecisionMade = true
                }
                .buttonStyle(.bordered)
                .disabled(reminderRequestInFlight)
            }
            if reminderDecisionMade {
                Text("Saved. You can change this in Profile.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func requestDailyReminder() {
        reminderRequestInFlight = true
        Task {
            // If iOS auth carries over from a prior install, the dialog
            // doesn't appear and the call returns immediately.
            _ = await store.requestNotificationAuthorization()
            reminderDecisionMade = true
            reminderRequestInFlight = false
        }
    }

    private var revealScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("You're set.").font(.title.bold())
            Text("We'll show today's progress, the habits influencing it, and one or two supportive actions to focus on next.")
                .foregroundStyle(.secondary)
            DisclaimerBanner()
        }
        .accessibilityIdentifier("onboarding.reveal")
    }

    // MARK: - Footer

    private var footer: some View {
        HStack {
            if step > 0 {
                Button("Back") { step -= 1 }
                    .buttonStyle(.bordered)
            }
            Spacer()
            Button(step == totalSteps - 1 ? "Finish" : "Continue") {
                advance()
            }
            .buttonStyle(.borderedProminent)
            .disabled(step == 1 && !disclaimerAccepted)
            .accessibilityIdentifier(step == totalSteps - 1 ? "onboarding.finish" : "onboarding.continue")
        }
        .padding(DesignTokens.Spacing.lg)
        .background(DesignTokens.Palette.surface)
    }

    private func advance() {
        if step < totalSteps - 1 {
            step += 1
        } else {
            let profile = UserProfile(birthDate: birthDate, biologicalSex: biologicalSex, toneMode: toneMode.rawValue)
            profile.smokingStatus = smokingStatus
            profile.alcoholFrequency = alcoholFrequency
            profile.dietQualityBaseline = dietQualityBaseline
            profile.sleepGoalHours = sleepGoalHours
            profile.strengthFrequencyPerWeek = strengthFrequency
            store.completeOnboarding(profile: profile, tone: toneMode, disclaimerAccepted: disclaimerAccepted)
            Task {
                // Apply reminder opt-in here — profile now exists, so
                // setDailyReminder's nil-profile guard passes. Read the
                // store's auth state directly rather than tracking a
                // duplicate flag.
                if store.notificationAuthorizationStatus == .authorized {
                    await store.setDailyReminder(enabled: true, hour: 20)
                }
                await store.bootstrap()
            }
        }
    }
}
