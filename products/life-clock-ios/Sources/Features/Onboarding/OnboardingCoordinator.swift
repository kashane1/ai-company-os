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
    @State private var mascotOverride = MascotOverride()
    @State private var telemetry = OnboardingTelemetryHolder(OSLogTelemetry())
    @State private var recomputeTask: Task<Void, Never>?

    var body: some View {
        VStack(spacing: 0) {
            // Persistent header — single instance for the whole flow,
            // hidden only on `coldOpen` (which is its own full-bleed
            // mascot moment). Living *above* the NavigationStack means
            // SwiftUI keeps this view's identity stable across pushes:
            // one onAppear after the first push, no rebuild between
            // subsequent screens, hands animate continuously.
            if !path.isEmpty {
                OnboardingHeader(
                    canGoBack: canGoBack,
                    onBack: popPath
                )
                .padding(.horizontal, 24)
                .transition(.opacity)
            }
            NavigationStack(path: $path) {
                ColdOpenView(onContinue: { advance(to: .welcome) })
                    .onboardingChrome()
                    .navigationDestination(for: OnboardingScreen.self) { screen in
                        destination(for: screen).onboardingChrome()
                    }
            }
        }
        .environment(telemetry)
        .environment(draft)
        .environment(mascotOverride)
        .onAppear { applyJumpFixtureIfNeeded() }
        // Shell-level reactor: any draft input mutation schedules a
        // debounced recompute so the persistent mascot reflects the
        // current state without waiting for Continue. 80ms balances
        // jank-risk vs feeling responsive (per debounce research).
        .onChange(of: draftInputsKey) { _, _ in
            scheduleRecompute()
        }
        .onDisappear {
            recomputeTask?.cancel()
        }
    }

    /// Composite hash of every draft field whose mutation should drive
    /// the persistent mascot. Adding a new lifestyle input? Add it here
    /// too — otherwise the hands won't react until Continue.
    private var draftInputsKey: Int {
        var hasher = Hasher()
        hasher.combine(draft.smokingStatus)
        hasher.combine(draft.alcoholFrequency)
        hasher.combine(draft.strengthFrequencyPerWeek)
        hasher.combine(draft.cardioMinsPerWeek)
        hasher.combine(draft.sleepGoalHours)
        hasher.combine(draft.dietQualityBaseline)
        hasher.combine(draft.heightCm)
        hasher.combine(draft.weightKg)
        hasher.combine(draft.parentMotherAlive)
        hasher.combine(draft.parentMotherAgeAtDeath)
        hasher.combine(draft.parentFatherAlive)
        hasher.combine(draft.parentFatherAgeAtDeath)
        hasher.combine(draft.perceivedStressScore)
        hasher.combine(draft.lonelinessScore)
        return hasher.finalize()
    }

    private func scheduleRecompute() {
        recomputeTask?.cancel()
        let engine = ClockEngine(clock: store.clock)
        recomputeTask = Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(80))
            guard !Task.isCancelled else { return }
            draft.recomputeEstimate(using: engine)
        }
    }

    @ViewBuilder
    private func destination(for screen: OnboardingScreen) -> some View {
        switch screen {
        case .welcome:
            WelcomeView(onContinue: { advance(to: .meetYourClock) })
        case .meetYourClock:
            MeetYourClockView(onContinue: { advance(to: .reactiveSlider) })
        case .reactiveSlider:
            ReactiveSliderView(onContinue: { advance(to: .goalPick) })
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
            ArchetypeRevealView(onContinue: { advance(to: .lifeGridRemaining) })
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
                // Free fallback: write the profile. The parent
                // `RootView`'s @Query observes the new UserProfile and
                // swaps to `MainTabView` — no intermediate placeholder
                // screen. We deliberately do NOT advance the path; if
                // the gate flip ever lags a frame, the user briefly
                // sees the dismissed paywall, which is preferable to a
                // generic "Almost there…" filler.
                completeOnboarding()
            })
        }
    }

    private func advance(to next: OnboardingScreen) {
        path.append(next)
    }

    // MARK: - Back navigation

    /// Screens where the back chevron should NOT appear. Once the user
    /// confirms the one-time anchor dial (`engineRevealAndDial`), the
    /// path is reset to `[.recoveryPreview]` so the dial cannot be
    /// reached again — back-nav from any of these would either re-expose
    /// the dial or pop into the cold-open root, neither of which is
    /// correct UX.
    private static let noBackScreens: Set<OnboardingScreen> = [
        .recoveryPreview,
        .healthKitAuth,
        .paywallPrimary,
    ]

    /// True iff the back chevron in the persistent header should be
    /// active. Hidden on the very first push (no prior screen to return
    /// to) and on the post-Confirm screens listed above.
    private var canGoBack: Bool {
        guard path.count >= 2 else { return false }
        guard let current = path.last else { return false }
        return !Self.noBackScreens.contains(current)
    }

    private func popPath() {
        guard !path.isEmpty else { return }
        path.removeLast()
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

    /// Debug-only: jump straight to a terminal-tier onboarding screen
    /// for polish audits. Set `LIFECLOCK_JUMP_TO=recoveryPreview` (or
    /// `healthKitAuth` / `paywallPrimary`) at launch.
    /// Pre-populates the draft so the persistent header's cumulative
    /// trajectory is non-zero and `RecoveryPreviewView` has the inputs
    /// it needs (DOB, sex, lifestyle answers).
    ///
    /// No-op in Release builds — the env-var read is `#if DEBUG` only.
    private func applyJumpFixtureIfNeeded() {
        #if DEBUG
        guard let raw = ProcessInfo.processInfo.environment["LIFECLOCK_JUMP_TO"],
              let target = OnboardingScreen(rawValue: raw),
              path.isEmpty
        else { return }

        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = .gmt
        draft.birthDate = calendar.date(from: DateComponents(year: 1985, month: 6, day: 15))
        draft.biologicalSex = "male"
        draft.heightCm = 178
        draft.weightKg = 82
        let engine = ClockEngine(clock: store.clock)
        // Latch a CLEAN (lifestyle-free) baseline first so the persistent
        // mascot's cumulative delta reflects the answers we're about to
        // load — not zero. Without this, baselineProjectedAgeYears is
        // assigned alongside the loaded inputs and current-baseline=0.
        draft.recomputeEstimate(using: engine)
        // Now load lifestyle answers that yield a clearly-negative
        // trajectory — that's the realistic state at the recovery-preview
        // screen (the user just confirmed a dial; the headline reads
        // "N more years"). A perfectly-healthy fixture would land on the
        // yearsBack==0 fallback copy and not exercise the primary layout.
        draft.smokingStatus = "heavy"
        draft.alcoholFrequency = "heavy"
        draft.strengthFrequencyPerWeek = 0
        draft.cardioMinsPerWeek = 0
        draft.sleepGoalHours = 5.5
        draft.dietQualityBaseline = "rough"
        draft.primaryGoal = .liveLonger
        draft.toneMode = .coach
        draft.personalAdjustmentYears = -2
        draft.anchorAdjustedAt = store.clock.now()
        draft.recomputeEstimate(using: engine)

        // Defer the path swap one runloop tick. Mutating `path` from
        // inside `.onAppear` races with `NavigationStack`'s view-tree
        // settle, leaving the destination view's `GeometryReader` and
        // `Canvas(rendersAsynchronously: true)` paths fighting for the
        // same first frame — the cold-open's auto-advance dispatch
        // (gated on `LIFECLOCK_JUMP_TO`) and our path swap landed in
        // an order that pushed `.welcome` on top of `[target]`. A 50ms
        // `asyncAfter` lands after the current runloop frame and the
        // NavigationStack has stabilized, so the destination renders
        // alone on top.
        //
        // Match `engineRevealAndDial.onConfirm` — terminal screens are
        // unreachable via back-nav, so the path is `[target]` not the
        // accumulated trail to it.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            path = [target]
        }
        #endif
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

