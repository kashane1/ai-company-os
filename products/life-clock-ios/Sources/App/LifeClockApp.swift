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
        // Construct SubscriptionStore here (rather than inline in the
        // @State default) so we can wire it as the entitlement source on
        // `store` BEFORE the first frame renders. This eliminates the
        // race window where a Pro user could tap into the override flow
        // before `.task` runs and see the .notEntitled error.
        let subscriptions = SubscriptionStore()
        store.entitlements = subscriptions
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
                    if launchConfiguration.forcePaywall {
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
                    PaywallSheet()
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
    @State private var selection: AppTab = LifeClockLaunchConfiguration.current.initialTab

    var body: some View {
        TabView(selection: $selection) {
            TodayView()
                .tabItem { Label(AppTab.today.title, systemImage: AppTab.today.systemImage) }
                .tag(AppTab.today)

            HistoryView()
                .tabItem { Label(AppTab.history.title, systemImage: AppTab.history.systemImage) }
                .tag(AppTab.history)

            ProfileView()
                .tabItem { Label(AppTab.profile.title, systemImage: AppTab.profile.systemImage) }
                .tag(AppTab.profile)
        }
    }
}
