# App Store Metadata Draft: Catchbook

Field-by-field draft for App Store Connect. Each field maps directly to an ASC input. Copy into ASC when the App Store lane begins.

Modeled on `docs/products/after-plans/APP_STORE_METADATA_DRAFT.md`.

Last updated: 2026-04-09
Status: FINALIZED — all fields locked. URLs live. WeatherKit added to description.

---

## App Information

| Field | Value | Status |
|-------|-------|--------|
| App name | **Catchbook** | ready |
| Subtitle | **Your Private Fishing Journal** (29 chars) | ready |
| Primary category | Sports | ready |
| Secondary category | Reference | ready |
| Content rights | Does not contain third-party content | ready |
| Age rating | 4+ (no objectionable content, no user-generated content in MVP) | ready |

## Pricing

| Field | Value | Status |
|-------|-------|--------|
| Price | **Free** | ready |
| In-app purchases | None in v1 | ready |

## Version Information

### Promotional Text (170 chars, editable without review)

FINAL:
> Your private fishing journal, offline and on-device. No accounts. No cloud. No tracking. Just honest catch data and weather conditions — all yours.

(148 chars)

Status: ready

### Description

FINAL:

Catchbook is a private fishing logbook for anglers who fish the same waters and want to remember what works.

**Log catches in seconds**

Start a trip, add catches as you go, and end your session. Every catch records species, size, lure, and the conditions at the time — all captured automatically.

**Live weather via Apple WeatherKit**

Each trip captures real-time temperature, wind speed and direction, cloud cover, and precipitation — all from Apple's WeatherKit, included free with no third-party services. Over time, weather patterns emerge that help you fish smarter. Works gracefully offline too — weather enriches your log when available, and core logging never depends on it.

**Keep your spots private**

Your spots are yours. Every location stays on your device. There is no community feed, no crowdsourced map, and no way for other anglers to see where you fish. When you share a catch, the spot stays hidden by default.

**See what worked last time**

Before your next trip, check what has worked at a specific spot — best time of day, top lure, seasonal patterns, and catch rates. Every insight is based on your own data, not crowdsourced averages.

**Review spot-by-spot history**

Every spot accumulates its own performance story. See trip history, catch totals, personal bests, and condition trends — all organized by the waters you actually fish.

**Share a win without exposing the spot**

Export a privacy-safe share card showing your catch — species, size, photo — without revealing the GPS coordinates or spot name. Share the fish, keep the spot.

**Why anglers choose Catchbook**

No accounts. No cloud. No tracking. No ads. No subscriptions. Just a straightforward fishing journal that respects your privacy. Perfect for bass anglers tracking seasonal patterns, saltwater fishermen logging tides and conditions, fly fishers documenting river data, or kayak anglers mapping productive spots.

Download Catchbook and own your fishing data.

Status: ready (under 4000 chars, WeatherKit featured, keyword-rich)

### What's New (for first version)

FINAL:
> Catchbook 1.0 — Your Private Fishing Journal. Log catches, track live weather conditions via Apple WeatherKit, review spot history, and see what works. All data stays on your device. No accounts, no cloud, no tracking.

### Keywords (100 chars max, comma-separated)

FINAL:
> fishing logbook,catch log,fishing journal,bass fishing,trout fishing,saltwater,offline,fish tracker

(99 characters)

**Keyword rationale:**
- "fishing logbook" — exact-match for the app category, high intent
- "catch log" — high volume short phrase
- "fishing journal" — primary alternative search term
- "bass fishing" / "trout fishing" / "saltwater" — species-specific high-volume terms
- "offline" — uncontested differentiator, no major competitor targets this
- "fish tracker" — broad category term
- Avoids: words already in title ("Catchbook") or subtitle ("Private", "Fishing", "Journal", "Your")
- Does NOT include: "app" (Apple ignores it), "free" (indicated by price)

Status: ready (keyword-researched 2026-04-09)

### Subtitle Rationale

Chose "Your Private Fishing Journal" (29 chars) over alternatives:
- "Private Catch & Spot Log" (24 chars) — good but less keyword-rich; "journal" has higher search volume than "log"
- "Log Trips, Track Catches" (24 chars) — action-oriented but misses the privacy differentiator
- "Catch Tracking, No Cloud" (24 chars) — too negative/technical for first impression

"Your Private Fishing Journal" immediately differentiates against social/cloud competitors (Fishbrain, Pro Angler) and includes "Fishing Journal" as a high-volume keyword phrase.

## URLs

| Field | Value | Status |
|-------|-------|--------|
| Privacy policy URL | https://kashane1.github.io/catchbook-legal/privacy-policy.html | ready (live) |
| Support URL | https://kashane1.github.io/catchbook-legal/support.html | ready (live) |
| Marketing URL | — (later) | deferred |

## Privacy Details (App Privacy Nutrition Labels)

| Category | Data collected | Linked to identity | Used for tracking |
|----------|---------------|-------------------|-------------------|
| Location | Precise location (GPS coordinates for spots) | No | No |
| Photos | Photos (catch photos stored locally) | No | No |

Data not collected: no analytics, no crash reports, no identifiers, no usage data, no purchases, no contacts, no browsing history.

All data is stored on-device only. No data leaves the device unless the user explicitly exports a backup or share card. Weather data is fetched from Apple WeatherKit — no third-party weather APIs — and stored locally.

Status: ready (strong privacy story)

## App Review Information

### Review Notes

FINAL:
> This app stores all data locally on-device using SwiftData. There are no accounts, no login, and no server communication. Location access is used only to tag fishing spots and is stored locally. Photo library access is used to attach catch photos. Weather data is fetched from Apple's WeatherKit and stored locally — no third-party services involved. The app works fully offline (weather enrichment is optional). To test: create a waterbody and spot, start a trip, add a catch, and end the trip. Then visit the Spots tab to see accumulated history and insights.

### Demo Account

Not applicable — no accounts, no login, no server.

## Pre-Submission Checklist Reference

See `submission-checklist.md` in this directory for the full structured checklist.

## Open Decisions for Human

1. ~~**App name**~~ — decided: **Catchbook** (2026-04-08)
2. ~~**Subtitle**~~ — decided: **Your Private Fishing Journal** (2026-04-09, keyword-researched)
3. ~~**Pricing**~~ — decided: **Free** (2026-04-09)
4. ~~**Privacy policy URL**~~ — **https://kashane1.github.io/catchbook-legal/privacy-policy.html** (live, deployed 2026-04-09)
5. ~~**Support URL**~~ — **https://kashane1.github.io/catchbook-legal/support.html** (live, deployed 2026-04-09)
6. **Release type** — recommended: manual release for v1.0 (review before going live) [needs: Kashane to confirm]
