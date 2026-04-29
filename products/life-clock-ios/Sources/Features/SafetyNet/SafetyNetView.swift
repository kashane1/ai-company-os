import SwiftUI

/// Safety-net screen for users who find the mortality framing distressing.
///
/// Implements the affordances the founder pack's `PRIVACY_COMPLIANCE.md`
/// asks for under "Emotional safety": gentle alternatives, crisis-resource
/// links, and a way to hide the clock entirely. Resolves Open Question 13
/// (self-harm-adjacent language / anxious users) and offers Open Question 5
/// (hide the clock, show only "time earned") as a one-tap toggle.
///
/// Reachable from Profile → "If this app is making you anxious".
struct SafetyNetView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var hideClockLocal: Bool = false
    @State private var showCrisis: Bool = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    intro
                    softerModeCard
                    hideClockCard
                    crisisResourcesCard
                    DisclaimerBanner()
                }
                .padding(DesignTokens.Spacing.lg)
            }
            .navigationTitle("Take a softer path")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .onAppear {
                hideClockLocal = store.profile?.hideClock ?? false
            }
        }
    }

    private var intro: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Your clock is feedback, not fate.")
                .font(.title2.bold())
            Text("Mortality framing is intense by design — it's also intense for some people in ways the app can't predict. If today is a hard day, here are three things you can do right now.")
                .foregroundStyle(.secondary)
        }
    }

    private var softerModeCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("1. Switch to Gentle tone")
                .font(.headline)
            Text("Gentle removes mortality language entirely. Same engine, different presentation: \"healthspan\", \"time earned\", \"future-self\" instead of clocks and countdowns.")
                .font(.callout)
                .foregroundStyle(.secondary)
            Button {
                store.setToneMode(.gentle)
            } label: {
                HStack {
                    Text("Use Gentle now")
                    if store.toneMode == .gentle {
                        Spacer()
                        Image(systemName: "checkmark").foregroundStyle(.tint)
                    }
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private var hideClockCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("2. Hide the clock")
                .font(.headline)
            Text("Replace the projected age and anchor date with \"Time earned today\". The engine still calculates your trajectory; you just don't see the dramatic version of it.")
                .font(.callout)
                .foregroundStyle(.secondary)
            Toggle("Hide projected age and anchor date", isOn: Binding(
                get: { hideClockLocal },
                set: { newValue in
                    hideClockLocal = newValue
                    Task { await store.setHideClock(newValue) }
                }
            ))
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private var crisisResourcesCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("3. Talk to someone")
                .font(.headline)
            Text("If thoughts about your life expectancy or daily habits feel overwhelming — or if you're in crisis — please reach out. These services are free, confidential, and staffed by trained humans 24/7.")
                .font(.callout)
                .foregroundStyle(.secondary)

            crisisRow(
                title: "988 Suicide & Crisis Lifeline (US)",
                detail: "Call or text 988 — free, 24/7, multiple languages.",
                phone: "988"
            )
            crisisRow(
                title: "Crisis Text Line (US/CA/UK/IE)",
                detail: "Text HOME to 741741 (US/CA), 85258 (UK), or 50808 (IE).",
                phone: nil
            )
            crisisRow(
                title: "International association",
                detail: "Find a hotline in your country at findahelpline.com.",
                phone: nil
            )

            Text("Life Clock is a habit-tracking app. It is not a substitute for professional mental-health support. The disclaimer at the bottom of every screen is not boilerplate — it's the product's actual stance.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.top, DesignTokens.Spacing.xs)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private func crisisRow(title: String, detail: String, phone: String?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Text(title).font(.callout.bold())
                Spacer()
                if let phone, let url = URL(string: "tel:\(phone)") {
                    Link("Call \(phone)", destination: url)
                        .font(.caption)
                }
            }
            Text(detail)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, DesignTokens.Spacing.xs)
    }
}
