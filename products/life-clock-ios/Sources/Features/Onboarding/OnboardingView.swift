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
    @State private var sleepGoalHours: Double = 7.5
    @State private var strengthFrequency: Int = 2
    @State private var toneMode: ToneMode = .coach
    @State private var disclaimerAccepted: Bool = false

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
            Text("Your daily habits move a visible time trajectory. Sleep, movement, workouts, and consistency add minutes. Heavy alcohol and skipping movement subtract them.")
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
            Text("Apple Health (later)").font(.title2.bold())
            Text("Live Apple Health reads land in a follow-up update. For now, the app uses sample data so you can see the loop.")
                .foregroundStyle(.secondary)
            Text("When live, the app will request the minimum data it needs and explain each prompt. Missing data never fakes precision — it lowers confidence.")
                .foregroundStyle(.secondary)
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
            profile.sleepGoalHours = sleepGoalHours
            profile.strengthFrequencyPerWeek = strengthFrequency
            store.completeOnboarding(profile: profile, tone: toneMode)
            Task { await store.bootstrap() }
        }
    }
}
