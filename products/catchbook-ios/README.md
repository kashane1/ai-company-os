# Fishing Logbook iOS

This directory contains the first managed product source tree.

For a code review, start with [data models](Sources/Models/FishingModels.swift),
[services](Sources/Services/), and [tests](Tests/). The repository's
[iOS test script](../../scripts/test_ios.sh) generates the Xcode project and
runs the Catchbook scheme on an available iPhone simulator. It requires macOS,
Xcode, XcodeGen, and jq. This source tree is not proof of a public store release.

Current contents:

- `project.yml` for `xcodegen`
- a single SwiftUI iOS app target
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
