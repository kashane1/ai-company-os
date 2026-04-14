import SwiftUI

struct CatchHistoryRow: View {
    let catchRecord: CatchRecord
    var includeTimestamp: Bool = false

    var body: some View {
        HStack(alignment: .top, spacing: Spacing.md) {
            if let photoData = catchRecord.primaryPhotoData {
                CatchPhotoThumbnailView(data: photoData)
            }

            VStack(alignment: .leading, spacing: Spacing.xs) {
                HStack {
                    Text(catchRecord.speciesDisplayName)
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    if includeTimestamp {
                        Text(AppFormatters.shortTime.string(from: catchRecord.caughtAt))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                let secondaryParts = [catchRecord.lureOrBait, catchRecord.method, catchRecord.gear]
                    .filter { !$0.isEmpty }
                if !secondaryParts.isEmpty {
                    Text(secondaryParts.joined(separator: " · "))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                let metricParts: [String] = [
                    catchRecord.disposition == .notRecorded ? nil : catchRecord.disposition.label,
                    catchRecord.weightKg.map { "\($0.formatted()) kg" },
                    catchRecord.lengthCm.map { "\($0.formatted()) cm" },
                    catchRecord.waterDepthM.map { "\($0.formatted()) m deep" },
                ].compactMap { $0 }

                if !metricParts.isEmpty {
                    Text(metricParts.joined(separator: " · "))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                if catchRecord.photoCount > 1 {
                    Text("\(catchRecord.photoCount) photos")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }

                if !catchRecord.note.isEmpty {
                    Text(catchRecord.note)
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                        .lineLimit(2)
                }
            }
        }
        .padding(.vertical, Spacing.xs)
    }
}
