import SwiftUI
import SwiftData

/// Replaces the legacy 7-step `OnboardingView` with a `NavigationStack`-
/// driven coordinator. Each screen is a separate sub-view; routing goes
/// through the `OnboardingScreen` enum as the path value type. Matches
/// the codebase convention (`TodayView.swift:8`, `HistoryView.swift:22`)
/// of `NavigationStack` per feature root.
///
/// The coordinator owns:
/// - the `OnboardingDraft` (transient @Observable, not persisted)
/// - the `NavigationPath` (programmatic forward + system-provided back)
/// - the `OnboardingTelemetryHolder` (read by every screen via env)
///
/// Forward navigation: `path.append(.nextScreen)`. Back navigation: free
/// via NavigationStack's gesture/button. Per the plan's spec-flow review,
/// post-confirm dial back-nav is BLOCKED — Phase 5's reveal+dial screen
/// resets the path to a fresh root on Confirm so the dial cannot be
/// reached again.
@MainActor
struct OnboardingCoordinator: View {
    @Environment(LifeClockStore.self) private var store
    @State private var path: [OnboardingScreen] = []
    @State private var draft = OnboardingDraft()
    @State private var telemetry = OnboardingTelemetryHolder(OSLogTelemetry())

    var body: some View {
        NavigationStack(path: $path) {
            ColdOpenView(onContinue: { advance(to: .appPreviews) })
                .navigationDestination(for: OnboardingScreen.self, destination: destination)
        }
        .environment(telemetry)
        .environment(draft)
    }

    @ViewBuilder
    private func destination(for screen: OnboardingScreen) -> some View {
        switch screen {
        case .appPreviews:
            AppPreviewsView(onContinue: { advance(to: .welcome) })
        case .welcome:
            WelcomeView(onContinue: { advance(to: .meetYourClock) })
        case .meetYourClock:
            MeetYourClockView(onContinue: { advance(to: .reactiveSlider) })
        case .reactiveSlider:
            ReactiveSliderView(onContinue: { advance(to: .visibilityFraming) })

        case .visibilityFraming:
            VisibilityFramingView(onContinue: { advance(to: .personalizeIntro) })
        case .personalizeIntro:
            PersonalizeIntroView(onContinue: { advance(to: .goalPick) })
        case .goalPick:
            GoalPickView(onContinue: { advance(to: .baselineDOB) })

        case .baselineDOB:
            BaselineDOBView(onContinue: { advance(to: .baselineSex) })
        case .baselineSex:
            BaselineSexView(onContinue: { advance(to: .bodyComp) })
        case .bodyComp:
            BodyCompView(onContinue: { advance(to: .smoking) })
        case .smoking:
            SmokingView(onContinue: { advance(to: .alcohol) })
        case .alcohol:
            AlcoholView(onContinue: { advance(to: .strength) })
        case .strength:
            StrengthView(onContinue: { advance(to: .cardio) })
        case .cardio:
            CardioView(onContinue: { advance(to: .sleep) })
        case .sleep:
            SleepView(onContinue: { advance(to: .diet) })
        case .diet:
            DietView(onContinue: { advance(to: .sensitiveConsent) })

        case .sensitiveConsent:
            SensitiveConsentView(
                onContinue: { advance(to: .familyMother) },
                onSkip: {
                    // Skip the sensitive block entirely — leave parental,
                    // stress, and loneliness fields nil.
                    advance(to: .tone)
                }
            )
        case .familyMother:
            FamilyMotherView(onContinue: { advance(to: .familyFather) })
        case .familyFather:
            FamilyFatherView(onContinue: { advance(to: .stress) })
        case .stress:
            StressView(onContinue: { advance(to: .social) })
        case .social:
            SocialView(onContinue: { advance(to: .tone) })

        case .tone:
            ToneView(onContinue: { advance(to: .priorAttempts) })
        case .priorAttempts:
            PriorAttemptsView(onContinue: { advance(to: .analyzing) })

        case .analyzing:
            AnalyzingView(onContinue: { advance(to: .archetypeReveal) })
        case .archetypeReveal:
            ArchetypeRevealView(onContinue: { advance(to: .lifeGridFull) })
        case .lifeGridFull:
            LifeGridFullView(onContinue: { advance(to: .lifeGridRemaining) })
        case .lifeGridRemaining:
            LifeGridRemainingView(onContinue: {
                if shouldShowPenaltyScreen() {
                    advance(to: .bigNumberPenalty)
                } else {
                    advance(to: .engineRevealAndDial)
                }
            })
        case .bigNumberPenalty:
            BigNumberPenaltyView(onContinue: { advance(to: .engineRevealAndDial) })
        case .engineRevealAndDial:
            EngineRevealAndDialView(
                onConfirm: { dialYears in
                    draft.personalAdjustmentYears = dialYears
                    draft.anchorAdjustedAt = store.clock.now()
                    // Per spec-flow rules: clear the path so the dial
                    // cannot be reached via back-nav after Confirm.
                    path = [.recoveryPreview]
                }
            )
        case .recoveryPreview:
            RecoveryPreviewView(onContinue: { advance(to: .healthKitAuth) })

        case .healthKitAuth:
            HealthKitAuthView(onContinue: { advance(to: .paywallPrimary) })

        case .paywallPrimary:
            PaywallPrimaryView(onClose: {
                // Free fallback: complete onboarding now (writes the
                // profile) and route to the entry view.
                completeOnboarding()
                advance(to: .entryView)
            })

        case .entryView:
            // Terminal — completing onboarding flips
            // `LifeClockApp`'s gate (profile exists) so this view is
            // dismissed by the parent. Show a brief "all set" until
            // that happens.
            EntryView()
        }
    }

    private func advance(to next: OnboardingScreen) {
        path.append(next)
    }

    /// Decide whether to show the `bigNumberPenalty` framing. Suppressed
    /// for under-18 users (legacy `isAdultBirthDate` rule) and for the
    /// `.justCurious` goal where mortality framing isn't appropriate.
    private func shouldShowPenaltyScreen() -> Bool {
        let isAdult = isAdultBirthDate(draft.birthDate)
        let isJustCurious = draft.primaryGoal == .justCurious
        return isAdult && !isJustCurious
    }

    private func isAdultBirthDate(_ date: Date?) -> Bool {
        guard let date else { return false }
        let yearsFromNow = Calendar.current.dateComponents(
            [.year], from: date, to: store.clock.now()
        ).year ?? 0
        return yearsFromNow >= 18
    }

    private func completeOnboarding() {
        let profile = draft.materialize()
        profile.onboardingV2CompletedAt = store.clock.now()
        let didComplete = store.completeOnboarding(
            profile: profile,
            tone: draft.toneMode ?? .coach,
            disclaimerAccepted: true
        )
        if didComplete {
            Task { await store.refreshFromHealthKit(force: true) }
        }
    }
}

// MARK: - Terminal entry view

struct EntryView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingTelemetryHolder.self) private var telemetry

    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("Almost there…")
                .foregroundStyle(.secondary)
        }
        .accessibilityIdentifier("onboarding.entryView")
        .onAppear {
            telemetry.value.screenAppeared("entryView")
        }
    }
}
