import SwiftData
@testable import Catchbook

struct ModelTestStore {
    let container: ModelContainer
    let context: ModelContext
}

enum ModelTestSupport {
    static func makeStore() throws -> ModelTestStore {
        let schema = Schema([
            Waterbody.self,
            Spot.self,
            ConditionSnapshot.self,
            Trip.self,
            CatchRecord.self,
            PersonalBest.self,
        ])
        let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
        let container = try ModelContainer(for: schema, configurations: configuration)
        let context = ModelContext(container)
        return ModelTestStore(container: container, context: context)
    }
}
