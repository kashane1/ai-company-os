# Fishing Logbook iOS

This directory contains the first managed product source tree.

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

- build now: one-handed logging, coherent spot recall, compact Spot DNA summary, and privacy-safe share-card export
- build next: pattern replay, seasonal or PB memory nudges, and optional catch-scan-lite prefilling
- later / not now: fish-ID-led positioning, social surfaces, widgets, Watch, broad analytics, and monetization implementation
