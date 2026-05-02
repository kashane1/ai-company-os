import SwiftUI

enum DailyCheckInMapping {
    static func extrasLevel(for alcoholLevel: String) -> String {
        switch alcoholLevel {
        case "heavy":
            return "lot"
        case "light":
            return "few"
        default:
            return "none"
        }
    }

    static func alcoholLevel(for extrasLevel: String) -> String {
        switch extrasLevel {
        case "one", "few":
            return "light"
        case "lot":
            return "heavy"
        default:
            return "none"
        }
    }
}

/// Today-screen daily check-in. Captures a few coarse manual signals and
/// feeds them to the engine via `store.setTodayHabits(_:)`.
struct QuickLogSheet: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var dietQuality: String = "okay"
    @State private var dietAmountRhythm: String = "right"
    @State private var wholeFoodMeal: String = "unknown"
    @State private var extrasLevel: String = "none"
    @State private var stressLevel: String = "medium"
    @State private var strengthCompleted: String = "notToday"
    @State private var nicotineUsed: String = "none"
    @State private var saving: Bool = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("A few quick signals help your Life Clock stay honest.")
                            .font(.headline)
                        Text("No calorie counting. No judgment.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                Section("Fuel") {
                    Text("How did food go today?")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Picker("How did food go today?", selection: $dietQuality) {
                        Text("Great").tag("great")
                        Text("Okay").tag("okay")
                        Text("Rough").tag("rough")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("quickLog.dietQuality")
                    .accessibilityValue(dietQuality)
                }
                if store.isAdultUser {
                    Section("Rhythm") {
                        Text("How much did you eat for your body's needs?")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Picker("How much did you eat for your body's needs?", selection: $dietAmountRhythm) {
                            Text("Right").tag("right")
                            Text("Too much").tag("overate")
                            Text("Too little").tag("undereate")
                            Text("Skipped, then over").tag("skipBinge")
                            Text("Irregular").tag("irregular")
                        }
                        .pickerStyle(.segmented)
                        .accessibilityIdentifier("quickLog.dietAmountRhythm")
                        .accessibilityValue(dietAmountRhythm)
                        Text("No calories, no judgment. Just rhythm.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Section("Whole food") {
                    Text("At least one solid whole-food meal today?")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Picker("At least one solid whole-food meal today?", selection: $wholeFoodMeal) {
                        Text("Yes").tag("yes")
                        Text("Almost").tag("almost")
                        Text("No").tag("no")
                        Text("—").tag("unknown")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("quickLog.wholeFoodMeal")
                    .accessibilityValue(wholeFoodMeal)
                }
                Section("Extras") {
                    Text("Any treats, drinks, or heavier choices?")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Picker("Any treats, drinks, or heavier choices?", selection: $extrasLevel) {
                        Text("None").tag("none")
                        Text("One").tag("one")
                        Text("A few").tag("few")
                        Text("A lot").tag("lot")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("quickLog.alcoholLevel")
                    .accessibilityValue(extrasLevel)
                    Text("Examples: dessert, drinks, late snack, or an extra-heavy meal.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Recovery") {
                    Text("How stressed did today feel?")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Picker("How stressed did today feel?", selection: $stressLevel) {
                        Text("Low").tag("low")
                        Text("Medium").tag("medium")
                        Text("High").tag("high")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("quickLog.stressLevel")
                    .accessibilityValue(stressLevel)
                }
                Section("Strength") {
                    Text("Did you train today?")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Picker("Did you train today?", selection: $strengthCompleted) {
                        Text("Not today").tag("notToday")
                        Text("Completed").tag("completed")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("quickLog.strengthTraining")
                    .accessibilityValue(strengthCompleted)
                }
                if store.isAdultUser {
                    Section("Nicotine") {
                        Text("Any nicotine today?")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Picker("Any nicotine today?", selection: $nicotineUsed) {
                            Text("None").tag("none")
                            Text("Used").tag("used")
                        }
                        .pickerStyle(.segmented)
                        .accessibilityIdentifier("quickLog.smokingVaping")
                        .accessibilityValue(nicotineUsed)
                    }
                }
                if store.todayHabits != nil {
                    Section {
                        Button(role: .destructive) {
                            clear()
                        } label: {
                            Text("Clear today's check-in")
                                .frame(maxWidth: .infinity, alignment: .center)
                        }
                        .disabled(saving)
                    } footer: {
                        Text("Removes today's manual signals. Your Life Clock will recompute from HealthKit signals only.")
                    }
                }
                Section {
                    DisclaimerBanner()
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }
            }
            .navigationTitle("Daily Check-In")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .accessibilityIdentifier("checkIn.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        save()
                    } label: {
                        if saving { ProgressView() } else { Text("Update Life Clock") }
                    }
                    .disabled(saving)
                    .accessibilityIdentifier("checkIn.save")
                }
            }
            .accessibilityIdentifier("checkIn.screen")
        }
        .onAppear { hydrateFromStore() }
    }

    private func hydrateFromStore() {
        guard let existing = store.todayHabits else { return }
        dietQuality = existing.dietQuality
        dietAmountRhythm = existing.dietAmountRhythm
        wholeFoodMeal = existing.wholeFoodMeal
        extrasLevel = DailyCheckInMapping.extrasLevel(for: existing.alcoholLevel)
        stressLevel = existing.stressLevel
        strengthCompleted = existing.strengthTraining ? "completed" : "notToday"
        nicotineUsed = existing.smokingVaping ? "used" : "none"
    }

    private func save() {
        saving = true
        Task {
            let habits = HabitLog(date: store.clock.calendar.startOfDay(for: store.clock.now()))
            habits.alcoholLevel = DailyCheckInMapping.alcoholLevel(for: extrasLevel)
            habits.smokingVaping = nicotineUsed == "used"
            habits.dietQuality = dietQuality
            habits.dietAmountRhythm = dietAmountRhythm
            habits.wholeFoodMeal = wholeFoodMeal
            habits.stressLevel = stressLevel
            habits.strengthTraining = strengthCompleted == "completed"
            await store.setTodayHabits(habits)
            saving = false
            dismiss()
        }
    }

    private func clear() {
        saving = true
        Task {
            await store.clearTodayHabits()
            saving = false
            dismiss()
        }
    }
}
