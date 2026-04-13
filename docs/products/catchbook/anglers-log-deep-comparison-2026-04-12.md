# Anglers' Log Deep Comparison: Lessons for Catchbook

**Date:** April 12, 2026
**Purpose:** Single-app deep dive into Anglers' Log — the closest-in-spirit competitor. Extract implementation patterns, UX ideas, and feature architecture that Catchbook can learn from. This document covers ONLY ideas not already in the previous competitive deep dive.

---

## Why Anglers' Log Matters

Anglers' Log is the indie gold standard for fishing journal apps. It's built by one developer (Cohen Adair), open source on GitHub (GPL-3.0), and has 267 ratings at 4.7/5 with users saying things like they'd happily pay $50/year for it. It shares Catchbook's core philosophy: no ads, no bloat, privacy-first, local data. But it has 72 releases and years of refinement behind it. The question isn't "can we beat it?" — it's "what did they figure out that we haven't yet?"

**Tech stack:** Flutter/Dart, Protobuf data model, Mapbox maps, Firebase auth, Google Drive backup, Visual Crossing Weather API, WorldTides.info API.

---

## 1. GPS Trail Tracking — How They Built It

This is the feature you specifically called out. Here's exactly how Anglers' Log implements it:

### Architecture

```
LocationMonitor (geolocator package)
  └─ streams LocationPoint { lat, lng, heading }
       └─ GpsTrailManager
            └─ creates GpsTrail { id, startTime, endTime, bodyOfWaterId }
                 └─ appends GpsTrailPoint { timestamp, lat, lng, heading }
```

### Key Implementation Details

- **10-meter distance filter** — only records a new point when the user has moved at least 10 meters from the last recorded point. This balances detail vs. battery drain.
- **User-configurable minimum distance** — users can adjust the sensitivity in settings (`minGpsTrailDistance` preference). Some want breadcrumb-level detail, others want just the general route.
- **Background location enabled** — iOS shows the blue location indicator bar. The app registers for background location updates so tracking continues when the phone is in a pocket or tackle box.
- **Heading tracking** — each point records which direction the user was facing, not just position. This could be useful for showing drift direction on a boat.
- **One active trail at a time** — enforced in code. You can't accidentally start two trails.
- **Unfinished trail recovery** — if the app crashes or is force-quit during tracking, it restores the unfinished trail on next launch. No data is lost.
- **Always allow stopping** — even if Pro subscription expires, the user can always stop an active trail. This is a safety detail (you don't want someone unable to stop GPS tracking because their subscription lapsed).
- **Multiple trails per trip** — a trip can link to multiple GPS trails via `gpsTrailIds`. This covers scenarios like driving between fishing spots, or fishing in the morning and afternoon at different locations.

### How It Looks on the Map

The GPS trail renders as a series of connected blue dots on the Mapbox satellite map. Catch markers (pins) appear along the trail at the locations where fish were caught. The trail detail page shows:
- The full trail path zoomed to fit the bounds
- Body of water name
- Start/end timestamps and elapsed time
- Active status indicator (pulsing dot if still recording)
- Trip association

### What This Means for Catchbook

If you want GPS trail tracking, the key decisions are:
- **Use Core Location's `CLLocationManager` with distance filter** — the Swift equivalent of what they're doing. Set `distanceFilter` to ~10 meters, `allowsBackgroundLocationUpdates = true`.
- **Store trail points as a lightweight array** — each point is just (timestamp, lat, lng, heading). Even a full day of kayak fishing might produce 500-1000 points.
- **Render on MapKit** — use `MKPolyline` overlay to draw the trail on the map. MapKit handles this natively and efficiently.
- **Battery warning** — Anglers' Log shows the iOS background location indicator. Users should be warned that GPS tracking increases battery drain. Consider a "check in every N minutes" mode as a battery-friendly alternative.
- **Make it Pro-only** — Anglers' Log gates this behind the subscription. It's a legitimate premium feature given the battery/complexity cost.

---

## 2. Map Interface — What Makes Theirs Great

### What They Do Differently from Catchbook's Current Map

**Mapbox with style switching:**
They use Mapbox (not Apple MapKit) with three map styles: light, dark, and satellite. The satellite view is particularly important for anglers — you can see actual water features, tree lines, shoreline contours, and structure. Apple MapKit also supports satellite, but Catchbook doesn't currently offer the toggle.

**Full-screen map as a primary tab:**
The Map is the FIRST tab in their bottom bar. It's not buried inside a Spots section — it's a top-level navigation destination. This signals that the map is a core part of the experience, not a secondary feature.

**Spot pins with visual hierarchy:**
Three pin types with distinct visual treatment:
- Active/selected pin (highlighted color)
- Inactive pins (muted color)
- Direction arrow (for GPS trail heading)

This makes it easy to see where you are, where your spots are, and which one you're looking at.

**Drop-pin-to-create workflow:**
Users create new fishing spots by dropping a pin directly on the map. Long-press → pin drops → name it → save. This is more intuitive than Catchbook's current flow which starts from a form and adds location to it.

**Spot detail overlay on map:**
When you tap a pin, you see the spot details (name, body of water, catch count, last visit) without leaving the map view. The map stays visible behind the overlay.

**GPS trail controls on the map:**
Start/stop GPS tracking buttons are directly on the map interface. The trail renders in real-time on the same map as your fishing spots. This creates a unified spatial view: "here's where I've been, here's where I've fished before."

### What Catchbook Should Steal

1. **Satellite map toggle** — add `.satellite` and `.hybrid` `MKMapType` options to `CatchbookMapView`. One button, three states (standard/satellite/hybrid). Anglers want to see actual water.

2. **Promote map to a primary tab or prominent position** — if the map is useful, don't hide it inside Spots. Consider making the Spots tab map-first with a list toggle, rather than list-first with a map buried.

3. **Drop-pin-to-create spots** — Catchbook already has pin-first spot creation, but make sure it feels as effortless as a long-press on the map → name → save. The fewer steps between "I'm standing here and want to save this spot" and "done," the better.

4. **Catch pins on the map** — show where individual catches happened on the map, not just where spots are. When viewing a trip, overlay catch positions on the map. This creates a visual story of the trip.

---

## 3. The "Configurable Tracking" Pattern

This is one of Anglers' Log's most praised design decisions, and Catchbook doesn't do it.

### How It Works

In Settings, users toggle which field categories they want to track:
- Anglers (for multi-person trips)
- Baits
- Fishing Spots
- Images
- Species
- Length
- Weight
- Methods
- Seasons
- Tides
- Time periods (dawn/morning/afternoon/etc.)
- Water clarity
- Gear
- Moon phases

**When you turn off a category, it disappears from the entire app.** The catch form hides that field, the stats don't reference it, the filters remove it. The app becomes exactly as simple or as complex as you want.

### Why This Matters

Users are split into two camps:
- **Minimalists** who just want species + photo + location
- **Data nerds** who want 20 fields per catch

Anglers' Log serves both without compromise. A beginner sees a clean, 3-field catch form. A tournament angler sees a 15-field form with gear details and water depth.

### What Catchbook Should Consider

Catchbook already has `showingOptionalFields` toggle in the catch logging form, but it's per-session, not per-field. Consider a settings-level approach:
- Let users choose which optional fields they care about
- Hide unchecked fields from the logging form, the trip detail, and stats
- Show a "you can enable more fields in Settings" hint for discovery
- Default to a minimal set (species, photo, weight, length, lure) with everything else off

This is a "Build Next" level feature, not a launch blocker. But it's what makes users say the app is "simple with unlimited customability."

---

## 4. The Bait Variant System

Anglers' Log has a surprisingly deep bait/lure tracking system that Catchbook doesn't.

### How It Works

```
Bait
  ├─ name: "Senko"
  ├─ category: "Soft Plastics" (FK to BaitCategory)
  ├─ type: artificial | real | live
  ├─ image
  └─ variants:
       ├─ Variant 1: { color: "Green Pumpkin", size: "5 inch", modelNumber: "9S-10" }
       ├─ Variant 2: { color: "Watermelon", size: "4 inch" }
       └─ Variant 3: { color: "Black/Blue Flake", size: "5 inch", minDiveDepth: 0, maxDiveDepth: 3 }
```

When logging a catch, users pick a bait AND a variant. Stats then break down by variant — "Green Pumpkin Senko caught 12 fish, Watermelon caught 3."

### What Catchbook Has

A single `lureOrBait: String` field. Free text. No variant tracking, no categorization, no image attachment.

### What Catchbook Could Do

This doesn't need to be as complex as Anglers' Log's system. A middle ground:
- Keep the simple text field for quick logging
- Add a "saved baits" library that grows as the user logs (auto-suggest from previous entries)
- Allow a color/variant suffix when saving ("Senko - Green Pumpkin" vs. "Senko - Watermelon")
- Stats group by the full lure string, which effectively creates variant-level analysis

This gives 80% of the benefit with 20% of the complexity. Save the full bait entity system for a future pass.

---

## 5. The Gear Tracking System

### What Anglers' Log Tracks

```
Gear
  ├─ name: "Bass Setup"
  ├─ rodMakeModel, rodSerialNumber, rodLength
  ├─ rodAction: x_fast | fast | moderate_fast | moderate | slow
  ├─ rodPower: ultralight | light | medium_light | medium | medium_heavy | heavy | xx_heavy | xxx_heavy
  ├─ reelMakeModel, reelSerialNumber, reelSize
  ├─ lineMakeModel, lineColor, lineRating
  ├─ leaderLength, leaderRating
  ├─ tippetLength, tippetRating
  └─ hookMakeModel, hookSize
```

Gear links to catches, so you can answer: "Which rod/reel setup caught the most fish?"

### What Catchbook Has

Nothing. No gear tracking at all.

### What Catchbook Could Do

Full gear tracking is deep. But a lightweight version would be:
- Add a `gear: String` optional field to CatchRecord (free text, like lureOrBait)
- Auto-suggest from previous entries
- Stats can then show "Setup A caught 30 fish, Setup B caught 12"

This lets users who care about tracking their rod/reel combos do so without building a full gear entity system. Revisit the full entity model later if demand warrants it.

---

## 6. The Species Counter (Real-Time Tally Tool)

This is a clever feature unique to Anglers' Log.

### How It Works

A simple screen with:
- A species picker at top
- A list of species with +/- stepper buttons
- Running total count

The user taps "+" each time they catch a fish. No photo, no details, no weight — just species and count. At the end of the session, they can "Create Trip" or "Add to Trip" which converts all the tallies into catch records linked to the trip.

### Why This Is Smart

For high-volume fishing (panfish, trout in a stocked pond, surf fishing), logging each fish individually is tedious. A tally counter lets users track volume quickly, then optionally add details later.

### What Catchbook Could Do

This would be a natural extension of the quick-catch flow. A "Tally Mode" that:
- Shows species buttons from recent catches
- Tap to increment count
- Auto-timestamps each tally
- At trip end, tallies become individual CatchRecords with species + time (no other details)

Simple to build, genuinely useful for high-volume fishing days.

---

## 7. The Add Catch Journey (Multi-Step Flow)

### How Anglers' Log Does It

Adding a catch isn't a single form. It's a guided multi-step journey:

1. **Photo picker** (if user tracks images) — shows immediately, extracts GPS from EXIF
2. **Species picker** (required) — pick or create species
3. **Fishing spot picker** (conditional) — shows map, auto-locates from photo GPS if available, matches nearby existing spots
4. **Full form** — all remaining fields pre-populated with what was gathered in steps 1-3

### The Photo-GPS-to-Spot Pipeline

This is particularly clever. When a user picks a catch photo:
1. App extracts GPS coordinates from photo EXIF metadata
2. Calls `FishingSpotManager.withinPreferenceRadius()` — checks if any saved spot is within the user's configured distance radius (configurable in settings)
3. If a match is found, auto-selects that fishing spot
4. If no match, pre-populates the coordinates for a new spot

This means: take a photo of your fish → the app automatically knows where you are and links it to the right spot. Zero manual location work.

### What Catchbook Does

A single-form approach: the catch editor shows all fields on one screen with an expandable optional section. Species, lure, method, weight, length, note, photo.

### What Catchbook Could Adopt

The photo-GPS pipeline is the highest-value piece here. Instead of restructuring the catch form:
- When user picks a photo, check for EXIF GPS data
- If GPS found and trip has no location yet, offer to set the trip location
- If GPS found and a known spot is nearby, surface "Caught near [Spot Name]?" confirmation
- This turns the photo into a location shortcut without requiring the user to think about it

---

## 8. Calendar View

### How Anglers' Log Does It

A month-view calendar (Syncfusion widget) shows:
- **Orange dots** on dates with catches
- **Green bars** spanning dates with trips (can span multiple days for multi-day trips)
- Tap a date to see all catches and trips from that day
- Month navigation + "Today" button

### What Catchbook Has

Nothing — no calendar view.

### What Catchbook Could Do

SwiftUI has native calendar components. A simple implementation:
- Month grid with colored dot indicators on fishing dates
- Tap a date to see the trip(s) and catches from that day
- Shows fishing frequency at a glance — "I haven't been out in 3 weeks"
- Reinforces the journal metaphor

This is a "Build Next" feature — low complexity, high perceived value. Users who log regularly love seeing their activity patterns on a calendar.

---

## 9. The Photo Gallery

### How Anglers' Log Does It

A dedicated photo gallery (accessible from the More tab) shows:
- Grid of all catch photos across all time
- Pinch-to-zoom (1x-5x) using `InteractiveViewer`
- Tap to open catch detail
- Photos are the visual anchor of the journal experience

### What Catchbook Has

Photos are attached to individual catches and visible in trip detail. No aggregate gallery view.

### What Catchbook Could Do

A "Photo Gallery" or "Trophy Wall" view that shows all catch photos as a scrollable grid. This is:
- Visually rewarding (your personal trophy wall)
- Quick way to find a specific catch by memory ("the big bass was in a photo with the red kayak")
- Low-effort to build (just query all CatchRecords with photos)

---

## 10. Smart Defaults and Auto-Suggestions

### Patterns from Anglers' Log

- **Auto-suggest from previous entries** — species, baits, and methods auto-complete from the user's own history, not a global database
- **Photo EXIF auto-fill** — date, time, location from photo metadata
- **Auto-fetch weather** — atmosphere data is fetched based on the catch's location and time, not just trip start
- **Per-catch weather** — weather is fetched for each catch individually, not just the trip-level snapshot. A morning catch might have different conditions than an afternoon catch.
- **Trip auto-population from catches** — when creating a trip and selecting catches, the app offers to auto-set trip fields (location, species, etc.) based on the selected catches

### What Catchbook Could Adopt

- **Auto-suggest species and lure from history** — as the user types, show matches from their own previous entries. This speeds up logging and reduces typos. After 20 catches, the user barely needs to type — just tap from their personal list.
- **Per-catch condition granularity** — right now Catchbook captures one ConditionSnapshot per trip. Consider whether catches logged hours apart should get their own weather context (WeatherKit supports historical queries for "what was the weather at this lat/lng at this time").

---

## 11. The In-App Polls System

Anglers' Log runs feature polls directly in the app. Users vote on what should be built next. This is:
- A feedback mechanism that doesn't require leaving the app
- A way to make users feel heard (reviews mention this)
- A prioritization tool for the solo developer

Catchbook could replicate this with a simple "What should we build next?" survey in Settings, but it's a post-launch feature at best.

---

## 12. Copy/Duplicate Catch

A Pro feature in Anglers' Log: tap a catch → "Copy" → new catch form pre-populated with all fields from the original. Just change what's different (species, weight, time).

This is extremely useful when fishing the same spot with the same setup and catching multiple fish. Instead of re-entering 10 fields, copy-paste and modify 2.

Catchbook could implement this as a context menu action on catch rows in trip detail.

---

## Summary: What to Take from Anglers' Log

### Adopt Now (High Impact, Reasonable Effort)

| # | Feature | Why |
|---|---------|-----|
| 1 | **Satellite/hybrid map toggle** | Users want to see actual water features. One button on the map. |
| 2 | **Auto-suggest species and lure from history** | Speeds up logging dramatically after first few catches. |
| 3 | **Copy/duplicate catch** | Context menu action. Saves time on repeat catches. |
| 4 | **Photo EXIF GPS → spot matching** | Turn the photo into a location shortcut. |

### Adopt Soon (Medium Effort, Strong User Value)

| # | Feature | Why |
|---|---------|-----|
| 5 | **GPS trail tracking** | The feature you want. 10-meter distance filter, background mode, trail rendered on map. Pro-only. |
| 6 | **Map as primary surface** | Make the map feel like a first-class citizen, not a sub-view. |
| 7 | **Catch pins on map overlay** | Show where fish were caught on the map, not just spots. |
| 8 | **Calendar view** | Simple month grid with fishing day indicators. Journal feel. |
| 9 | **Species tally counter** | Quick-tally mode for high-volume fishing days. |

### Adopt Later (Deep Features for Post-Launch)

| # | Feature | Why |
|---|---------|-----|
| 10 | **Configurable tracking toggles** | Let users hide fields they don't use. "Simple with unlimited customability." |
| 11 | **Bait variant system** | Distinguish "Senko - Green Pumpkin" from "Senko - Watermelon" in stats. |
| 12 | **Gear tracking** | Start with a free-text field, evolve to entity model if demand warrants. |
| 13 | **Photo gallery / trophy wall** | Aggregate all catch photos in a scrollable grid. |
| 14 | **In-app polls** | Let users vote on next features. |

---

## Where Catchbook Is Already Ahead of Anglers' Log

| Advantage | Detail |
|-----------|--------|
| **Deterministic insights** | Anglers' Log has stats. Catchbook has contextual recall — "last time here," similar conditions, what worked. That's smarter. |
| **Layered location model** | Anglers' Log has BodyOfWater → FishingSpot (two levels). Catchbook has Waterbody → Spot → Trip with fallback chains. More nuanced. |
| **No account at all** | Anglers' Log uses Firebase auth for backup features. Catchbook has zero auth. |
| **Zero third-party SDKs** | Anglers' Log uses Firebase, Mapbox, Syncfusion, Visual Crossing, WorldTides. Catchbook uses only Apple frameworks. |
| **Native iOS** | Anglers' Log is Flutter (cross-platform). Catchbook is SwiftUI. On iOS, native always feels tighter — animations, system integration, gestures. |
| **Share card with PB badge** | Anglers' Log has basic social sharing. Catchbook has a rendered share card with personal best badges and hidden GPS. |
| **WeatherKit (no API key)** | Anglers' Log uses Visual Crossing (third-party weather API). Catchbook uses Apple WeatherKit — included free with Apple Developer membership. No external dependency. |
| **Post-trip spot creation** | Anglers' Log doesn't offer to create a spot from a finished trip. Catchbook does. |

---

*Sources: Anglers' Log GitHub repository (cohenadair/anglers-log), App Store listing, anglerslog.ca website, App Store reviews, version history. Research conducted April 12, 2026.*
