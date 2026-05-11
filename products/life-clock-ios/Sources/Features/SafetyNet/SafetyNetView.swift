import SwiftUI

/// Safety-net screen for users who find the mortality framing distressing.
///
/// Implements the affordances the founder pack's
/// `docs/products/life-clock/PRIVACY_COMPLIANCE.md` requires under
/// "Emotional safety": gentle alternatives, crisis-resource links, and a
/// way to hide the clock entirely.
///
/// Reachable from Profile → "If this app is making you anxious".
///
/// **Copy is intentionally tone-neutral.** SafetyNet is the refuge from
/// whichever tone the user is in. A firmDirect tone here would be
/// hostile to the anxious user the surface exists for; a coach tone
/// would still carry accountability language. The strings below lean
/// toward Gentle's register regardless of `store.toneMode`. Do not wire
/// these through `ToneMode` keys.
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
                        .accessibilityIdentifier("safetyNet.done")
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
                .accessibilityAddTraits(.isHeader)
            Text("Mortality framing is intense by design — it's also intense for some people in ways the app can't predict. If today is a hard day, here are three things you can do right now.")
                .foregroundStyle(.secondary)
        }
        .accessibilityIdentifier("safetyNet.intro")
    }

    private var softerModeCard: some View {
        let alreadyGentle = store.toneMode == .gentle
        return VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(alreadyGentle ? "1. You're already on Gentle" : "1. Switch to Gentle tone")
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
            Text("Gentle removes mortality language entirely. Same engine, different presentation: \"healthspan\", \"time earned\", \"future-self\" instead of clocks and countdowns.")
                .font(.callout)
                .foregroundStyle(.secondary)
            Button {
                store.setToneMode(.gentle)
            } label: {
                HStack {
                    Text(alreadyGentle ? "Gentle is on" : "Use Gentle now")
                    if alreadyGentle {
                        Spacer()
                        Image(systemName: "checkmark")
                            .foregroundStyle(.tint)
                            .accessibilityHidden(true)
                    }
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(alreadyGentle)
            .accessibilityIdentifier("safetyNet.tone.gentle")
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private var hideClockCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("2. Hide the clock")
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
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
            .accessibilityIdentifier("safetyNet.hideClock.toggle")
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private var crisisResourcesCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("3. Talk to someone")
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
            Text("If thoughts about your life expectancy or daily habits feel overwhelming — or if you're in crisis — please reach out. These services are free, confidential, and staffed by trained humans 24/7.")
                .font(.callout)
                .foregroundStyle(.secondary)

            crisisRow(
                title: "988 Suicide & Crisis Lifeline (US)",
                detail: "Call or text 988 — free, 24/7, multiple languages.",
                phone: "988",
                identifierSuffix: "988"
            )
            crisisRow(
                title: "Crisis Text Line (US/CA/UK/IE)",
                detail: "Text HOME to 741741 (US/CA), 85258 (UK), or 50808 (IE).",
                phone: nil,
                identifierSuffix: "textLine"
            )
            crisisRow(
                title: "International association",
                detail: "Find a hotline in your country at findahelpline.com.",
                phone: nil,
                identifierSuffix: "international"
            )

            Text(LifeClockConfiguration.safetyNetClosing)
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.top, DesignTokens.Spacing.xs)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }

    private func crisisRow(title: String, detail: String, phone: String?, identifierSuffix: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Text(title).font(.callout.bold())
                Spacer()
                if let phone, let url = URL(string: "tel:\(phone)") {
                    Link("Call \(phone)", destination: url)
                        .font(.caption)
                        .accessibilityLabel("Call \(title)")
                        .accessibilityIdentifier("safetyNet.crisis.\(identifierSuffix).call")
                }
            }
            Text(detail)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, DesignTokens.Spacing.xs)
        .accessibilityIdentifier("safetyNet.crisis.\(identifierSuffix)")
    }
}
