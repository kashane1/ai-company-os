---
date: 2026-04-11
topic: catchbook-location-model
---

# Catchbook Location Model Brainstorm

## What We're Building
Catchbook needs a clearer location model that improves memory recall without turning every logging flow into a mapping tool. The current issue exposed by the new Spots and Trips maps is that location data exists in multiple places with different meanings: trip condition snapshots may have coordinates, but spots and waterbodies often do not. That makes records feel more precise than the map layer can actually represent.

The goal is to define a location model that is simple enough for everyday use, precise enough to support maps and future insights, and structured enough to power later summaries such as productive waters, reliable spots, and location-aware recall. The experience should stay private, lightweight, and easy to trust.

An important product principle also emerged from this discussion: **Catchbook should minimize the felt burden of data entry by doing as much intelligent prefilling and suggestion work as possible.** When the app can make a strong guess, it should present a confident default and make correction easy, rather than asking the user to build every record from scratch.

## Why This Approach
We considered three broad approaches:

### Approach A: Minimal Recall Model
Keep only waterbody and spot coordinates, and ignore trip- or catch-level precision for now.

**Pros:**
- Simple mental model
- Lowest UI complexity
- Easier migration from current data

**Cons:**
- Weak support for "where exactly on this trip?" questions
- Trip condition coordinates remain disconnected
- Harder to build higher-confidence summaries later

**Best when:** the product is focused almost entirely on simple saved-place recall.

### Approach B: Layered Location Model
Store coordinates at different levels based on their role: waterbody for canonical place, spot for user-defined fishing area, trip for observed location during that outing, and optional catch-level precision later.

**Pros:**
- Best balance of simple UX and future analytical value
- Maps can become trustworthy without forcing exact capture everywhere
- Lets the app distinguish canonical, inferred, and observed location

**Cons:**
- Requires clearer product language about what each coordinate means
- Touches trip flow, spot creation, and map fallbacks

**Best when:** the product wants simple recall first, with room for deeper pattern analysis.

### Approach C: Precision-First Model
Push users toward dropping pins and capturing exact coordinates for waters, spots, trips, and catches as often as possible.

**Pros:**
- Strongest raw data for future analysis
- Enables catch heatmaps and micro-location summaries earlier

**Cons:**
- Highest user friction
- Greater privacy sensitivity
- Risks making the app feel technical instead of reflective

**Best when:** precision is the core product promise and users are willing to do more input work.

### Recommendation
Choose **Approach B: Layered Location Model**.

It matches the product direction we discussed: optimize for simple memory recall, but store enough structured place data to support better maps and richer summaries later. It avoids overfitting the product around exact coordinates while still giving the app a clear long-term model for location-aware recall.

## Key Decisions
- **Catchbook should do the work first.**
  Across the app, the product should reduce the tediousness of logging by prefilling likely values whenever possible. For location-related flows, that includes suggesting nearby waters, dropping likely spot pins, reusing recent context, and proposing follow-up actions such as creating a spot after a trip.

- **Waterbody should have one canonical coordinate.**
  This is the representative map anchor for the place itself. It should support search, zoomed-out maps, weather fallback, and later water-level summaries.

- **Spot should be user-owned, user-named, and optionally pin-drop based.**
  A spot is the user's remembered fishing area within a waterbody. This is the most important precision layer for recall.

- **Trip should retain its own observed location for conditions.**
  The trip's weather/location snapshot should not be treated as identical to the waterbody's canonical coordinate. It represents where the user actually was that day, not necessarily the water's center.

- **Catch-level coordinates should be optional and likely phased later.**
  They are valuable for exact bite-zone analysis, but they should not be required in the initial redesign. The app should first prove value with waterbody, spot, and trip-level location.

- **The app should distinguish exact, inferred, and inherited coordinates.**
  Trust matters. If a map pin or summary is derived from a spot, a trip snapshot, or a canonical waterbody center, that should be understandable in the product language and model.

- **Known waterbody selection should be supported when possible.**
  If map/place search is available, users should be able to choose an existing named waterbody instead of always creating one manually. Private/custom waters should still be supported.

- **Map behavior should prefer user memory over raw GPS noise.**
  Waterbody maps should show waters. Spot maps should show user spots. Future exact-catch maps should only appear if the product earns that precision without cluttering the core experience.

- **Confidence should shape the UI more than provenance should.**
  In the main logging flow, users likely do not need explicit "this was inferred" system language. Instead, Catchbook should express confidence through the value shown and make editing easy. Detailed provenance can exist deeper in the model and, when needed, secondary UI.

## Resolved Questions
- **Should Catchbook optimize for simple recall or deeper analysis?**
  Simple recall is the priority, but not at the expense of collecting enough location structure to support later analysis.

- **Should waterbody and weather coordinates always be the same?**
  No. Waterbody coordinates represent the place. Trip weather coordinates represent the observed outing location and should remain separate concepts.

- **Should spot names be system-generated from the map?**
  No. Spot names should remain user-entered. The map should help place the spot, not define its meaning.

- **What should the primary waterbody entry flow be?**
  Waterbody entry should be search-first. As the user types, Catchbook should show smart autocomplete suggestions using canonical waterbody/place results, ranked with nearby matches first and farther matches later. A nearby map-entry control should let the user switch to a map flow and select a waterbody by dropping a pin.

- **When should a spot get a pin?**
  Spot creation should drop a pin immediately using the best available current location. The user should be able to open a map view right there to fine-tune the spot location before or during save.

- **Should trips without spots lead to new-spot creation?**
  Yes. If a trip ends without a saved spot, Catchbook should suggest creating one from the trip's observed location and may offer suggested spot names to reduce friction.

- **What location language should the product use?**
  The product should probably avoid technical words like "exact" and "estimated" in the main UI. A better direction is plain-language labels such as **"At"** for precise recorded location and **"Near"** for inherited or approximate location. Supporting detail text can explain where the location came from when needed.

- **Should Catchbook expose inference details in the main flow?**
  Not usually. The preferred direction is to show confident defaults, let users change them easily, and reserve provenance detail for deeper UI only when necessary.

## Product Implications
- This suggests an app-wide design principle, not just a location-specific one: Catchbook should aggressively reduce data-entry friction through intelligent defaults, suggestions, and context reuse.
- Waterbody creation should become smart-autocomplete first, with map-assisted selection as a nearby alternate path.
- Spot creation should use an immediate pin drop with optional fine-tuning in map view.
- Trip flow should support post-trip spot creation suggestions when no spot was chosen during the outing.
- Trip flow may need clearer handling for "using saved spot location" versus "recording actual outing location."
- Maps need stronger fallback rules and clearer semantics about what each pin means.
- Future summaries can become more useful once location layers are explicit and trustworthy.

## Confidence UX Direction
- Use smart defaults whenever the app has a strong guess.
- Keep the user in control by making every guessed value easy to change.
- Prefer plain-language certainty cues over technical provenance labels.
- Use **"At"** when the app has a precise user-selected or recorded location.
- Use **"Near"** when the app is using an inherited, approximate, or lower-confidence location.
- Consider preserving richer confidence/provenance in the model for future explanations, audits, or smarter suggestion systems.

## Suggested Phasing
- **Phase 1:** Smart waterbody autocomplete, canonical waterbody coordinates, and immediate spot pin-drop with optional fine-tuning
- **Phase 2:** Trip observed-location support, better map fallbacks, and post-trip "create a spot from this trip" suggestions
- **Phase 3:** Optional catch-level coordinates and advanced location-aware summaries

## Open Questions
- Should map-based waterbody selection snap to a nearby canonical named waterbody automatically, or allow fully custom unnamed/private water creation from the dropped pin?
- What suggested spot-name patterns should Catchbook use after a trip: directional names, shoreline features, user notes, or nearby place labels?
- In the UI, when should Catchbook surface location provenance details beyond "At" and "Near" so users trust the summaries without feeling overloaded?

## Next Steps
- Refine the location model into explicit product rules for waterbody, spot, trip, and catch data ownership.
- Decide the preferred UX entrypoint for known waterbody selection and spot pin-drop.
- Decide whether the "Catchbook should do the work first" principle should live only in this feature plan or be elevated into broader product/architecture guidance.
- Move into a deep planning session for phased implementation across models, forms, maps, and summaries.
