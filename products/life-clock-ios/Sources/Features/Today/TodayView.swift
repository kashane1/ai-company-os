import SwiftUI

struct TodayView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(SubscriptionStore.self) private var subscriptions
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var quickLogPresented: Bool = false
    @State private var reflectionPresented: Bool = false
    @State private var planEditorPresented: Bool = false
    @State private var paywallPresented: Bool = false
    @State private var connectingHealth: Bool = false

    /// Wake animation: `wakeProgress` ramps 0→1 every time the app opens
    /// (cold launch + foreground). Both the headline number and the mascot
    /// hands derive from it, so they animate in lockstep from a single
    /// source. `mascotWakeTrigger` is the one-shot input to the mascot
    /// scale keyframe (increment to fire). Tab-switches inside the same
    /// session do NOT replay — `hasFiredOnce` keeps the on-appear path
    /// honest, while scenePhase handles every fresh foreground.
    /// Cadence per `feedback_life_clock_wake_animation.md` memory.
    @State private var wakeProgress: Double = 1.0
    @State private var mascotWakeTrigger: Int = 0
    @State private var morningWakeHapticTrigger: Int = 0
    @State private var hasFiredOnce: Bool = false

    /// One-shot trigger for the quest-completion mascot SCALE keyframe
    /// (vision Q14, 2026-05-09). Increments on every completion-overlay
    /// INCREASE (check), not decrease (uncheck). Suppressed entirely
    /// when Reduce Motion is on — the visible clock movement (gated
    /// by LifeClockMascotView's own reduceMotion check) carries the
    /// moment without a celebration scale pulse.
    @State private var questCompletionPulseTrigger: Int = 0

    /// Separate trigger for the success haptic so haptic fires under
    /// Reduce Motion even when the scale pulse is suppressed. iOS's
    /// "Reduce Motion" accessibility setting does not disable haptics —
    /// users with motion sensitivity often rely on haptic feedback.
    @State private var questCompletionHapticTrigger: Int = 0
    @State private var monthlyMilestoneHapticTrigger: Int = 0

    /// Last observed `completionOverlay` value, used to detect
    /// increase-vs-decrease transitions for the pulse trigger.
    @State private var lastObservedOverlay: Int = 0
    @State private var lastMilestoneHapticKey: String?

    /// Wall-clock budget for the wake sequence. Hand sweep + count-up
    /// share this duration; the mascot scale keyframe runs concurrently
    /// and finishes inside it. Bumped from 0.50s to 1.0s after live
    /// review — 0.5s read as "did something just flash?", 1.0s feels
    /// like a greeting.
    private static let wakeDuration: Double = 1.0

    /// In-day "felt time" surcharge: the sum of `rewardEstimateMinutes`
    /// for today's quests the user has marked complete. Persist-banked
    /// per vision Q14 / Q-plan-1 — completing a quest visibly moves the
    /// clock and the move PERSISTS for the rest of the day; unchecking
    /// retracts.
    ///
    /// Derived (not @State); the store's observable mechanism re-fires
    /// `displayedDelta` on every `toggleQuestCompletion` write. Day
    /// boundary clears it automatically because today's `Quest`
    /// instances become yesterday's at midnight and today's fresh
    /// quests have `completedAt == nil`. No special-case code.
    ///
    /// Important model-truth note: this overlay does NOT enter
    /// `ClockEngine.calculateDailyDelta`. Quest reward minutes are a
    /// projection of *tomorrow's* HK signal (more steps from the walk,
    /// etc.), not earned-today. The visible headline shows
    /// `canonical + overlay`; the canonical (model truth) is recoverable
    /// by inspecting `store.todayEstimate?.dailyTimeDeltaMinutes`.
    private var completionOverlay: Int {
        let dayStart = store.clock.calendar.startOfDay(for: store.clock.now())
        return store.todayQuests
            .filter { quest in
                guard let completedAt = quest.completedAt else { return false }
                return store.clock.calendar.isDate(completedAt, inSameDayAs: dayStart)
            }
            .map(\.rewardEstimateMinutes)
            .reduce(0, +)
    }

    /// The delta value driving both the headline count-up and the mascot
    /// hand sweep. When `wakeProgress < 1` (mid-animation), this is a
    /// linear interpolation from 0 toward `(canonical + overlay)`; once
    /// settled, it's `(canonical + overlay)`. Single source of truth for
    /// the wake sequence + the persist-banked completion sequence.
    /// `LifeClockMascotView`'s existing
    /// `.animation(.interpolatingSpring(), value: minutesDelta)` handles
    /// the visual transition on every overlay change for free.
    private var displayedDelta: Int {
        let real = store.todayEstimate?.dailyTimeDeltaMinutes ?? 0
        return Int(((Double(real) + Double(completionOverlay)) * wakeProgress).rounded())
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                // 2026-05-01 IA refactor: Today is the daily ritual surface
                // (score → why → plan → reflection → check-in). Order is
                // deliberate; do not reshuffle without revisiting the
                // brainstorm in docs/plans/2026-05-01-refactor-life-clock-
                // tab-consolidation-plan.md.
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    headline
                    mascotHero
                    clockCard
                    rescueLine
                    if let moment = store.supportMoment {
                        supportMomentCard(moment)
                    }
                    driversCard
                    questsCard
                    ReflectionCard(onTap: { reflectionPresented = true })
                    quickLogCard
                    monthlyLoggingBanner
                    DisclaimerBanner()
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle(store.toneMode.todayHeadline)
            // At accessibility text sizes a large title with "Today's
            // progress" / "Today's reckoning" overflows and ellipsizes
            // (caught 2026-05-06 axxl recon — "Today's prog…"). Inline
            // mode lets the title shrink to the available width.
            .navigationBarTitleDisplayMode(
                dynamicTypeSize.isAccessibilitySize ? .inline : .large
            )
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        quickLogPresented = true
                    } label: {
                        Label("Check in", systemImage: "square.and.pencil")
                    }
                    .accessibilityIdentifier("today.checkInToolbar")
                }
            }
            .sheet(isPresented: $quickLogPresented) {
                QuickLogSheet()
            }
            .sheet(isPresented: $reflectionPresented) {
                let prompt = ReflectionPrompts.prompt(
                    for: store.clock.now(),
                    tone: store.toneMode,
                    calendar: store.clock.calendar
                )
                ReflectionSheet(
                    prompt: prompt,
                    onDismiss: { reflectionPresented = false }
                )
            }
            .sheet(isPresented: $planEditorPresented) {
                PlanEditorSheet()
            }
            .sheet(isPresented: $paywallPresented) {
                PaywallSheet()
            }
            .onAppear {
                // Cold launch: fire once. Tab-switches back to Today
                // re-call .onAppear too — the flag suppresses replay
                // within the same session. Background→foreground is
                // handled separately by the scenePhase listener below.
                guard !hasFiredOnce else { return }
                hasFiredOnce = true
                lastObservedOverlay = completionOverlay
                triggerWakeIfPossible()
                triggerMonthlyMilestoneHapticIfNeeded()
                #if DEBUG
                if LifeClockLaunchConfiguration.current.forceQuickLog {
                    quickLogPresented = true
                }
                #endif
            }
            .onChange(of: scenePhase) { _, newPhase in
                if newPhase == .active { triggerWakeIfPossible() }
            }
            .onChange(of: store.monthlyLogging) { _, _ in
                triggerMonthlyMilestoneHapticIfNeeded()
            }
            .onChange(of: completionOverlay) { oldValue, newValue in
                // Pulse fires only on overlay increase (check), not
                // decrease (uncheck). Uncheck path is the visible
                // mascot retraction alone — no celebration feedback.
                guard newValue > oldValue else {
                    lastObservedOverlay = newValue
                    return
                }
                // Defer if wake is still in flight; the pulse + haptic
                // would compete with the count-up. Wake completes inside
                // 1.0s; a tap during wake is rare. Per plan Q-plan-7
                // discussion, we do not retroactively fire after wake
                // settles — the visible clock movement is the message.
                guard wakeProgress >= 1.0 else {
                    lastObservedOverlay = newValue
                    return
                }
                // Haptic fires regardless of Reduce Motion (haptics are
                // a separate accessibility surface). Scale keyframe
                // suppressed under Reduce Motion — the visible mascot
                // hand spring (already reduceMotion-gated inside
                // LifeClockMascotView) carries the visual moment.
                questCompletionHapticTrigger &+= 1
                if !reduceMotion {
                    questCompletionPulseTrigger &+= 1
                }
                lastObservedOverlay = newValue
            }
        }
    }

    /// Plays the wake animation if it's safe to:
    /// - reduce-motion is OFF
    /// - not running under XCUITest (deterministic snapshots)
    /// - we have a real estimate to count up to (the mascot+headline
    ///   already render "Loading…" otherwise; no point sweeping to 0)
    ///
    /// Snaps `wakeProgress` to 0 with no animation, then `withAnimation`
    /// to 1 over `wakeDuration`. The mascot scale keyframe fires off
    /// `mascotWakeTrigger` and runs concurrently inside the same budget.
    private func triggerWakeIfPossible() {
        guard !reduceMotion,
              !LifeClockLaunchConfiguration.current.isUITest,
              store.todayEstimate != nil
        else { return }

        wakeProgress = 0
        withAnimation(.easeOut(duration: Self.wakeDuration)) {
            wakeProgress = 1
        }
        morningWakeHapticTrigger &+= 1
        mascotWakeTrigger &+= 1
    }

    private func triggerMonthlyMilestoneHapticIfNeeded() {
        guard !LifeClockLaunchConfiguration.current.isUITest,
              let milestone = store.monthlyLogging.milestone,
              store.monthlyLogging.daysLogged >= 1
        else { return }

        let key = [
            store.monthlyLogging.monthName,
            String(describing: milestone),
            "\(store.monthlyLogging.daysLogged)",
        ].joined(separator: ":")
        guard key != lastMilestoneHapticKey else { return }

        lastMilestoneHapticKey = key
        monthlyMilestoneHapticTrigger &+= 1
    }

    private var quickLogCard: some View {
        Button {
            quickLogPresented = true
        } label: {
            HStack {
                Image(systemName: "square.and.pencil")
                VStack(alignment: .leading) {
                    Text(store.todayHabits == nil ? "Save today's check-in" : "Update today's check-in")
                        .font(.callout.bold())
                    Text("Fuel, extras, recovery, strength, nicotine. About 30 seconds.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(.secondary)
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("today.checkInCard")
    }

    private var headline: some View {
        Group {
            if let estimate = store.todayEstimate, canJustifyTodayHeadline {
                // Final-value sign drives the prefix and color; mid-sweep
                // would otherwise read "+0 min" in green for a negative
                // day. Visible NUMBER is the wake-animated value.
                let realDelta = estimate.dailyTimeDeltaMinutes
                let shown = displayedDelta
                let prefix = realDelta >= 0 ? store.toneMode.deltaPositivePrefix : store.toneMode.deltaNegativePrefix
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text("\(prefix) today")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(TimeDeltaFormatter.format(minutes: shown))
                        .font(.system(size: 44, weight: .semibold, design: .rounded))
                        .foregroundStyle(realDelta >= 0 ? DesignTokens.Palette.positive : DesignTokens.Palette.negative)
                        .contentTransition(.numericText(value: Double(shown)))
                        .monospacedDigit()
                    Text(LifeClockConfiguration.lifespanShortDisclaimer)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("today.lifespanShortDisclaimer")
                    if let confidence = Confidence(rawValue: estimate.confidenceRaw) {
                        ConfidenceBadge(confidence: confidence)
                    }
                }
            } else if let estimate = store.todayEstimate {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text("Today")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(sparseHeadlineTitle)
                        .font(.title2.weight(.semibold))
                    Text(sparseHeadlineBody)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    if store.healthDataState == .awaitingAuthorization {
                        // Inline affordance so the sparse "Connect Apple
                        // Health" headline isn't a dead end — without
                        // this the user has to discover the Profile tab.
                        // Under `.noRecentData` the system sheet won't
                        // re-prompt (Apple caches the prior choice), so
                        // we deliberately do NOT surface this button
                        // there; Profile's `Open Settings` is the
                        // correct path in that branch.
                        Button {
                            connectingHealth = true
                            Task {
                                await store.requestHealthAuthorization()
                                connectingHealth = false
                            }
                        } label: {
                            HStack(spacing: DesignTokens.Spacing.xs) {
                                Text("Connect Apple Health")
                                if connectingHealth { ProgressView() }
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.small)
                        .disabled(connectingHealth)
                        .padding(.top, DesignTokens.Spacing.xs)
                        .accessibilityIdentifier("today.headlineSparse.connect")
                    }
                    if let confidence = Confidence(rawValue: estimate.confidenceRaw) {
                        ConfidenceBadge(confidence: confidence)
                    }
                }
                .accessibilityIdentifier("today.headlineSparse")
            } else {
                Text("Loading…").foregroundStyle(.secondary)
            }
        }
        .accessibilityIdentifier("today.headline")
    }

    /// Tone-modulated "patterns, not perfection" line. Renders only when
    /// today netted negative AND a diet signal (`rough` quality, `skipBinge`
    /// rhythm, or `no` whole-food anchor) was logged. Equatable inputs let
    /// SwiftUI skip body re-evaluation when unchanged. Returns `EmptyView`
    /// when the predicate is false.
    private var rescueLine: some View {
        let delta = store.todayEstimate?.dailyTimeDeltaMinutes ?? 0
        return RescueLine(
            netDelta: delta,
            dietQuality: store.todayHabits?.dietQuality ?? "",
            rhythm: store.todayHabits?.dietAmountRhythm ?? "",
            anchor: store.todayHabits?.wholeFoodMeal ?? "",
            tone: store.toneMode
        )
    }

    private func supportMomentCard(_ moment: SupportMoment) -> some View {
        SupportMomentCard(
            moment: moment,
            dismissAction: store.dismissSupportMoment
        )
        .accessibilityIdentifier("today.supportMoment")
    }

    /// "Projected healthspan + anchor date" card. Hidden entirely when
    /// `profile.hideClock` is true — replaced by the headline-only path
    /// (the "+X min today" delta still renders above). Resolves Q5 and is
    /// the centerpiece of the safety-net offering.
    ///
    /// Hero mascot above the projected-healthspan readout. Renders only
    /// when there's an estimate AND the user hasn't hidden the clock.
    /// Both this view and `clockCard` read from the same
    /// `store.todayEstimate.dailyTimeDeltaMinutes` binding, so the visual
    /// hands and the textual delta animate from a single source.
    @ViewBuilder
    private var mascotHero: some View {
        if store.profile?.hideClock == true {
            // Zero-height marker so an agent / UITest can positively
            // verify "user hid the clock" rather than only inferring
            // it from the absence of `today.mascot`.
            Color.clear
                .frame(height: 0)
                .accessibilityIdentifier("today.mascotHidden")
                .accessibilityHidden(true)
        } else if store.todayEstimate != nil {
            // Hands rotate from 12 baseline by `displayedDelta * 6°`
            // (see `LifeClockMascotView`). Driving by `displayedDelta`
            // means the morning sweep falls out of changing one value.
            // The scale keyframe overlays a one-shot wake bump on top.
            LifeClockMascotView(minutesDelta: displayedDelta)
                .frame(maxWidth: 240, maxHeight: 240)
                .frame(maxWidth: .infinity, alignment: .center)
                .keyframeAnimator(
                    initialValue: 1.0,
                    trigger: mascotWakeTrigger
                ) { content, scale in
                    content.scaleEffect(scale)
                } keyframes: { _ in
                    KeyframeTrack {
                        CubicKeyframe(1.00, duration: 0.0)
                        CubicKeyframe(1.06, duration: 0.40)
                        SpringKeyframe(1.00, duration: 0.60, spring: .bouncy)
                    }
                }
                // Quest-completion pulse, parallel to the wake keyframe
                // above. Subtler scale than wake (1.045 vs 1.06) and
                // shorter (520ms vs ~1s) — wake is a "good morning,"
                // pulse is a "nice tap" acknowledgement. Vision Q14.
                .keyframeAnimator(
                    initialValue: 1.0,
                    trigger: questCompletionPulseTrigger
                ) { content, scale in
                    content.scaleEffect(scale)
                } keyframes: { _ in
                    KeyframeTrack {
                        CubicKeyframe(1.00, duration: 0.0)
                        CubicKeyframe(1.045, duration: 0.22)
                        SpringKeyframe(1.00, duration: 0.30, spring: .bouncy)
                    }
                }
                .sensoryFeedback(.success, trigger: questCompletionHapticTrigger)
                .sensoryFeedback(LifeClockHaptics.morningWake, trigger: morningWakeHapticTrigger)
                .accessibilityIdentifier("today.mascot")
        } else {
            EmptyView()
        }
    }

    @ViewBuilder
    private var clockCard: some View {
        if store.profile?.hideClock == true {
            EmptyView()
        } else {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text("Projected healthspan")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text(store.todayEstimate.map { TimeDeltaFormatter.format(years: $0.projectedAgeYears) } ?? "—")
                    .font(.title.bold())
                if let projected = store.todayEstimate?.projectedDate {
                    Text("Reference date: \(projected.formatted(.dateTime.year().month().day()))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
            .accessibilityIdentifier("today.healthspan")
        }
    }

    private var driversCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(store.toneMode.todayDriversHeading)
                .font(.headline)
            if store.todayDrivers.isEmpty {
                Text(driversEmptyStateText)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            } else {
                Text(interpretationLine)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("today.drivers.interpretation")
                ForEach(Array(store.todayDrivers.prefix(3).enumerated()), id: \.element.id) { index, driver in
                    HStack {
                        Text(driver.title).lineLimit(1)
                        Spacer()
                        Text(TimeDeltaFormatter.format(minutes: driver.deltaMinutes))
                            .foregroundStyle(driver.deltaMinutes >= 0 ? DesignTokens.Palette.positive : DesignTokens.Palette.negative)
                    }
                    .font(.callout)
                    .accessibilityIdentifier("today.driver.\(driver.driverType)")
                    .accessibilityValue(TimeDeltaFormatter.format(minutes: driver.deltaMinutes))
                }
                if let dietHint = dietContextLine {
                    Text(dietHint)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        .accessibilityIdentifier("today.drivers")
    }

    private var canJustifyTodayHeadline: Bool {
        !store.todayDrivers.isEmpty
    }

    private var sparseHeadlineTitle: String {
        switch store.healthDataState {
        case .unavailable:
            return "Apple Health unavailable"
        case .awaitingAuthorization:
            return "Connect Apple Health"
        case .historicalOnly:
            return "Waiting on today's signal"
        case .noRecentData:
            return "Waiting on data"
        case .availableToday:
            return "Waiting on data"
        }
    }

    private var sparseHeadlineBody: String {
        switch store.healthDataState {
        case .unavailable:
            return "This device can't share Apple Health data, so the clock won't guess at a daily minute change."
        case .awaitingAuthorization:
            return "We can't justify a minute estimate until Apple Health is allowed to share today's signal."
        case .historicalOnly:
            return "Earlier history is still here, but we can't justify a new minute estimate until today's Apple Health data arrives."
        case .noRecentData:
            return "We can't currently see Apple Health data, so the clock won't invent precision."
        case .availableToday:
            return "We need more signal before claiming a daily minute change."
        }
    }

    private var driversEmptyStateText: String {
        switch store.healthDataState {
        case .unavailable:
            return "Apple Health isn't available on this device. Save a quick check-in to start seeing patterns."
        case .awaitingAuthorization:
            return "We can't see your Apple Health data yet. Connect Apple Health or save a quick check-in to start seeing patterns."
        case .historicalOnly:
            return "We can't see today's Apple Health data yet. Your earlier history is still here. Save a quick check-in or review what's shared in Apple Health."
        case .noRecentData:
            return "We can't currently see your Apple Health data. Save a quick check-in, or review what's shared in Apple Health so the clock doesn't have to guess."
        case .availableToday:
            return store.toneMode.todayDriversEmptyState
        }
    }

    /// One-line plain-language interpretation that frames the headline
    /// delta. Sits below "Why it changed" and above the driver list. Reads
    /// the headline delta sign + the top driver title (a primitive — keeps
    /// `ToneMode` SwiftData-free per its `import Foundation`-only boundary).
    private var interpretationLine: String {
        guard let estimate = store.todayEstimate else {
            return store.toneMode.todayInterpretationPreData()
        }
        let topTitle = store.todayDrivers.first?.title
        return estimate.dailyTimeDeltaMinutes >= 0
            ? store.toneMode.todayInterpretationPositive(driverTitle: topTitle)
            : store.toneMode.todayInterpretationNegative(driverTitle: topTitle)
    }

    /// Calendar-month "kind streak" banner (vision Q7, 2026-05-06). Shows
    /// when the user has logged at least one day this month. The chain
    /// cannot break: missed days never decrement the count and the only
    /// reset is the calendar rolling over on the 1st. Milestone days
    /// (1, 25%, 50%, 75% of the month elapsed) swap the secondary line
    /// for tone-aware milestone copy that names the moment without
    /// shaming the count.
    @ViewBuilder
    private var monthlyLoggingBanner: some View {
        let monthly = store.monthlyLogging
        if monthly.daysLogged >= 1 {
            HStack(alignment: .firstTextBaseline, spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "calendar")
                    .foregroundStyle(.orange)
                VStack(alignment: .leading, spacing: 4) {
                    Text(monthly.daysLogged == 1
                        ? "1 day logged so far · \(monthly.monthName)"
                        : "\(monthly.daysLogged) days logged so far · \(monthly.monthName)")
                        .font(.callout.bold())
                    Text(secondaryLine(for: monthly))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer(minLength: 0)
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
            .accessibilityIdentifier("today.monthlyLogging")
            .accessibilityValue("\(monthly.daysLogged) days this month")
            .sensoryFeedback(LifeClockHaptics.monthlyMilestone, trigger: monthlyMilestoneHapticTrigger)
        } else {
            EmptyView()
        }
    }

    private func secondaryLine(for monthly: MonthlyLogging) -> String {
        if let milestone = monthly.milestone {
            return store.toneMode.monthlyLoggingMilestoneLine(
                milestone,
                daysLogged: monthly.daysLogged,
                monthName: monthly.monthName
            )
        }
        return store.toneMode.monthlyLoggingNeutralLine
    }

    /// One soft, plain-language line about today's diet impact when relevant.
    /// Only fires when diet is actually a top driver — avoids "you ate badly"
    /// nagging on days the user didn't log.
    private var dietContextLine: String? {
        let dietDriver = store.todayDrivers.first { $0.driverType == "diet" }
        guard let dietDriver else { return nil }
        if dietDriver.deltaMinutes > 0 {
            return "Your meals supported today's progress."
        }
        return "A rough food day is feedback, not failure. One better meal can help tomorrow feel steadier."
    }

    /// Equatable so SwiftUI's diffing can skip body re-eval when inputs
    /// unchanged. Inputs are primitives — no SwiftData entities — matching
    /// the `ToneMode` Foundation-only convention.
    struct RescueLine: View, Equatable {
        let netDelta: Int
        let dietQuality: String
        let rhythm: String
        let anchor: String
        let tone: ToneMode

        var shouldShow: Bool {
            netDelta < 0 &&
                (dietQuality.lowercased() == "rough"
                    || rhythm.lowercased() == "skipbinge"
                    || anchor.lowercased() == "no")
        }

        var body: some View {
            if shouldShow {
                Text(tone.todayRescueBody())
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .accessibilityIdentifier("today.rescueLine")
            } else {
                EmptyView()
            }
        }
    }

    private var questsCard: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Text(store.toneMode.todayPlanHeading)
                    .font(.headline)
                Spacer()
                Button {
                    if subscriptions.isPro {
                        planEditorPresented = true
                    } else {
                        paywallPresented = true
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: subscriptions.isPro ? "slider.horizontal.3" : "lock.fill")
                        Text(subscriptions.isPro ? "Edit" : "Pro")
                    }
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier(subscriptions.isPro ? "today.planEdit" : "today.planEditLocked")
            }
            Text(store.toneMode.todayPlanSubline)
                .font(.caption)
                .foregroundStyle(.secondary)
            ForEach(Array(store.todayQuests.enumerated()), id: \.element.id) { index, quest in
                Button {
                    store.toggleQuestCompletion(quest)
                } label: {
                    HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
                        Image(systemName: quest.completedAt == nil ? "circle" : "checkmark.circle.fill")
                            .foregroundStyle(quest.completedAt == nil ? .secondary : DesignTokens.Palette.positive)
                        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                            Text(quest.title).font(.callout.bold())
                            Text(quest.detail).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("today.planAction.\(index)")
                // Carries the completion state into the a11y tree so
                // UITests can assert the toggle actually flipped, not
                // just that the button still exists. Tests read this
                // via XCUIElement.value.
                .accessibilityValue(quest.completedAt == nil ? "incomplete" : "complete")
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        // `.contain` preserves child identifiers (today.planEditLocked,
        // today.planAction.<i>) instead of clobbering them with the
        // container's own id, which is the default SwiftUI behavior.
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("today.plan")
    }
}
