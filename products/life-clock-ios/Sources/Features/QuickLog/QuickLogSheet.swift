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
///
/// **Tone-key surface for narration only.** The intro pair
/// (`tone.quickLogIntroHeadline` + `tone.quickLogIntroSubheadline`), the
/// Rhythm caption (`tone.quickLogRhythmCaption`), the clear-footer body
/// (`tone.quickLogClearFooter`), and the save CTA
/// (`tone.quickLogSaveCTA(hasExistingHabits:)`) route through `ToneMode`
/// keys. Vision Q11 resolution (2026-05-11).
///
/// **Intentionally neutral, do NOT wire through `ToneMode`:**
/// - **Section labels** (Fuel / Rhythm / Whole food / Extras / Recovery /
///   Strength / Nicotine) — anchored on schema fields (`dietAmountRhythm`
///   ↔ "Rhythm"); tone-shifting risks creating navigation confusion
///   across modes.
/// - **Seven question prompts** under each section (`"How did food go
///   today?"`, etc.) — picker affordances, not narration. Tone-keying
///   them would either split the group register-randomly or push Q11's
///   total key count past the ≥14-key threshold without payoff.
/// - **All picker option labels** (`Great / Okay / Rough`, `None / One /
///   A few / A lot`, etc.) — picker tags persisted into `HabitLog` and
///   consumed by `ClockEngine` switch statements; tone-shifting them
///   decouples display from storage.
/// - **Destructive button label** (`"Clear today's check-in"`) — iOS HIG
///   verb-noun pattern; tone-shifting destructive labels risks softening
///   firmDirect into ambiguity or hardening gentle into anxiety territory.
/// - **Nav title** (`"Daily Check-In"`) and toolbar `"Cancel"` — surface
///   anchors and iOS standards.
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
                        Text(store.toneMode.quickLogIntroHeadline)
                            .font(.headline)
                        Text(store.toneMode.quickLogIntroSubheadline)
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
                        // Q11 polish 2026-05-11: was `.segmented`. With 5
                        // options, segmented truncated "Skipped, then over"
                        // to "Skipped…" at the default content size on
                        // iPhone 17 Pro. Menu picker handles long labels
                        // gracefully and the rendering is honest.
                        // `.labelsHidden()` because the standalone Text
                        // above already shows the question — without this
                        // the menu picker duplicates the prompt inline.
                        .pickerStyle(.menu)
                        .labelsHidden()
                        .accessibilityIdentifier("quickLog.dietAmountRhythm")
                        .accessibilityValue(dietAmountRhythm)
                        Text(store.toneMode.quickLogRhythmCaption)
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
                        Text(store.toneMode.quickLogClearFooter)
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
                        if saving {
                            LifeClockSpinner()
                        } else {
                            Text(store.toneMode.quickLogSaveCTA(
                                hasExistingHabits: store.todayHabits != nil
                            ))
                        }
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
