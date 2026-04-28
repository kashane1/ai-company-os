import SwiftUI

// MARK: - Onboarding coordinator
// Switches between sub-views based on the current OnboardingStep. Each
// sub-view is responsible for its own validation and only signals
// `onContinue` when ready. Persistence to UserDefaults is handled by
// OnboardingState.

struct OnboardingView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @StateObject private var state = OnboardingState()

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color.appBackground, Color.appMomentum.opacity(0.10)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ).ignoresSafeArea()

            switch state.step {
            case .intro:
                IntroCarouselStepView(
                    onContinue: { state.advance() },
                    onSkip: { complete() }
                )
            case .name:
                NameStepView(
                    firstName: Binding(
                        get: { state.draft.firstName },
                        set: { newValue in state.updateDraft { $0.firstName = newValue } }
                    ),
                    onContinue: {
                        Task { await applyProfileThenAdvance() }
                    },
                    onBack: { state.goBack() }
                )
            case .privacy:
                PrivacyStepView(
                    privacyMode: Binding(
                        get: { state.draft.privacyMode },
                        set: { newValue in state.updateDraft { $0.privacyMode = newValue } }
                    ),
                    onContinue: {
                        Task { await applyProfileThenAdvance() }
                    },
                    onBack: { state.goBack() }
                )
            case .activityVenue:
                ActivityVenueStepView(
                    declaredActivityIDs: Binding(
                        get: { state.draft.declaredActivityIDs },
                        set: { newValue in state.updateDraft { $0.declaredActivityIDs = newValue } }
                    ),
                    declaredVenueIDs: Binding(
                        get: { state.draft.declaredVenueIDs },
                        set: { newValue in state.updateDraft { $0.declaredVenueIDs = newValue } }
                    ),
                    onContinue: {
                        Task { await declareInterestsThenAdvance() }
                    },
                    onBack: { state.goBack() }
                )
            case .inviteCode:
                InviteCodeStepView(
                    inviteCode: Binding(
                        get: { state.draft.inviteCode },
                        set: { newValue in state.updateDraft { $0.inviteCode = newValue } }
                    ),
                    redeemed: state.draft.inviteCodeRedeemed,
                    onRedeem: {
                        Task { await redeemInvite() }
                    },
                    onContinue: { complete() },
                    onBack: { state.goBack() }
                )
            case .complete:
                ProgressView().onAppear { complete() }
            }
        }
    }

    private func applyProfileThenAdvance() async {
        let trimmed = state.draft.firstName.trimmingCharacters(in: .whitespaces)
        if !trimmed.isEmpty {
            await store.updateOnboardingProfile(firstName: trimmed, privacyMode: state.draft.privacyMode)
        }
        state.advance()
    }

    private func declareInterestsThenAdvance() async {
        for activityID in state.draft.declaredActivityIDs {
            await store.declareActivityInterest(activityID: activityID, venueID: nil)
        }
        state.advance()
    }

    private func redeemInvite() async {
        let code = state.draft.inviteCode.trimmingCharacters(in: .whitespaces)
        guard !code.isEmpty else { return }
        let ok = await store.redeemInviteCode(code)
        if ok {
            state.updateDraft { $0.inviteCodeRedeemed = true }
        }
    }

    private func complete() {
        state.skipToEnd()
        state.reset()
        store.finishOnboarding()
    }
}
