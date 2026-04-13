import CoreLocation
import ImageIO
import SwiftUI
import UniformTypeIdentifiers
import UIKit

struct CatchPhotoThumbnailView: View {
    let data: Data
    var size: CGFloat = 64

    var body: some View {
        if let image = UIImage(data: data) {
            Image(uiImage: image)
                .resizable()
                .scaledToFill()
                .frame(width: size, height: size)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .stroke(.quaternary, lineWidth: 1)
                )
        } else {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(.fill.tertiary)
                .frame(width: size, height: size)
                .overlay {
                    Image(systemName: "photo")
                        .foregroundStyle(.secondary)
                }
        }
    }
}

struct CatchPhotoDraftStripView: View {
    let photos: [CatchPhotoDraft]
    let onRemove: (UUID) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                ForEach(photos) { photo in
                    VStack(alignment: .leading, spacing: 6) {
                        CatchPhotoThumbnailView(data: photo.data, size: 72)
                        Button(role: .destructive) {
                            onRemove(photo.id)
                        } label: {
                            Label("Remove", systemImage: "trash")
                                .font(.caption)
                        }
                        .buttonStyle(.borderless)
                    }
                }
            }
            .padding(.vertical, 4)
        }
    }
}

struct CameraCaptureView: UIViewControllerRepresentable {
    let onCapture: (Data) -> Void
    let onCancel: () -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(onCapture: onCapture, onCancel: onCancel)
    }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let controller = UIImagePickerController()
        controller.sourceType = .camera
        controller.cameraCaptureMode = .photo
        controller.delegate = context.coordinator
        return controller
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    final class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        let onCapture: (Data) -> Void
        let onCancel: () -> Void

        init(onCapture: @escaping (Data) -> Void, onCancel: @escaping () -> Void) {
            self.onCapture = onCapture
            self.onCancel = onCancel
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            onCancel()
        }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            guard let image = info[.originalImage] as? UIImage else {
                onCancel()
                return
            }
            let metadata = info[.mediaMetadata] as? [String: Any]
            guard let data = jpegData(for: image, metadata: metadata) else {
                onCancel()
                return
            }
            onCapture(data)
        }

        private func jpegData(for image: UIImage, metadata: [String: Any]?) -> Data? {
            guard let cgImage = image.cgImage else {
                return image.jpegData(compressionQuality: 0.9)
            }

            let data = NSMutableData()
            guard let destination = CGImageDestinationCreateWithData(
                data,
                UTType.jpeg.identifier as CFString,
                1,
                nil
            ) else {
                return image.jpegData(compressionQuality: 0.9)
            }

            CGImageDestinationAddImage(destination, cgImage, metadata as CFDictionary?)
            guard CGImageDestinationFinalize(destination) else {
                return image.jpegData(compressionQuality: 0.9)
            }

            return data as Data
        }
    }
}

struct PhotoSpotSuggestionCard: View {
    let suggestion: CatchPhotoLocationSuggestion
    let currentSpotID: UUID?
    let pendingSpotID: UUID?
    let onUseSpot: (UUID) -> Void

    private var activeSpotID: UUID? {
        pendingSpotID ?? currentSpotID
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            if suggestion.matches.isEmpty {
                Label("Photo includes location data, but no saved spot matched nearby.", systemImage: "location.magnifyingglass")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else if suggestion.matches.count == 1, let match = suggestion.matches.first {
                if activeSpotID == match.spotID {
                    Label("Photo location matches \(match.title).", systemImage: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundStyle(.appAccent)
                } else {
                    Text("Photo location is near \(match.title).")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Button {
                        onUseSpot(match.spotID)
                    } label: {
                        Label("Use \(match.title) for This Trip", systemImage: "mappin.circle")
                            .font(.footnote.weight(.medium))
                    }
                    .buttonStyle(.bordered)
                    .tint(.appAccent)
                }
            } else {
                Text("Photo location is near saved spots.")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: Spacing.sm) {
                        ForEach(suggestion.matches) { match in
                            Button {
                                onUseSpot(match.spotID)
                            } label: {
                                Text(match.title)
                                    .font(.footnote.weight(activeSpotID == match.spotID ? .semibold : .medium))
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 8)
                                    .frame(minHeight: 44)
                                    .background(
                                        activeSpotID == match.spotID ? Color.appAccent.opacity(0.16) : Color(.tertiarySystemFill),
                                        in: Capsule()
                                    )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
    }
}
