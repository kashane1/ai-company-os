# Competitive Deep Dive: Fishing Log Apps vs. Catchbook

**Date:** April 12, 2026
**Purpose:** Identify standard fishing log features Catchbook must match, plus small details from LogIT and other competitors that would make Catchbook feel complete.

---

## Primary Competitor: LogIT (Fishing Log & Journal)

LogIT is the closest direct competitor — a native iOS, privacy-respecting, personal fishing journal with no social features. It launched Nov 2024 and has iterated aggressively (20+ releases in 5 months). 4.7/5 rating, 19 ratings. $29.99 lifetime / $9.99/yr / $1.99/mo.

### LogIT Features Catchbook Currently LACKS

These are features LogIT has that Catchbook does **not** currently have in its data model or UI:

| # | Feature | LogIT Implementation | Catchbook Status | Priority |
|---|---------|---------------------|------------------|----------|
| 1 | **Released vs. Kept toggle** | Not in LogIT, but found in MyCatch as explicit popup selector | Missing from CatchRecord model entirely | **HIGH** — this is a universally expected fishing log feature |
| 2 | **Fishing method field** | Records method (e.g., spinning, fly, trolling, bottom) | Has `method` field in CatchRecord ✓ | Already done |
| 3 | **Bait/lure distinction** | Separate tracking of bait type | Has `lureOrBait` combined field ✓ | Consider splitting later |
| 4 | **Water depth** | Records depth at catch location | Missing from CatchRecord | **MEDIUM** — serious anglers track this |
| 5 | **Distance from shore** | How far from shore the bait was placed | Missing from CatchRecord | LOW — niche but differentiating |
| 6 | **Water level** | Current water level (high/normal/low) | Missing from ConditionSnapshot | **MEDIUM** — useful for river/reservoir anglers |
| 7 | **Beaufort scale (BFT)** | Wind force on Beaufort scale | Has windSummary but not BFT specifically | LOW — windSummary is adequate |
| 8 | **Tide conditions** | Incoming/outgoing/high/low tide state | Missing from ConditionSnapshot | **MEDIUM** — essential for saltwater anglers |
| 9 | **Air pressure** | Barometric pressure at time of catch | Missing from ConditionSnapshot | **MEDIUM** — many anglers correlate this with bite activity |
| 10 | **Water clarity** | Clear/stained/muddy water | Missing from ConditionSnapshot | **MEDIUM** — affects lure choice, anglers track this |
| 11 | **Moon phase** | Moon phase at time of fishing | Missing from ConditionSnapshot | **MEDIUM** — solunar theory believers want this |
| 12 | **Multiple photos per catch** | Up to 8 images per catch | Single photo (photoData) only | **MEDIUM** — users want hero shot + measurement + release |
| 13 | **Day-level notes/events** | Notes and events per fishing day, separate from catch notes | Trip has notes, but no separate event system | LOW — trip notes may suffice |
| 14 | **Favorite/starred sessions** | Mark special days as favorites | Missing from Trip model | **LOW** — nice-to-have |
| 15 | **Skunked day tracking** | Explicit "skunked" button for days with no catch | Has skunked trip concept ✓ | Already done |
| 16 | **Success rate statistics** | Calculates success rate from days with vs. without catches | Has catch rate insight rules ✓ | Already done |
| 17 | **Catches per hour** | Calculates CPH from trip duration and catch count | Could be derived but not currently shown | **MEDIUM** — easy to compute, valuable stat |
| 18 | **Total fishing time** | Aggregate hours spent fishing | Could be derived from trip start/end | **MEDIUM** — easy to compute, valuable stat |
| 19 | **Season filtering for stats** | Filter all statistics by season | Has season filter in TripsView ✓ | Already done |
| 20 | **CSV export with images** | Export data as CSV + images in ZIP | Has LogbookBackupExporter ✓ | Already done |
| 21 | **Satellite map mode** | Toggle between classic and satellite map | Could be added to CatchbookMapView | LOW |
| 22 | **Simplified input mode** | Hide optional fields for faster entry | Has showingOptionalFields toggle ✓ | Already done |
| 23 | **Camera capture** | Direct camera button in catch logging | Uses PhotosPicker only | **MEDIUM** — faster than photo library |
| 24 | **Auto-fill from photo metadata** | Extract date/time/location from photo EXIF | Missing | LOW — nice but not essential |
| 25 | **Catch search** | Search across all catches | Missing from TripsView | **MEDIUM** — useful with large catch history |
| 26 | **Alternative catch log view** | Different view of all catches (not trip-grouped) | Missing — catches only shown within trips | **MEDIUM** — flat catch list is useful |
| 27 | **Swipe-to-delete safety toggle** | Setting to disable accidental swipe deletion | Missing | LOW |
| 28 | **Fullscreen photo view with zoom** | View catch photos fullscreen with pinch zoom | Unknown — needs checking | LOW |

---

## Cross-Competitor Feature Gap Analysis

Features found across multiple competitors that Catchbook should consider:

### Tier 1: MUST HAVE (Expected by any fishing log user)

| Feature | Who Has It | Catchbook Status |
|---------|-----------|-----------------|
| **Released vs. Kept/Harvested** | MyCatch (explicit popup), GotOne, Log.Fish | **MISSING** — Add to CatchRecord |
| **Personal bests with visual indicator** | LogIT (crown icons by species) | **HAS IT** ✓ |
| **Species tracking** | All competitors | **HAS IT** ✓ |
| **Photo per catch** | All competitors | **HAS IT** ✓ |
| **Trip-based organization** | LogIT, ANGLR, MyCatch, Anglers' Log | **HAS IT** ✓ |
| **Map with saved spots** | All competitors | **HAS IT** ✓ |
| **Weather auto-capture** | LogIT, ANGLR, FishAngler, Anglers' Log | **HAS IT** ✓ |
| **Offline functionality** | ANGLR, Anglers' Log, LogIT | **HAS IT** ✓ |
| **Skunked trip logging** | LogIT, Anglers' Log | **HAS IT** ✓ |
| **Data export** | LogIT (CSV), Anglers' Log (CSV) | **HAS IT** ✓ |
| **Privacy-safe sharing** | LogIT (hides location) | **HAS IT** ✓ |

### Tier 2: SHOULD HAVE (Common enough to feel like a gap if missing)

| Feature | Who Has It | Catchbook Status |
|---------|-----------|-----------------|
| **Water depth at catch** | LogIT, FishAngler (45+ attrs) | **MISSING** |
| **Water clarity** | LogIT, FishAngler, Anglers' Log | **MISSING** |
| **Air pressure / barometric** | LogIT, FishAngler, Anglers' Log | **MISSING** |
| **Moon phase** | LogIT, FishAngler, Anglers' Log, Fishbrain | **MISSING** |
| **Tide conditions** | LogIT, Fishbrain, Pro Angler | **MISSING** |
| **Multiple photos per catch** | LogIT (8), Anglers' Log, FishAngler | **MISSING** (single photo only) |
| **Catches per hour stat** | LogIT (Pro) | **MISSING** (derivable) |
| **Total fishing time stat** | LogIT (Pro) | **MISSING** (derivable) |
| **Direct camera capture** | LogIT, MyCatch, FishAngler | **MISSING** (PhotosPicker only) |
| **Catch search / flat catch list** | LogIT, Anglers' Log | **MISSING** |

### Tier 3: NICE TO HAVE (Differentiating but not expected)

| Feature | Who Has It | Catchbook Status |
|---------|-----------|-----------------|
| **GPS trip route tracking** | ANGLR, Anglers' Log (Pro), MyCatch | Not planned (battery concern) |
| **AI Fish ID** | Fishbrain, FishAngler | Explicitly deferred |
| **Tournament/event mode** | MyCatch, Log.Fish, FishAngler | Not planned |
| **Apple Watch support** | ANGLR | Explicitly deferred |
| **Tackle box / gear library** | ANGLR, FishAngler | Not planned |
| **Fishing forecast / BiteTime** | Fishbrain, FishAngler, WeFish | Not planned (not a journal feature) |
| **Satellite map toggle** | LogIT | Easy to add |
| **Favorite/starred trips** | LogIT | Easy to add |
| **Distance from shore** | LogIT | Niche but interesting |
| **Beaufort wind scale** | LogIT | windSummary sufficient |
| **Calendar view** | Anglers' Log | Not planned |
| **Species counter (real-time)** | Anglers' Log (Pro) | Not planned |

---

## The "Released vs. Kept" Detail

This is the specific feature you noticed. Here's how competitors handle it:

- **MyCatch**: Explicit popup asking "Released" or "Harvested" after logging a catch. Conservation-focused — this drives their citizen science data.
- **GotOne**: Tracks released vs. kept as core data point for conservation research partnerships.
- **Log.Fish**: Includes catch disposition as part of their verification system.
- **LogIT**: Does NOT have this (as of v2.0.4).
- **Fishbrain / FishAngler / ANGLR**: Do NOT have this.

**Recommendation for Catchbook:** Add a `catchDisposition` field to `CatchRecord` with values: `released`, `kept`, `notRecorded` (default). Present as a simple segmented control or toggle in the catch logging flow. This enables:
- Stats on release rate by species
- Filter catches by disposition
- "You released 47 fish this season" type insights
- Share card could show "Released" or "Kept" badge
- Aligns with conservation-minded angler identity

---

## Detailed Feature Recommendations for Catchbook

### Priority 1 — Add Before Launch (Missing "table stakes")

1. **Released/Kept toggle on catch logging**
   - Add `catchDisposition: String` to `CatchRecord` (values: "released", "kept", "")
   - Simple segmented control in quick-catch and catch editor flows
   - Default to empty (not recorded) so it doesn't slow down logging

2. **Water clarity field**
   - Add `waterClarity: String?` to `ConditionSnapshot` (values: "clear", "stained", "muddy", "")
   - Simple picker in condition capture

3. **Moon phase (auto-captured)**
   - Can be computed from date alone (no API needed)
   - Add `moonPhase: String?` to `ConditionSnapshot`
   - Auto-populate on trip start from date calculation

4. **Air pressure (from WeatherKit)**
   - Already using WeatherKit — just capture the pressure field too
   - Add `pressureHPa: Double?` to `ConditionSnapshot`

### Priority 2 — Add Soon After Launch

5. **Tide conditions**
   - Add `tideState: String?` to `ConditionSnapshot` (values: "incoming", "outgoing", "high", "low", "slack", "")
   - Manual selection — reliable tide APIs are complex

6. **Water depth at catch**
   - Add `waterDepthM: Double?` to `CatchRecord`
   - Optional numeric field in catch logging

7. **Multiple photos per catch**
   - Change from single `photoData` to array/relationship
   - Allow 2-4 photos (hero shot, measurement, release)

8. **Direct camera capture**
   - Add camera button alongside PhotosPicker in catch logging
   - Faster than browsing photo library while on the water

9. **Catches per hour and total fishing time stats**
   - Pure computation from existing data (trip duration / catch count)
   - Surface in insights or trip summary

10. **Catch search and flat catch list**
    - All-catches view (not trip-grouped) with search by species, lure, date
    - Useful once user has 50+ catches

### Priority 3 — Later Enhancement

11. **Favorite/starred trips** — flag memorable sessions
12. **Water level** — for river/reservoir anglers
13. **Satellite map toggle** — easy MapKit configuration
14. **Auto-fill from photo EXIF** — date/time/location from photo metadata
15. **Fullscreen photo zoom** — quality of life for reviewing catches
16. **Swipe-to-delete safety setting** — prevent accidental data loss

---

## What Catchbook Already Does Better Than Competitors

These are areas where Catchbook is ahead — don't lose these advantages:

| Advantage | Detail |
|-----------|--------|
| **Zero account required** | No competitor except ANGLR offers this; LogIT requires iCloud |
| **Zero third-party SDKs** | Cleanest privacy story in the category |
| **Deterministic insights** | LogIT has stats; Catchbook has recall-focused insights (what worked here, when, similar conditions) |
| **Layered location model** | Waterbody → Spot → Trip hierarchy is more sophisticated than any competitor |
| **Personal best badges on share cards** | No competitor integrates PB badges into sharing |
| **Spot recall ("Last time here")** | No competitor surfaces contextual recall at trip start |
| **App size** | Catchbook likely competitive with LogIT's 15.7 MB vs. ANGLR's 438 MB |
| **No ads, no paywall degradation** | Unlike Fishbrain/FishAngler which strip features over time |

---

## Pricing Context

The competitive landscape suggests these pricing sweet spots for a premium fishing journal:
- **Lifetime:** $24.99–$34.99 (LogIT: $29.99)
- **Annual:** $9.99–$14.99 (LogIT: $9.99, Anglers' Log: $11.99)
- **Monthly:** $1.49–$1.99 (LogIT: $1.99, Anglers' Log: $1.49)

Subscription fatigue is REAL in this market. Fishbrain ($12.99/mo) and FishAngler ($6.99/mo) are widely criticized for aggressive paywalling. The lifetime option is a strong differentiator.

---

## Summary: The Gap Checklist

| Feature | Status | Action |
|---------|--------|--------|
| Released/Kept toggle | MISSING | Add to CatchRecord model + UI |
| Water clarity | MISSING | Add to ConditionSnapshot |
| Moon phase | MISSING | Auto-compute from date |
| Air pressure | MISSING | Pull from WeatherKit |
| Tide state | MISSING | Add manual picker |
| Water depth | MISSING | Add to CatchRecord |
| Multiple photos | MISSING | Expand from single to multi |
| Camera capture button | MISSING | Add alongside PhotosPicker |
| Catches per hour | DERIVABLE | Compute and surface |
| Total fishing time | DERIVABLE | Compute and surface |
| Catch search | MISSING | Add search/flat list view |
| Species tracking | HAS IT | ✓ |
| Trip organization | HAS IT | ✓ |
| Personal bests | HAS IT | ✓ |
| Map with spots | HAS IT | ✓ |
| Weather capture | HAS IT | ✓ |
| Skunked trips | HAS IT | ✓ |
| Export/backup | HAS IT | ✓ |
| Privacy-safe sharing | HAS IT | ✓ |
| Offline-first | HAS IT | ✓ |
| Insights/recall | HAS IT | ✓ |

---

*Sources: App Store listings (LogIT, MyCatch, Fishbrain, FishAngler, ANGLR, Anglers' Log, Fishidy, Pro Angler, GotOne, Log.Fish), App Store reviews, competitor websites, FishingBooker expert reviews, GilledIt comparisons. Research conducted April 12, 2026.*
