import Foundation
import SwiftData

struct CatchPhotoDraft: Identifiable, Equatable {
    let id: UUID
    var data: Data
    var contentType: String
    var photoReference: String?

    init(
        id: UUID = UUID(),
        data: Data,
        contentType: String = "image/jpeg",
        photoReference: String? = nil
    ) {
        self.id = id
        self.data = data
        self.contentType = contentType
        self.photoReference = photoReference
    }
}

enum CatchPhotoMigrationService {
    private static let migrationVersionKey = "catchbook.catch-photo-migration.v1"

    static func runIfNeeded(context: ModelContext, userDefaults: UserDefaults = .standard) throws {
        guard !userDefaults.bool(forKey: migrationVersionKey) else { return }

        let catches = try context.fetch(FetchDescriptor<CatchRecord>())
        for catchRecord in catches {
            if !catchRecord.sortedPhotos.isEmpty { continue }
            guard let data = catchRecord.photoData else { continue }

            let photo = CatchPhoto(
                catchRecord: catchRecord,
                createdAt: catchRecord.caughtAt,
                sortOrder: 0,
                photoReference: catchRecord.photoReference,
                photoContentType: catchRecord.photoContentType,
                photoData: data
            )
            catchRecord.photos.append(photo)
            context.insert(photo)
        }

        try context.save()
        userDefaults.set(true, forKey: migrationVersionKey)
    }

    static func sync(
        record: CatchRecord,
        drafts: [CatchPhotoDraft],
        in context: ModelContext
    ) {
        for photo in record.photos {
            context.delete(photo)
        }
        record.photos.removeAll()

        for (index, draft) in drafts.enumerated() {
            let photo = CatchPhoto(
                catchRecord: record,
                createdAt: record.caughtAt,
                sortOrder: index,
                photoReference: draft.photoReference,
                photoContentType: draft.contentType,
                photoData: draft.data
            )
            record.photos.append(photo)
            context.insert(photo)
        }

        if let firstDraft = drafts.first {
            record.photoData = firstDraft.data
            record.photoContentType = firstDraft.contentType
            record.photoReference = firstDraft.photoReference ?? "embedded-photo"
        } else {
            record.photoData = nil
            record.photoContentType = nil
            record.photoReference = nil
        }
    }

    static func drafts(for catchRecord: CatchRecord?) -> [CatchPhotoDraft] {
        guard let catchRecord else { return [] }

        if !catchRecord.sortedPhotos.isEmpty {
            return catchRecord.sortedPhotos.compactMap { photo in
                guard let data = photo.photoData else { return nil }
                return CatchPhotoDraft(
                    id: photo.id,
                    data: data,
                    contentType: photo.photoContentType ?? "image/jpeg",
                    photoReference: photo.photoReference
                )
            }
        }

        guard let data = catchRecord.photoData else { return [] }
        return [
            CatchPhotoDraft(
                data: data,
                contentType: catchRecord.photoContentType ?? "image/jpeg",
                photoReference: catchRecord.photoReference
            )
        ]
    }
}
