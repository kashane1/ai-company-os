import SwiftUI

@Observable
class AppRouter {
    var selectedTab: AppTab = .home
    var homePath: [HomeDestination] = []
    var pendingTripStart: TripStartContext?

    func showActiveTrip(_ trip: Trip) {
        selectedTab = .home
        homePath = [.activeTrip(trip)]
    }

    func navigateToTripHistory(_ trip: Trip) {
        selectedTab = .trips
    }

    func requestTripStart(spot: Spot? = nil, waterbody: Waterbody? = nil) {
        selectedTab = .home
        pendingTripStart = TripStartContext(preselectedSpot: spot, preselectedWaterbody: waterbody)
    }
}

enum HomeDestination: Hashable {
    case activeTrip(Trip)

    static func == (lhs: HomeDestination, rhs: HomeDestination) -> Bool {
        switch (lhs, rhs) {
        case let (.activeTrip(a), .activeTrip(b)):
            return a.id == b.id
        }
    }

    func hash(into hasher: inout Hasher) {
        switch self {
        case let .activeTrip(trip):
            hasher.combine(trip.id)
        }
    }
}

struct TripStartContext: Identifiable {
    let id = UUID()
    let preselectedSpot: Spot?
    let preselectedWaterbody: Waterbody?
}
