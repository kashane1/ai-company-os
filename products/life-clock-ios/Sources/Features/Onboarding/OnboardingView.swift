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

    private let totalSteps = 6

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
                    case 5: revealScreen
                    default: revealScreen
                    }
                }
                .padding(DesignTokens.Spacing.lg)
            }

            footer
        }
    }

    // MARK: - Steps

    private var valueScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Earn time back.")
                .font(.largeTitle.bold())
            Text("Your daily habits move a visible time trajectory. Food choices, sleep, movement, and consistency add minutes. Heavy alcohol, smoking, and rough food days pull them back.")
                .foregroundStyle(.secondary)
            Text("Diet quality is one of your strongest levers — without ever counting a calorie.")
                .foregroundStyle(.secondary)
            Text("This isn't a death predictor. It's a healthspan game with agency baked in.")
                .foregroundStyle(.secondary)
        }
    }

    private var safetyScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Your clock is an estimate, not fate.")
                .font(.title2.bold())
            DisclaimerBanner()
            Toggle(isOn: $disclaimerAccepted) {
                Text("I understand Life Clock is not medical advice.")
                    .font(.callout)
            }
            .padding(.top, DesignTokens.Spacing.sm)
        }
    }

    private var baselineScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("A few quick baselines")
                .font(.title2.bold())
            DatePicker("Date of birth", selection: $birthDate, displayedComponents: .date)
            Picker("Biological sex (optional)", selection: $biologicalSex) {
                Text("Prefer not to say").tag("unspecified")
                Text("Female").tag("female")
                Text("Male").tag("male")
            }
            Picker("Smoking", selection: $smokingStatus) {
                Text("Never").tag("none")
                Text("Former").tag("former")
                Text("Light").tag("light")
                Text("Heavy").tag("heavy")
            }
            Picker("Alcohol", selection: $alcoholFrequency) {
                Text("Rare").tag("rare")
                Text("Weekly").tag("weekly")
                Text("Daily").tag("daily")
            }
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Picker("Typical diet quality", selection: $dietQualityBaseline) {
                    Text("Great").tag("great")
                    Text("Okay").tag("okay")
                    Text("Rough").tag("rough")
                }
                .pickerStyle(.segmented)
                Text("How would you describe most of your meals — coarse on purpose. No counting required.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Stepper("Strength sessions per week: \(strengthFrequency)", value: $strengthFrequency, in: 0...7)
            VStack(alignment: .leading) {
                Text("Sleep goal: \(String(format: "%.1f", sleepGoalHours)) hours")
                Slider(value: $sleepGoalHours, in: 5.0...10.0, step: 0.5)
            }
        }
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
            }
        }
    }

    private var permissionEducationScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Connect Apple Health").font(.title2.bold())
            Text("Life Clock reads steps, sleep, exercise minutes, and resting heart rate. We don't read everything — only the signals that move your time delta.")
                .foregroundStyle(.secondary)
            Text("Apple controls the prompt. You can grant or deny each data type separately, and you can change your mind later in iOS Settings → Health.")
                .foregroundStyle(.secondary)
            HStack {
                if permissionRequestInFlight {
                    ProgressView()
                }
                Button(store.healthAuthorizationKnown ? "Re-prompt Apple Health" : "Connect Apple Health") {
                    requestHealthAuthorization()
                }
                .buttonStyle(.borderedProminent)
                .disabled(permissionRequestInFlight)

                if store.healthAuthorizationKnown {
                    Text("Asked").font(.caption).foregroundStyle(.secondary)
                }
            }
            Text("You can skip this and connect later from Profile.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func requestHealthAuthorization() {
        permissionRequestInFlight = true
        Task {
            await store.requestHealthAuthorization()
            permissionRequestInFlight = false
        }
    }

    private var revealScreen: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("You're set.").font(.title.bold())
            Text("We'll show your starting Life Clock and a quest for tomorrow.")
                .foregroundStyle(.secondary)
            DisclaimerBanner()
        }
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
            store.completeOnboarding(profile: profile, tone: toneMode)
            Task { await store.bootstrap() }
        }
    }
}
