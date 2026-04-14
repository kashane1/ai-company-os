---
title: "iOS App Runs in iPhone Compatibility Mode on iPad Because TARGETED_DEVICE_FAMILY = 1"
category: integration-issues
date: 2026-04-14
tags:
  - catchbook
  - ios
  - ipad
  - xcode
  - pbxproj
  - targeted-device-family
  - compatibility-mode
  - layout
  - device-support
  - build-settings
module: Catchbook.xcodeproj
symptom: "On iPad, the entire app renders in a small iPhone-shaped window pinned to the upper-left of the screen with the rest of the iPad canvas showing wallpaper. The tab bar and all content appear at iPhone aspect ratio, not scaled up, not centered. The simulator and real iPads both reproduce it. iPhone looks fine."
root_cause: "The main app target had `TARGETED_DEVICE_FAMILY = 1` (iPhone only) in the Debug and Release build configurations of `project.pbxproj`. iOS runs iPhone-only apps on iPad in a legacy compatibility mode that renders the app at native iPhone pixel dimensions in the upper-left corner of the screen instead of scaling or using the full canvas. The fix is a two-character change: set it to `\"1,2\"` so the same SwiftUI layout targets both device families."
---

## Problem

Opening the Catchbook app on an iPad Pro 11" simulator produced a broken-looking layout: the Home title, the "Start a Trip" card, and the tab bar all sat in a small iPhone-shaped box pinned to the upper-left of the screen. The rest of the iPad canvas showed the home-screen wallpaper peeking through — not black, not scaled, not centered. It looked like a rendering bug.

Screenshot of the symptom: the app's `NavigationStack` is fully rendered, fonts and spacing are correct *within* its window, the tab bar is visible and tinted, but the whole thing only fills maybe 40% of the iPad screen's width and 50% of its height, and it's anchored to the top-left.

iPhone simulators rendered the same app with no layout problems at all. The SwiftUI code was identical. The `Info.plist` had no orientation lock, no `UIRequiresFullScreen` key, no scene-delegate shenanigans. Nothing in the app code mentioned device class.

## Root Cause

This is not a layout bug. It's iPad's compatibility mode for iPhone-only apps.

When an iOS app declares itself as iPhone-only via `TARGETED_DEVICE_FAMILY = 1`, iPad runs it in a legacy compatibility mode that renders the app at native iPhone pixel dimensions in a fixed window — not scaled up, not centered, not responsive. That's exactly what the user saw. The cramped top-left window is the signature symptom of iPhone-only compatibility mode on iPad, and once you know it, you can never unsee it.

In `products/catchbook-ios/Catchbook.xcodeproj/project.pbxproj`, both the Debug and Release configurations of the main app target had:

```
PRODUCT_BUNDLE_IDENTIFIER = io.aicompanyos.products.fishinglogbook;
PRODUCT_NAME = Catchbook;
SDKROOT = iphoneos;
SUPPORTS_MACCATALYST = NO;
TARGETED_DEVICE_FAMILY = 1;
```

Meanwhile the **test** target had `TARGETED_DEVICE_FAMILY = "1,2"` — which is why running the test suite on an iPad simulator worked and nobody noticed the app target was different.

Xcode's `TARGETED_DEVICE_FAMILY` takes a comma-separated list inside quotes when there's more than one value:

- `1` = iPhone
- `2` = iPad
- `"1,2"` = universal
- `"1,2,7"` = universal + Apple Vision

There's no layout work, no SwiftUI restructure, no new entitlements, and no asset-catalog changes needed to go from iPhone-only to universal for a SwiftUI app that already uses `NavigationStack` / `TabView` — those views adapt to iPad automatically. The only thing stopping the app from filling an iPad screen was this one build setting.

## Investigation Steps That Didn't Help

Worth noting because they're tempting and they waste time:

1. **Inspected `Info.plist`.** Looked for `UIRequiresFullScreen`, `UISupportedInterfaceOrientations~ipad`, scene configuration, window tint, safe-area overrides. Clean. Irrelevant — compatibility mode is decided before the plist is consulted.
2. **Searched SwiftUI code for iPhone-specific modifiers.** `.frame()`, `.navigationSplitViewStyle()`, hardcoded widths, `UIDevice.current.userInterfaceIdiom` checks. None existed. Irrelevant — the SwiftUI code never runs at iPad dimensions in compatibility mode.
3. **Assumed it was `NavigationStack` not expanding on iPad.** It would be reasonable to suspect `NavigationSplitView` was needed, or that `TabView` on iPad needed different styling. Irrelevant — at iPad dimensions `NavigationStack` and `TabView` adapt correctly out of the box. The app was never being asked to render at iPad dimensions.

The diagnostic insight is: **if the content looks correct but the window is the wrong size and pinned to a corner, suspect compatibility mode first.** That's what `TARGETED_DEVICE_FAMILY = 1` on iPad looks like.

## Working Solution

Edit `products/catchbook-ios/Catchbook.xcodeproj/project.pbxproj` and change both occurrences of `TARGETED_DEVICE_FAMILY = 1;` (one in the Debug configuration, one in Release) to `TARGETED_DEVICE_FAMILY = "1,2";`.

The quotes are required because the value contains a comma — Xcode's pbxproj format treats bare values as unquoted tokens and anything with special characters must be string-quoted.

A scripted version of the change (safe because only the main app target has this value — the tests target already uses `"1,2"`):

```bash
python3 << 'PY'
import pathlib
p = pathlib.Path('products/catchbook-ios/Catchbook.xcodeproj/project.pbxproj')
src = p.read_text()
new = src.replace('TARGETED_DEVICE_FAMILY = 1;', 'TARGETED_DEVICE_FAMILY = "1,2";')
assert src.count('TARGETED_DEVICE_FAMILY = 1;') == 2, "expected 2 iPhone-only entries"
p.write_text(new)
PY
```

Then verify the main target's build settings:

```bash
grep -B1 "TARGETED_DEVICE_FAMILY" products/catchbook-ios/Catchbook.xcodeproj/project.pbxproj
```

Every entry should read `TARGETED_DEVICE_FAMILY = "1,2";`.

Build and rerun on an iPad simulator:

```bash
cd products/catchbook-ios
xcodebuild -project Catchbook.xcodeproj -scheme Catchbook \
  -destination 'platform=iOS Simulator,name=iPad Pro 11-inch,OS=26.4' build
```

The app should now fill the full iPad canvas. `NavigationStack` centers its content with normal iPad padding, the `TabView` tab bar spans the width of the screen, and safe-area insets work correctly in landscape.

This landed as commit `30b898c` on `main`:

```
fix(catchbook): enable iPad support by broadening TARGETED_DEVICE_FAMILY
```

## Prevention

**Every new Apple-platform app should start universal.** There is no good reason for a new SwiftUI app to ship as iPhone-only in 2026 unless it uses an iPhone-exclusive hardware feature (and even then, `"1,2"` + runtime capability checks is the better pattern). Leaving the default as `1` means the first time anyone opens the app on an iPad, it looks broken — and the diagnostic path is non-obvious because the SwiftUI code appears innocent.

Rules of thumb:

1. **When creating a new iOS app target in Xcode**, check "iPad" in the destinations list before hitting Create. The default value for `TARGETED_DEVICE_FAMILY` is then `"1,2"`.
2. **When reviewing a PR that touches `project.pbxproj`**, grep for `TARGETED_DEVICE_FAMILY` and verify it's `"1,2"` (or whatever your product requires). This setting is easy to regress accidentally because Xcode sometimes rewrites build settings on save.
3. **Test every PR on at least one iPad simulator destination** before merging. The test suite ran fine on iPad here because the tests target was already `"1,2"` — but the app target's symptom only shows up at actual app launch on an iPad. An iPad smoke test would have caught this on the first commit.
4. **If you ever see an iOS app rendering in a small fixed window pinned to a corner of an iPad**, the diagnosis is almost always `TARGETED_DEVICE_FAMILY = 1`. Skip the SwiftUI layout investigation and go straight to `project.pbxproj`.

### Diagnostic checklist

When an iOS app looks wrong on iPad:

- [ ] Is the window the correct shape and size? If **no** → compatibility mode, check `TARGETED_DEVICE_FAMILY`.
- [ ] Is the window correct but content is laid out wrong inside it? Then it's a SwiftUI layout issue — investigate `NavigationStack` vs `NavigationSplitView`, regular size class handling, orientation constraints.
- [ ] Is the window fullscreen but jet-black bars appear? Check `Info.plist` orientation keys and `UIRequiresFullScreen`.

Only the first case is `TARGETED_DEVICE_FAMILY`. The other two are real layout bugs.

## Cross-References

- Commit `30b898c` — the fix
- Commit `b7acfa3` — same session, "finish More tab with CSV export and fishing stats" (the user spotted this iPad bug while testing the completed More tab flow, which is how it got found at all)
- [`docs/solutions/integration-issues/swiftdata-mandatory-attribute-migration-landmine.md`](./swiftdata-mandatory-attribute-migration-landmine.md) — unrelated content, but another "the build setting / model declaration looks innocent and the symptom looks like an unrelated bug" class of problem in the same project. Both reinforce the same lesson: **Catchbook build-and-model configuration errors present as feature bugs, not as build errors.**
- Apple docs on `TARGETED_DEVICE_FAMILY`: the canonical reference is under Xcode Build Settings Reference → Deployment → "Targeted Device Families". Accepts `1` (iPhone), `2` (iPad), `7` (Apple Vision), as comma-separated values inside quotes when combining.
