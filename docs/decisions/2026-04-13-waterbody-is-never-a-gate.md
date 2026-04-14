---
title: Waterbody is never a gate
date: 2026-04-13
status: accepted
supersedes_partial: docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md
related_plan: docs/plans/2026-04-13-refactor-catchbook-optional-waterbody-plan.md
---

# ADR: Waterbody is never a gate

## Context

The 2026-04-11 Catchbook location-model brainstorm established a layered location model where **Waterbody** is the "canonical place anchor" — the representative coordinate for a named body of water. The brainstorm also established the broader principle that **"Catchbook should do the work first"** — aggressively prefill likely values instead of asking the user to build every record from scratch.

The partial implementation in commit `194078d` (feat(catchbook): make spots map-first with crosshair pin placement and waterbody auto-detection) added 3-layer waterbody auto-detection to `NewSpotForm`, but kept the existing empty-state gate ("No waterbodies yet — add a waterbody first") in front of the form. The result was a chicken-and-egg: the auto-detect couldn't run until the user manually created a waterbody first, which defeated the purpose.

On fresh install, users also hit the same wall in `TripStartSheet` ("Add your first water — create a waterbody to start logging trips and catches") and in the trip editor (`TripEditingLogic.canSave` required a non-nil waterbody ID). The brainstorm did not explicitly forbid these gates, but they are incompatible with "do the work first" applied to someone who has never used the app before.

## Decision

**Waterbody is an optional tag at every entry point across Catchbook. It is never a precondition for creating a spot, starting a trip, editing a trip, logging a catch, or surfacing any post-trip follow-up.**

Specifically:

1. `Spot` and `Trip` continue to hold an optional relationship to `Waterbody` (models already allow nil — no schema change).
2. No form may block save / submit on `waterbody == nil` or `waterbodies.isEmpty`. `canSave` functions across `SpotFormLogic`, `TripEditingLogic`, and any future form must ignore waterbody state entirely.
3. Waterbody auto-detection (via `WaterbodyAutoDetectionService`) runs silently from a coordinate when the app has one. On hit, the detected waterbody is attached to the record being saved. On miss, the record saves with `waterbody == nil` and that is a fully valid state.
4. Post-trip follow-ups (e.g. `LogFeatureLogic.shouldOfferCreateSpot`) use resolvable coordinates, not waterbody presence, as their gating condition.
5. Trips map aggregation (`TripHistoryLogic.waterbodySummaries`) must surface nil-waterbody trips in a "General area" synthetic cluster — they cannot be silently dropped from the map.
6. Pickers that reference waterbody use `"None"` as the first option (with a `Divider`), matching Apple HIG conventions (Reminders "No List", Notes folder picker).
7. When auto-detection populates the picker, a quiet `.caption2` "Detected from your location" row appears under the picker. Users can clear it by picking anything else. No provenance labels ("inferred", "75% confident", etc.).

## What this changes relative to the brainstorm

The brainstorm's "Waterbody should have one canonical coordinate" rule still holds **when** a waterbody is attached. The canonical-anchor semantics are untouched: if a `Waterbody` row exists and has lat/lon, it continues to drive map anchoring, weather fallback, and future water-level summaries.

What this ADR changes is the **mandatory-ness**: the brainstorm implicitly treated waterbody as a required anchor for every record. This ADR says waterbody is always welcome but never required. A spot or trip with no waterbody is a first-class record, not a degenerate one.

Applied to the brainstorm's specific decisions:

- "Waterbody should have one canonical coordinate" → still true **when present**.
- "Spot should be user-owned, user-named, and optionally pin-drop based" → unchanged.
- "Trip should retain its own observed location for conditions" → unchanged.
- "The app should distinguish exact, inferred, and inherited coordinates" → unchanged, except that the inference chain must not require a waterbody to start.
- "Known waterbody selection should be supported when possible" → unchanged.
- "Map behavior should prefer user memory over raw GPS noise" → still true; extended to include "general area" fallbacks for nil-waterbody records so the map is not misleading.

## Consequences

**Positive:**

- Fresh-install users can log a spot and start a trip with zero waterbody interaction.
- `NewSpotForm` and `TripStartSheet` auto-detection runs the first time a user drops a pin or starts a trip near a named water — because the form is no longer short-circuited on `waterbodies.isEmpty`.
- The "waterbody is a gate" anti-pattern is ruled out by precedent for future features. A code comment in `products/catchbook-ios/CLAUDE.md` (or root `CLAUDE.md`) will point to this ADR.

**Negative / accepted trade-offs:**

- Some records will exist with `waterbody == nil` forever, even when a real waterbody could have been inferred later. Downstream features that want "all records for Lake Tahoe" will need to handle coordinate-based fallback (already true for trip map visualization; will need similar treatment for future insights).
- The Trips map requires a synthetic "General area" cluster to avoid dropping nil-waterbody trips. This adds one rendering code path that wouldn't exist in a waterbody-required world.
- Duplicate waterbody rows from case variants ("Lake Tahoe" vs "lake tahoe") are deduped by `WaterbodyAutoDetectionService.findOrCreate`'s case-insensitive name match. More exotic dedupe (proximity, fuzzy matching) is deferred; if users report phantom waterbodies, revisit.

## Implementation reference

See `docs/plans/2026-04-13-refactor-catchbook-optional-waterbody-plan.md` for the full implementation plan, phasing, and acceptance criteria.
