import SwiftUI
import UIKit
import XCTest
@testable import LifeClock

final class DesignTokenContrastTests: XCTestCase {
    func testSignedTextHasNormalTextContrastOnBothSurfaces() {
        for style in [UIUserInterfaceStyle.light, .dark] {
            let traits = UITraitCollection(userInterfaceStyle: style)
            for background in [UIColor.systemBackground, .secondarySystemBackground] {
                for foreground in [DesignTokens.Palette.positive, DesignTokens.Palette.negative] {
                    traits.performAsCurrent {
                        let fg = components(UIColor(foreground).resolvedColor(with: traits))
                        let bg = components(background.resolvedColor(with: traits))
                        let composed = zip(fg.rgb, bg.rgb).map { $0 * fg.alpha + $1 * (1 - fg.alpha) }
                        let first = luminance(composed)
                        let second = luminance(bg.rgb)
                        let ratio = (max(first, second) + 0.05) / (min(first, second) + 0.05)
                        XCTAssertGreaterThanOrEqual(ratio, 4.5, "Signed text contrast in \(style): \(ratio)")
                    }
                }
            }
        }
    }

    private func components(_ color: UIColor) -> (rgb: [Double], alpha: Double) {
        var red: CGFloat = 0, green: CGFloat = 0, blue: CGFloat = 0, alpha: CGFloat = 0
        XCTAssertTrue(color.getRed(&red, green: &green, blue: &blue, alpha: &alpha))
        return ([Double(red), Double(green), Double(blue)], Double(alpha))
    }

    private func luminance(_ values: [Double]) -> Double {
        let linear = values.map { $0 <= 0.04045 ? $0 / 12.92 : pow(($0 + 0.055) / 1.055, 2.4) }
        return zip(linear, [0.2126, 0.7152, 0.0722]).map(*).reduce(0, +)
    }
}
