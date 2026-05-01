---
date: 2026-05-01
topic: history-deferred-followups
origin_pr: https://github.com/kashane1/ai-company-os/pull/18
---

# History/Wrap-Ups/Overrides — Deferred Follow-Ups

## What We're Building

A consolidated cleanup + hardening pass on the History feature shipped in PR #18. The base feature works end-to-end — Yesterday Wrap-Up sheet, Pro override flow, 90-day import, Pro/free blur — but the multi-agent review of the last commit surfaced a list of items that were intentionally deferred so the user-visible feature could ship first.

This brainstorm consolidates those items into a coherent next slice. Each item builds on the now-functional foundation rather than blocking it.

## Why This Approach

We considered shipping each follow-up as its own PR (one per item), but most of them touch the same files (`HistoryView`, `OverrideService`, `SnapshotOverrideMap`, `LifeClockStore`) and would create constant rebase churn. Bundling them into one well-scoped follow-up PR is faster end-to-end and easier to review as a coherent quality pass.

We also considered deferring further — letting these sit until TestFlight feedback proves which ones actually matter. We're rejecting that because three items (the isPro engine gate, the downgrade banner, the HK 1-query-per-metric optimization) are correctness/performance bugs the review explicitly flagged, and the cleanup pass has near-zero risk if it lands as a single bundled change.

## Key Decisions

### Functional / Correctness

- **isPro engine-layer gate for overrides** — when a user downgrades from Pro to Free, the plan said "overrides remain stored but engine ignores them." The current code writes the override through to the raw field, so the engine sees the corrected value regardless of `isPro`. We need an isPro check at either `OverrideService.applyOverride` (refuse-write while !isPro) or at the engine read site (read raw if !isPro). Engine-read-site approach is cleaner: existing overrides remain stored, just become inert.
- **Pro→Free downgrade banner** — one-time tone-aware notice when `isPro` flips from true to false: "Your adjustments are paused. Re-subscribe to keep using corrected values." Requires tracking the prior `isPro` state across launches (a `lastSeenIsPro: Bool` on `UserProfile`).

### Performance

- **`HKStatisticsCollectionQuery` for 90-day import** — collapse ~540 per-day HK queries into 4 queries (one per metric) over the full 90-day window. Wall-clock target: <3s, vs. current 45-120s. This is a `LiveHealthKitService` refactor; the existing `HistoricalImportCoordinator` code stays the same.
- **`LazyVStack` + single blur overlay in HistoryView** — current `ScrollView { ForEach }` builds all 83 blurred rows up front; each row carries `.ultraThinMaterial.opacity(0.4)` overlay. On A13/A14 devices this drops frames during scroll. Switch to `LazyVStack`; render one blurred overlay covering the locked region rather than 83 individual blurred rows.
- **`@Query` for HistoryView snapshots** — current code calls `store.recentSnapshots(limit: 90)` in body, which re-fetches on every observed mutation. `@Query` maintains an incremental observer.
- **Decoded override map cache** — `effectiveValue(for:)` decodes JSON on every access. `DayDetailView`'s metric row calls it 3x per field × 4 fields = 12 decodes per render; History list calls `hasOverrides` once per row × 90 rows = 90 decodes. Cache the decoded map keyed on `overridesData.hashValue`.
- **Debounce `recomputeYesterdayDelta`** — 4 rapid field edits = 4 redundant recomputes for the same yesterday. 300ms trailing debounce.

### Simplicity

- **Collapse 5 field-switch tables into one `FieldSpec`** — `OverrideService.isValid`, `OverrideService.assignRawValue`, `OverrideSheet.prefill`, `OverrideSheet.keyboardType`, `OverrideSheet.bounds`, `DayDetailView.format`, `SnapshotOverrideAccess.rawValue(for:)` all switch on `Field`. One `FieldSpec` (keyboard, bounds, formatter, raw-getter, raw-setter) on the Field enum eliminates the "add a field, edit 6 sites" footgun.
- **Shared `PaywallTeaser` component** — `HistoryView.paywallTeaser` (weekly) and `HistoryView.historyPaywallTeaser` (90-day) are near-duplicates. One `PaywallTeaser(title:body:cta:onTap:)` view.
- **Extract `DayHistoryRow` to its own file** — currently a private struct at the bottom of `HistoryView.swift`. Parallel to `DayDetailView.swift`.
- **Inline `SnapshotOverrideAccess` into the model file** — 52 lines of trivial accessors don't need a separate file.
- **Extract `OverrideService` transactional helper** — `applyOverride` and `revertOverride` share the same encode-mutate-save-rollback shape. One private helper.

### Tests

- **`ClockHandView` snapshot tests** — positive / negative / zero / reduce-motion variants. Requires `swift-snapshot-testing` SPM dep (or hand-rolled image-equality with a tolerance).
- **`OverrideService` re-edit-after-revert test** — the data-integrity reviewer flagged this should be pinned. Spec: revert clears originalHealthKitValuesData; next applyOverride re-captures from current raw.
- **UITests for wrap-up flow + tab rename** — cover the first-open trigger, single-show-per-day, dismiss path, History tab title.

## Animation Direction

No new animation work in this slice — the existing `ClockHandView` is unchanged. The snapshot tests verify behavior across the 4 variants but don't add new visual behavior.

## Non-Goals For This Slice

- Editing the 90-day import window (stays at 90 for V1).
- Adding new overridable fields beyond the existing 4 (steps, sleep, exercise, active energy).
- A migration to a SwiftData V2 schema (the additive optionals shipped in PR #18 don't need versioning).
- Replacing the current `JSONCoder` round-trip for override storage (works fine; the cache solves the perf concern).
- Enriching the long-absence card beyond the simple supportive heading + body shipped in PR #18.

## Next Steps

→ `/workflows:plan` for implementation planning across the functional, performance, simplicity, and test buckets.
