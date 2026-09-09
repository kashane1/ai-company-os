# Fishing Logbook iOS

This directory contains the first managed product source tree.

For a code review, start with [data models](Sources/Models/FishingModels.swift),
[services](Sources/Services/), and [tests](Tests/). The repository's
[iOS test script](../../scripts/test_ios.sh) generates the Xcode project and
runs the Catchbook scheme on an available iPhone simulator. It requires macOS,
Xcode, XcodeGen, and jq. Simulator builds are unsigned and require no Apple
development team or local signing configuration. This source tree and its local test script do not prove a release archive,
TestFlight upload, App Store submission, or public store release.

Current contents:

- `project.yml` for `xcodegen`
- SwiftUI app, unit-test, and UI-test targets
- local-first SwiftData models for the MVP loop
- core trip / catch / history flow scaffolding

The product remains private-by-default and intentionally narrow:

- no social features
- no community feed
- no release automation
- no CloudKit dependency for MVP

Near-term product order:

- current state: compressed logging, coherent spot recall, and one narrow privacy-safe catch share-card export
- build next: decision pass on pattern replay, seasonal or PB memory nudges, and optional catch-scan-lite prefilling
- later / not now: fish-ID-led positioning, social surfaces, widgets, Watch, broad analytics, and monetization implementation


## Tests

From the repository root, run:

```bash
./scripts/test_ios.sh --product catchbook
```

The script generates the project and selects an available iPhone simulator. Set
`IOS_SIMULATOR_ID` to select a particular installed simulator.

Verified 2026-09-09 with Xcode 26.6 and an iPhone 17 Pro simulator on iOS
26.5: **325 passed, 0 failed, 0 skipped** (323 unit tests and 2 UI tests).
The UI tests exercise the empty-state primary action at the largest Dynamic
Type size and the offline start-trip → save-catch loop. The result bundle is
written to `build/ios/catchbook.xcresult`.
