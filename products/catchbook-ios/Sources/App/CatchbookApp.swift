import SwiftData
import SwiftUI

@main
struct CatchbookApp: App {
    @State private var router = AppRouter()

    init() {
        // Instantiate the shared formatters singleton eagerly so its locale
        // change observer is registered before any view reads a formatter.
        _ = AppFormatters.shared
    }

    var body: some Scene {
        WindowGroup {
            CatchbookRootView(router: router)
        }
        .modelContainer(for: [
            Waterbody.self,
            Spot.self,
            Trip.self,
            CatchRecord.self,
            CatchPhoto.self,
            ConditionSnapshot.self,
            PersonalBest.self,
        ])
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

            NavigationStack {
                SpotsView()
            }
            .tabItem {
                Label("Spots", systemImage: "mappin.and.ellipse")
            }
            .tag(AppTab.spots)

            NavigationStack {
                TripsView()
            }
            .tabItem {
                Label("Trips", systemImage: "clock.arrow.circlepath")
            }
            .tag(AppTab.trips)

            NavigationStack {
                MoreView()
            }
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
