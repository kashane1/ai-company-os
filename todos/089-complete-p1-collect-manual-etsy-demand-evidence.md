---
status: complete
priority: p1
issue_id: "089"
tags: [home-from-working, etsy, research, marketplace-insights]
dependencies: []
---

# Collect manual Etsy demand and visibility evidence

## Problem Statement

Etsy Marketplace Insights, Search Visibility, Stats, and buyer-query data are needed to replace provisional candidate scores. Current Etsy API terms make automated browser/extension scraping an inappropriate route, and the initial read-only OAuth scopes do not expose these seller analytics.

## Findings

- A 15-row worksheet exists at `state/home-from-working/operations/marketplace-insights-template.csv`.
- The founder completed all 15 searches on 2026-09-06. Twelve rows contain Etsy search and competition counts; three rows preserve Etsy's displayed Error as an unknown rather than a zero.
- The import deduplicated 70 listings into 29 concepts. Fourteen concepts receive marketplace-evidence ranks; 15 remain incomplete, including every concept touched by one of Etsy's three Error rows.
- The founder explicitly waived related queries, dominant visual pattern, price band, and buyer occasion as out of scope on 2026-09-07. The blank fields remain unknown and are not used as zero-demand evidence or as a qualification claim.
- Signed-in read-only evidence now captures Search Visibility, aggregate Stats, and buyer search terms. Etsy reports nine visits, eight listing views, zero orders, and two buyer terms with one visit each; this is a baseline, not enough evidence for a format decision.
- The import command now preserves a completed worksheet, maps concept-specific queries before broad section queries, and deterministically calculates evidence ranks without bypassing hard gates.
- The Etsy audit recommends one manual pass through the first-party seller tools.

## Proposed Solutions

### Option 1: Founder completes the prepared worksheet

**Approach:** Run the 15 saved queries in Marketplace Insights and enter observed 30-day search/listing counts, related queries, trend, price/visual notes, and buyer occasion. Export aggregate Stats/Search Visibility data where Etsy provides it.

**Pros:** First-party evidence; complies with the conservative automation boundary.  
**Cons:** Requires a short manual session.  
**Effort:** 30–45 minutes  
**Risk:** Low.

### Option 2: Defer demand evidence

**Approach:** Keep all opportunities provisional and do not create a new production batch.

**Pros:** No founder time now.  
**Cons:** Days 8–21 exit condition remains unmet.  
**Effort:** None  
**Risk:** Medium business risk from continued guessing.

## Recommended Action

Use Option 1. Fill the worksheet in place; `scripts/home_from_working_opportunities.py` will import it on the next run, re-score demand/competition, and rank the opportunity set deterministically. Evidence ranking does not advance any concept past failed or unknown hard gates.

## Technical Details

**Affected files:**

- `state/home-from-working/operations/marketplace-insights-template.csv`
- `state/home-from-working/operations/opportunities/scored-concepts.json`
- `state/home-from-working/operations/evidence/`

## Resources

- [Etsy Marketplace Insights](https://help.etsy.com/hc/en-us/articles/35122361353239-How-Do-I-Use-Etsy-s-Marketplace-Insights-Tool)

## Acceptance Criteria

- [x] All 15 queries were attempted and contain observation dates; Etsy Error rows remain explicitly unknown.
- [x] Related queries, dominant visual pattern, price band, and buyer occasion are recorded or explicitly waived as out of scope.
- [x] Aggregate Search Visibility issues and buyer search terms are saved without buyer PII.
- [x] Candidate scores are regenerated with evidence coverage and source provenance.
- [x] A maximum of three concepts advances for founder review. None advances: all 29 concepts remain blocked by unknown hard gates, which satisfies the maximum without claiming a qualified shortlist.

## Work Log

### 2026-09-06 - Worksheet prepared

**By:** Codex

**Actions:** Created the manual evidence schema and populated the 15 approved query rows with blank metrics.

### 2026-09-06 - Founder observations imported

**By:** Codex

**Actions:** Validated all 15 attempted searches, retained three Etsy Error results as unknown, and regenerated a 29-concept deduplicated backlog. Fourteen concepts receive provisional evidence ranks; none advances past unknown hard gates.

**Learnings:** Search and competition counts are now available for 12 queries, but the qualitative columns and aggregate seller visibility evidence still need a deliberate completion or waiver decision. Ranking code now rejects substring and design-folder contamination, so terms such as `cat` do not match `caterpillar` and batch-folder names do not supply false concept evidence.

### 2026-09-06 - Seller analytics captured

**By:** Codex

**Actions:** Read Search Visibility, Shop Stats, and Etsy-search traffic details in the signed-in seller UI without saving changes. Stored a PII-free evidence record at `state/home-from-working/operations/evidence/2026-09-06/etsy-search-and-stats.json`.

**Learnings:** Etsy reports one visibility risk affecting 35 titles, nine visits, eight listing views, no orders, and two one-visit buyer terms: `halloween t-shirt` and `solar storm shirt`. This is far below the pilot decision threshold, so it does not justify a shop-wide format change.

### 2026-09-07 - Founder waived qualitative Marketplace Insights fields

**By:** Founder, recorded by Codex

**Actions:** Recorded the founder's explicit decision to waive related queries, dominant visual pattern, price band, and buyer occasion as out of scope. Verified all 15 query rows retain an observation date; the three Etsy Error rows remain unknown. Verified the PII-free aggregate Search Visibility, Shop Stats, and buyer-search evidence file remains present. Verified `scored-concepts.json` contains 29 deduplicated concepts, 14 with complete numeric Marketplace Insights evidence, zero evidence-qualified concepts, and no founder-review advancement.

**Learnings:** The waiver completes the qualitative-field acceptance criterion only. It does not turn heuristic factors, sparse shop analytics, or unknown hard gates into evidence qualification.

## Notes

Blank is unknown; it must never be interpreted as zero demand.

The founder waived only the four qualitative Marketplace Insights fields listed above. Numeric Etsy Error rows remain unknown and continue to block complete marketplace evidence for affected concepts.
