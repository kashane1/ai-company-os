import Foundation
import PhotosUI
import SwiftUI

enum CatchPhotoLoadResult: Equatable {
    case loaded(Data)
    case unavailable
}

enum CatchPhotoLoader {
    static func load(from item: PhotosPickerItem) async -> CatchPhotoLoadResult {
        await load {
            try await item.loadTransferable(type: Data.self)
        }
    }

    static func load(_ dataSource: () async throws -> Data?) async -> CatchPhotoLoadResult {
        do {
            return resolve(data: try await dataSource())
        } catch {
            return .unavailable
        }
    }

    static func resolve(data: Data?) -> CatchPhotoLoadResult {
        guard let data, !data.isEmpty else { return .unavailable }
        return .loaded(data)
    }
}
