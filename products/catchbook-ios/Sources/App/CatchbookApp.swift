import SwiftData
import SwiftUI

@main
struct CatchbookApp: App {
    @State private var router = AppRouter()
    private let modelContainer: ModelContainer

    init() {
        // Instantiate the shared formatters singleton eagerly so its locale
        // change observer is registered before any view reads a formatter.
        _ = AppFormatters.shared

        let schema = Schema([
            Waterbody.self,
            Spot.self,
            Trip.self,
            CatchRecord.self,
            CatchPhoto.self,
            ConditionSnapshot.self,
            PersonalBest.self,
            SavedLure.self,
        ])
        let configuration = ModelConfiguration(
            isStoredInMemoryOnly: CatchbookLaunchConfiguration.isUITest
        )
        do {
            modelContainer = try ModelContainer(for: schema, configurations: configuration)
        } catch {
            fatalError("Unable to initialize Catchbook data store: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            CatchbookRootView(router: router)
        }
        .modelContainer(modelContainer)
    }
}

enum CatchbookLaunchConfiguration {
    static var isUITest: Bool {
        #if DEBUG
        ProcessInfo.processInfo.environment["CATCHBOOK_UI_TEST"] == "1"
        #else
        false
        #endif
    }
}

private struct CatchbookRootView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var router: AppRouter

    var body: some View {
        TabView(selection: $router.selectedTab) {
            NavigationStack(path: $router.homePath) {
                HomeView()
                    .navigationDestination(for: HomeDestination.self) { destination in
                        switch destination {
                        case let .activeTrip(trip):
                            ActiveTripView(trip: trip) { endedTrip in
                                router.homePath = []
                                router.navigateToTripHistory(endedTrip)
                            }
                        }
                    }
            }
            .tabItem {
                Label("Home", systemImage: "house")
            }
            .tag(AppTab.home)

            SpotsView()
            .tabItem {
                Label("Spots", systemImage: "mappin.and.ellipse")
            }
            .tag(AppTab.spots)

            TripsView()
            .tabItem {
                Label("Trips", systemImage: "clock.arrow.circlepath")
            }
            .tag(AppTab.trips)

            MoreView()
            .tabItem {
                Label("More", systemImage: "ellipsis")
            }
            .tag(AppTab.more)
        }
        .tint(.catchbookOcean)
        .environment(router)
        .task {
            try? CatchPhotoMigrationService.runIfNeeded(context: modelContext)
        }
    }
}
