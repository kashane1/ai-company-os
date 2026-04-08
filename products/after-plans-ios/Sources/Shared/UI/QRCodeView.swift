import SwiftUI
import UIKit
import CoreImage.CIFilterBuiltins

struct QRCodeView: View {
    let payload: String
    var size: CGFloat = 200

    var body: some View {
        if let image = makeQRImage() {
            Image(uiImage: image)
                .interpolation(.none)
                .resizable()
                .scaledToFit()
                .frame(width: size, height: size)
        } else {
            Rectangle()
                .fill(.secondary.opacity(0.15))
                .frame(width: size, height: size)
                .overlay {
                    Label("QR unavailable", systemImage: "qrcode")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
        }
    }

    private func makeQRImage() -> UIImage? {
        let context = CIContext()
        let filter = CIFilter.qrCodeGenerator()
        filter.message = Data(payload.utf8)
        filter.correctionLevel = "M"
        guard let output = filter.outputImage else { return nil }
        let scaled = output.transformed(by: CGAffineTransform(scaleX: 10, y: 10))
        guard let cgImage = context.createCGImage(scaled, from: scaled.extent) else { return nil }
        return UIImage(cgImage: cgImage)
    }
}
