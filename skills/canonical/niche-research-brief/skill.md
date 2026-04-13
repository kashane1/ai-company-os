# Skill: niche-research-brief

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Research a product niche and produce a structured brief covering audience
profile, pain points, seasonal calendar, credibility lexicon, social media
landscape, content gaps, competitor app intelligence, archetype performance,
and a scored topic registry. Accumulates intelligence across runs via a
persistent memory file so every execution builds on previous findings.

## Contract

Inputs:

- `product_id`: string — product identifier from `infra/products.json`.
- `niche`: string — target niche description (e.g. "freshwater bass fishing").
- `platforms`: list of enum — social platforms to analyze. Default: `[tiktok]`.
  Values: `tiktok`, `instagram`, `threads`, `x`, `youtube`.
- `focus_areas`: list of string or null — optional areas to emphasize this run
  (e.g. "seasonal patterns", "competitor reviews"). Null means balanced pass.

Outputs:

- `brief_path`: string — path to `docs/products/<product_id>/gtm/niche-research-brief.md`.
- `memory_path`: string — path to `docs/products/<product_id>/gtm/niche-research-memory.yaml`.
- `topics_discovered`: int — count of new topics added to the registry this run.
- `run_number`: int — sequential run number for this product.

## Allowed edit boundaries

- `docs/products/<product_id>/gtm/niche-research-brief.md`
- `docs/products/<product_id>/gtm/niche-research-memory.yaml`

## Forbidden areas

- `apps/`
- `packages/`
- `infra/`
- `state/`
- `products/`

## Dependencies

- Web search and web fetch tools (for research)
- `docs/products/<product_id>/gtm/performance-log.md` (read-only, for feedback loop)
- `docs/products/<product_id>/gtm/content-backlog.yaml` (read-only, to know what topics are already in use)

## Memory file

There is exactly **one memory file per product** at
`docs/products/<product_id>/gtm/niche-research-memory.yaml`.

The memory file stores two layers of intelligence:

- **Product-level context** — identity, features, cross-niche vocabulary,
  product-level competitors. Shared across all niches. Written once on first
  run, updated when product scope changes.
- **Niche-level context** — audience, topics, sources, lexicon, seasonal
  calendar, archetype performance. One section per niche, keyed by niche-id
  (kebab-case, e.g. `freshwater-bass-fishing`).

The full YAML schema is defined in `memory-schema.yaml` in this skill's
canonical directory. **Follow that schema exactly.** Every field, nesting
level, and enum value must match the schema. The schema is the contract —
do not invent fields or skip required ones.

Key schema rules:
- Never delete entries from `runs`, `topics`, or `lexicon`. Append-only.
- Topics are the core unit. Each gets a unique id within its niche.
- The lexicon has 6 categories: species, techniques, gear_brands, slang,
  locations, seasons_and_conditions.
- Confidence ratings: high (3+ sources), medium (2 sources), low (1 source).
- Composite scores are always recalculated from dimension scores.
- When a niche run discovers product-level intelligence (e.g. a competitor
  that spans niches), write it to `product_context`, not just the niche.
- The seasonal_calendar must cover all 12 months.

---

## Instructions

### Phase 0 — Load product context

0. **Read the memory schema** at
   `skills/canonical/niche-research-brief/memory-schema.yaml` to understand
   the exact structure you must produce.

### Phase 1 — Load memory and close the feedback loop

1. **Read the memory file** at `docs/products/<product_id>/gtm/niche-research-memory.yaml`.
   If it does not exist, this is the first run for this product — initialize
   the memory structure per the schema:
   - Populate `product_context` from `docs/products/<product_id>/founder-brief.md`,
     `product-brief.md`, and `mvp-spec.md` if they exist.
   - Create an empty niche entry under `niches.<niche-id>`.
   If the memory file exists but this niche is not in it, add a new niche
   entry — do not overwrite existing niches or product context.

2. **Read the performance log** at `docs/products/<product_id>/gtm/performance-log.md`.
   For each row with engagement data, attempt to match it to a topic in the
   memory file's `topics` registry (match by content hook text or topic ID if
   the backlog item references one).

3. **Update topic performance ratings** in memory:
   - If a topic's content received above-median engagement → `content_performance: high`
   - Median → `content_performance: medium`
   - Below median → `content_performance: low`
   - Adjust `signal_strength` accordingly: high-performing topics get promoted,
     low-performing topics get a note but are not deleted (patterns emerge over
     multiple runs).

4. **Read the content backlog** to know which topics from memory have already
   been turned into content items. Set `used_in_content: true` for those topics.

### Phase 2 — Plan the research pass

Based on what the memory file already knows:

5. **Identify research priorities:**
   - Sources not sampled in the last 30 days → high priority
   - Sources with `signal: high` → re-check for new threads/trends
   - Sources with `signal: low` → skip unless `focus_areas` overrides
   - If Run 1: sample all Tier 1 sources

6. **Identify topic gaps:**
   - Content archetypes with few or no topics → need discovery
   - Topics with `content_performance: high` → find more topics in the same shape
   - The `focus_areas` input can override automatic prioritization

### Phase 3 — Execute research (deep pass)

Research sources in priority order. For each source, use web search and web
fetch to gather intelligence. Extract structured findings.

#### Source: Reddit

7. **Discover relevant subreddits** (Run 1) or re-check known subreddits.
   Search for `site:reddit.com "<niche>" subreddit` to find communities.
   For each subreddit:
   - Search for top posts (by upvotes/engagement)
   - Extract: pain points, debates, frequently asked questions, gear mentions,
     species references, technique names, seasonal patterns
   - Note thread titles and upvote counts as signal strength indicators
   - Rate the subreddit's signal quality and store in memory

#### Source: App Store competitor reviews

8. **Discover competing apps** (Run 1) or re-check cached competitors.
   Search for `"<niche>" app site:apps.apple.com` and variations.
   For each competitor:
   - Read recent reviews (focus on 2-4 star reviews — they contain the most
     actionable feedback)
   - Extract: praised features, complaints, missing feature requests, exact
     user language
   - Store competitor name, key complaints, and key praise in memory

#### Source: TikTok / social platform analysis

9. **Search for niche content on target platforms.**
   Search for `"<niche>" tiktok` and relevant hashtags.
   Extract:
   - Which content formats perform (slideshow, POV video, tutorial, etc.)
   - Top creators in the niche (names, rough follower counts)
   - Hook patterns that appear in high-performing content
   - Hashtag clusters with volume estimates
   - Which content archetypes dominate (educational, identity, debate, etc.)

#### Source: Google Trends

10. **Check seasonal patterns.**
    Search for trend data on niche-related queries.
    Extract:
    - Monthly interest patterns (when does this niche peak/trough?)
    - Rising queries (what's gaining interest?)
    - Regional differences if notable

#### Source: Amazon / gear reviews (targeted)

11. **Fill lexicon gaps only.** Do not do a broad scrape.
    If the credibility lexicon is missing brand names, gear categories, or
    technique-specific terminology, search for `"best <niche> <gear>" reviews`
    and extract the specific terms anglers/enthusiasts use.

### Phase 4 — Classify and score topics

12. **Classify every discovered topic into a content archetype:**

    | Archetype | Trigger | Primary engagement |
    |-----------|---------|-------------------|
    | Pain Point | "I've had that problem" | Comments, saves |
    | Value / Educational | "I learned something" | Saves, follows |
    | Identity / Tribal | "That's so me" | Shares, comments |
    | Debate / Hot Take | "I have an opinion" | Comments (high volume) |
    | Aspirational / Aesthetic | "I want that life" | Saves, shares |
    | Humor / Relatable | "I need to send this to someone" | Shares |
    | Seasonal / Timely | "This is relevant right now" | Comments, follows |
    | Behind-the-scenes / Process | "I feel like I know this person" | Follows, comments |

13. **Score every topic** on 5 dimensions (each 0-100):

    - **Virality** — Will people engage (comment, share, save, stitch)?
      Indicators: polarizing, relatable, surprising, comment-bait.
    - **Niche fit** — How specific is this to the target audience?
      100 = only this audience gets it. 0 = generic/anyone content.
    - **Product alignment** — How naturally does the product connect?
      100 = product directly solves this. 0 = no connection at all.
    - **Content gap** — Is this underserved by existing creators?
      100 = nobody covers it well. 0 = saturated topic.
    - **Timeliness** — Is this relevant right now (season, trend, event)?
      100 = relevant this week. 0 = evergreen / no urgency.

    Composite score formula (engagement-first weighting):

    ```
    Composite = (Virality x 0.30) + (Niche fit x 0.25) + (Content gap x 0.20)
              + (Timeliness x 0.15) + (Product alignment x 0.10)
    ```

    Product alignment is intentionally the lowest weight. The strategy is
    engagement-first — build audience, then convert.

14. **Analyze archetype performance** for this niche.
    Based on what the research shows about top-performing content in the niche,
    assess which archetypes over-perform and under-perform. Recommend a target
    mix with percentage allocations that sum to 100%.

### Phase 5 — Merge findings into memory

All writes target the niche entry at `niches.<niche-id>` unless the finding
is product-level (competitor that spans niches, cross-niche vocabulary).
Follow the schema in `memory-schema.yaml` for exact field names and types.

15. **Add new topics** to `niches.<niche-id>.topics`. Do not duplicate
    existing topics — if a topic matches an existing one (same core subject),
    update it instead and set `last_validated` to today. Each topic must
    include all fields from the schema: id, title, description, archetype,
    discovered, discovered_run, source, source_evidence, scores (all 5
    dimensions + composite), signal_strength, lifecycle, used_in_content,
    content_performance, backlog_item_number, last_validated,
    seasonal_relevance, still_relevant.

16. **Update source quality ratings** in `niches.<niche-id>.sources` based on
    this run's findings. Update `last_sampled` dates. Add any newly discovered
    subreddits, hashtags, creators, or channels.

17. **Grow the credibility lexicon** at `niches.<niche-id>.lexicon` with any
    new terms discovered. The lexicon has 6 categories: species, techniques,
    gear_brands, slang, locations, seasons_and_conditions. Each term gets a
    confidence rating based on `source_count` (high: 3+, medium: 2, low: 1).
    If a term already exists, increment its source_count and upgrade
    confidence if warranted.

18. **Update the seasonal calendar** at `niches.<niche-id>.seasonal_calendar`
    if new seasonal intelligence was found. All 12 months must be present.

19. **Update competitors.**
    - Product-level competitors → `product_context.competitors`
    - Niche-specific notes → `niches.<niche-id>.competitor_notes`
    If a competitor was already cached, update `last_reviewed` and merge
    any new complaints/praise. Do not overwrite existing entries.

20. **Update archetype performance** at
    `niches.<niche-id>.archetype_performance` based on social media research.
    All 8 archetypes must be present. `recommended_mix_pct` values must sum
    to 100.

21. **Update product context** if this run surfaced product-level intelligence:
    - New cross-niche vocabulary → `product_context.cross_niche_vocabulary`
    - New product-level competitors → `product_context.competitors`
    - Updated feature relevance → `product_context.features`

22. **Add a run entry** to `niches.<niche-id>.runs` with all required fields.

23. **Update top-level metadata**: set `last_updated` to today.

### Phase 6 — Generate the brief

24. **Write `niche-research-brief.md`** with ALL cumulative intelligence, not
    just this run's findings. The brief is the readable output; the memory file
    is the machine state.

    Required sections:

    ```
    ## Audience Profile
    ## Pain Points & Desires
    ## Seasonal Calendar
    ## Credibility Lexicon
    ## Social Media Landscape
    ## Content Gaps
    ## Competitor App Intelligence
    ## Archetype Performance
    ## Scored Topic Registry
    ```

    Each topic in the Scored Topic Registry includes:
    - Topic title (as a content hook)
    - Archetype classification
    - Composite score with all 5 dimension breakdowns
    - Source attribution
    - Lifecycle tag: `NEW` | `CONFIRMED` | `PROMOTED` | `DEPRIORITIZED` | `USED`
    - Platform and format recommendation

    Sort the Scored Topic Registry by composite score descending.

    The brief frontmatter must include:
    ```yaml
    product_id: <product_id>
    niche: "<niche>"
    generated: <date>
    run_number: <n>
    previous_run: <date or null>
    topics_total: <count>
    topics_new_this_run: <count>
    memory_file: niche-research-memory.yaml
    ```

### Phase 7 — Validate

25. Confirm the brief file exists and is non-empty.
26. Confirm the brief contains all 9 required sections.
27. Confirm the memory file is valid YAML that conforms to `memory-schema.yaml`.
28. Confirm the memory file has an updated run entry for this execution.
29. Confirm at least 3 sources were sampled (Run 1) or at least 1 source was
    re-checked (subsequent runs).
30. Confirm the credibility lexicon has entries in all 6 categories (species,
    techniques, gear_brands, slang, locations, seasons_and_conditions).
31. Confirm the seasonal calendar has all 12 months.
32. Confirm the scored topic registry has at least 10 topics (Run 1) or grew
    or explicitly noted "no new topics found" (subsequent runs).
33. Confirm all 8 archetypes are present in archetype_performance with mix
    percentages summing to 100.

## Non-goals

- This skill does not create or modify GTM artifacts (voice.md, hook-library.md,
  content-backlog.yaml, etc.). That is the job of `gtm-artifact-refresh`.
- This skill does not generate content, images, or posts.
- This skill does not publish anything or interact with social platforms.
- The performance log is read-only — this skill never appends to it.
