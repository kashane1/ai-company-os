import SwiftUI
import SwiftData

@main
@MainActor
struct LifeClockApp: App {
    let container: ModelContainer
    let launchConfiguration: LifeClockLaunchConfiguration
    @State private var store: LifeClockStore
    @State private var subscriptions: SubscriptionStore
    @State private var hasBootstrapped: Bool = false
    @State private var forcedPaywallPresented: Bool = false
    @State private var forcedPaywallScrollTarget: PaywallSheet.Section? = nil
    @Environment(\.scenePhase) private var scenePhase

    init() {
        let launchConfiguration = LifeClockLaunchConfiguration.current
        self.launchConfiguration = launchConfiguration
        let container: ModelContainer
        do {
            container = try LifeClockContainer.make(inMemory: launchConfiguration.useInMemoryStore)
        } catch {
            fatalError("ModelContainer init failed: \(error)")
        }
        self.container = container
        launchConfiguration.seedInitialStateIfNeeded(in: container.mainContext)
        let notificationsService = NotificationsService()
        // Foreground delegate must be set BEFORE any notification could
        // arrive — otherwise iOS silently suppresses foreground banners.
        notificationsService.installForegroundDelegate()
        let store = LifeClockStore(
            healthService: launchConfiguration.makeHealthService(),
            modelContext: container.mainContext,
            engineClock: launchConfiguration.clock,
            notificationsService: notificationsService
        )
        // V1.7.0: tab selection lives on the store so cross-tab
        // navigation (TodayView trajectory peek → Future) works from
        // any view. Seed from the launch config so initial-tab and
        // JUMP_TO knobs continue to land deterministically.
        store.selectedTab = launchConfiguration.effectiveInitialTab
        // Construct SubscriptionStore here (rather than inline in the
        // @State default) so we can wire it as the entitlement source on
        // `store` BEFORE the first frame renders. This eliminates the
        // race window where a Pro user could tap into the override flow
        // before `.task` runs and see the .notEntitled error.
        let subscriptions = SubscriptionStore()
        store.entitlements = subscriptions
        if let forced = launchConfiguration.forcePalette {
            // Set on the pre-bootstrap store so the first rendered frame
            // (including jump-to-terminal-onboarding screens that never
            // load a UserProfile) tints with the forced palette. The
            // seed pre-writes the same value into the seeded profile, so
            // bootstrap()'s restore won't disagree on `.onboarded` runs.
            store.palette = forced
        }
        _store = State(wrappedValue: store)
        _subscriptions = State(wrappedValue: subscriptions)
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .environment(subscriptions)
                .tint(store.palette.accent)
                .preferredColorScheme(forcedColorScheme)
                .task {
                    await store.bootstrap()
                    hasBootstrapped = true
                    await subscriptions.loadProducts()
                    await subscriptions.refreshEntitlements()
                    // Test-only: present the paywall on launch so an XCUITest
                    // can audit the paywall.close path without first navigating
                    // to Profile and triggering a purchase flow.
                    // V1.7.0: also triggered by LIFECLOCK_JUMP_TO=
                    // paywallWhatIfSection — same path, with scrollTo wired.
                    if launchConfiguration.effectiveForcePaywall {
                        forcedPaywallScrollTarget = launchConfiguration.effectivePaywallScrollTarget
                        forcedPaywallPresented = true
                    }
                }
                .onChange(of: scenePhase) { _, newPhase in
                    // Catch permission flips made in iOS Settings without
                    // requiring a relaunch. Skip the first .active
                    // transition — bootstrap() already refreshed and
                    // reconciled.
                    guard newPhase == .active, hasBootstrapped else { return }
                    Task {
                        await store.refreshNotificationAuthorization()
                        // Day may have rolled over while backgrounded;
                        // re-run the wrap-up coordinator. The 300s short-
                        // circuit in refreshFromHealthKit prevents redundant
                        // HK fetches on rapid foregrounds.
                        await store.refreshFromHealthKit()
                    }
                }
                .sheet(isPresented: $forcedPaywallPresented) {
                    PaywallSheet(scrollTo: forcedPaywallScrollTarget)
                        .environment(subscriptions)
                }
                .sheet(item: wrapUpBinding) { wrapUp in
                    WrapUpSheet(
                        wrapUp: wrapUp,
                        signedMinutes: wrapUpMinutes(for: wrapUp),
                        toneMode: store.toneMode,
                        onDismiss: {
                            store.markWrapUpShown(wrapUp)
                        }
                    )
                }
        }
        .modelContainer(container)
    }

    /// Bridges `store.pendingWrapUp` (a tracked property) into a binding the
    /// sheet modifier can drive. Setting the binding back to nil triggers the
    /// dismiss path.
    private var wrapUpBinding: Binding<WrapUpCoordinator.PendingWrapUp?> {
        Binding(
            get: { store.pendingWrapUp },
            set: { newValue in
                if newValue == nil, let presented = store.pendingWrapUp {
                    // Sheet dismissed via swipe / outside tap — advance state
                    // so the same wrap-up doesn't immediately re-present.
                    store.markWrapUpShown(presented)
                }
            }
        )
    }

    private var forcedColorScheme: ColorScheme? {
        switch launchConfiguration.forceColorScheme {
        case .light: return .light
        case .dark: return .dark
        case nil: return nil
        }
    }

    private func wrapUpMinutes(for wrapUp: WrapUpCoordinator.PendingWrapUp) -> Int {
        switch wrapUp {
        case .yesterday: return store.yesterdayDeltaMinutes ?? 0
        case .weekly: return store.lastWeekDeltaMinutes ?? 0
        }
    }
}

// `WrapUpCoordinator.PendingWrapUp` has to be `Identifiable` for SwiftUI's
// `.sheet(item:)` modifier. Synthesize a stable id from the case data.
extension WrapUpCoordinator.PendingWrapUp: Identifiable {
    public var id: String {
        switch self {
        case .yesterday(let date): return "yesterday-\(date.timeIntervalSince1970)"
        case .weekly(let weekStart): return "weekly-\(weekStart.timeIntervalSince1970)"
        }
    }
}

struct RootView: View {
    @Query private var profiles: [UserProfile]

    var body: some View {
        if profiles.isEmpty {
            OnboardingCoordinator()
        } else {
            MainTabView()
        }
    }
}

struct MainTabView: View {
    @Environment(LifeClockStore.self) private var store

    private var futureTabVisible: Bool {
        // Two gates: (1) onboarding complete — Future tab requires a
        // baseline; (2) launch-config flag — DEBUG default true, RELEASE
        // default false until Phase 4 ships. Either gate failing hides
        // the tab entirely (no half-built UI on TestFlight; no
        // baseline-less tab for fresh installs).
        guard LifeClockLaunchConfiguration.current.futureTabUnlocked else { return false }
        guard store.profile?.onboardingCompletedAt != nil else { return false }
        return true
    }

    var body: some View {
        @Bindable var store = store
        TabView(selection: $store.selectedTab) {
            TodayView()
                .tabItem { Label(AppTab.today.title, systemImage: AppTab.today.systemImage) }
                .tag(AppTab.today)

            HistoryView()
                .tabItem { Label(AppTab.history.title, systemImage: AppTab.history.systemImage) }
                .tag(AppTab.history)

            if futureTabVisible {
                FutureView()
                    .tabItem { Label(AppTab.future.title, systemImage: AppTab.future.systemImage) }
                    .tag(AppTab.future)
            }

            ProfileView()
                .tabItem { Label(AppTab.profile.title, systemImage: AppTab.profile.systemImage) }
                .tag(AppTab.profile)
        }
    }
}
