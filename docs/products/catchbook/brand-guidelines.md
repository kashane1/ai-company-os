# Brand Guidelines: Catchbook

Derived from the app icon (location pin with fish silhouette over water).
Created: 2026-04-08

---

## Color Palette

Extracted from the Catchbook app icon. The palette is a blue gradient from sky to deep ocean, reinforcing the water/fishing identity.

### Primary Colors

| Name | Hex | Usage |
|------|-----|-------|
| Sky Blue | `#B8E4F8` | Lightest tint — backgrounds, subtle highlights, empty states |
| Aqua Blue | `#6DCFF6` | Secondary accent — borders, tags, selected states, circle highlights |
| Ocean Blue | `#3BA3D9` | **Primary brand color** — buttons, navigation tint, links, active states |
| Deep Blue | `#1A7AB5` | Strong anchor — headers, tab bar, toolbar backgrounds |
| Navy Blue | `#0D5E94` | Darkest — text on light backgrounds, dark mode accents |

### Neutrals

| Name | Hex | Usage |
|------|-----|-------|
| White | `#FFFFFF` | Primary background, text on dark surfaces, fish silhouette |
| Soft Gray | `#C8D8E4` | Shadows, dividers, secondary text, disabled states |
| Dark Text | `#1A2A3A` | Primary text color (near-black with blue tint for brand consistency) |

### Semantic Colors

| Name | Hex | Usage |
|------|-----|-------|
| Success Green | `#34C759` | Catch logged, trip saved, personal best |
| Warning Amber | `#FF9F0A` | Skunked trip, missing data |
| Error Red | `#FF3B30` | Delete confirmation, validation errors |

---

## Typography Direction

- System fonts (San Francisco) to stay iOS-native
- Bold weight for headings and key stats (catch count, personal bests)
- Regular weight for body text and log entries
- Monospace for data/stats where alignment matters (measurements, coordinates)

---

## Icon Style

- The app icon is a **blue location pin** with a **white fish silhouette** over stylized **water waves**
- Small **sparkle/star** details suggest precision and clarity
- The location pin shape reinforces the "spots" concept — logging where you fish
- The gradient flows from light sky to deep water, top to bottom

---

## Marketing Content Style

### Slideshow Images (TikTok/IG)

- Use Ocean Blue (`#3BA3D9`) as the primary background or overlay color
- White text on blue backgrounds for maximum readability
- Fishing photography should feel serene, golden hour, private — not competitive or crowded
- Consistent bottom bar or watermark with "Catchbook" in white on Deep Blue

### Tone of Voice

- Private, confident, knowledgeable
- Speak like an experienced angler, not a marketer
- "Remember what worked" — not "Track your fish!"
- Calm authority, not hype

### Hashtag Base Set

TikTok: `#fishing #fishinglife #catchoftheday #bassfishing #fishingapp`
Instagram: `#fishingjournal #tightlines #catchandrelease #fishinglog #anglerlife`

---

## SwiftUI Color Implementation

```swift
// Catchbook Brand Colors
extension Color {
    static let catchbookSky = Color(hex: "B8E4F8")
    static let catchbookAqua = Color(hex: "6DCFF6")
    static let catchbookOcean = Color(hex: "3BA3D9")      // Primary
    static let catchbookDeep = Color(hex: "1A7AB5")
    static let catchbookNavy = Color(hex: "0D5E94")
    static let catchbookShadow = Color(hex: "C8D8E4")
    static let catchbookText = Color(hex: "1A2A3A")
}
```

These should be added to the Asset Catalog as named colors for both light and dark mode variants.

---

*This palette applies to both the iOS app UI and all marketing content (slideshows, screenshots, social media). Consistency across app and marketing is what separates a brand from a random Pinterest feed.*
