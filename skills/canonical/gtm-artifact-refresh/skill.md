# Skill: gtm-artifact-refresh

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Consume a niche-research-brief and refresh the GTM artifact chain:
content-taxonomy.md, voice.md, hook-library.md, hashtag-strategy.md,
content-backlog.yaml, and campaign-calendar.md. Preserves existing content
that is still valid, adds new items from the brief, retires stale entries,
and enforces content archetype mix balance.

## Contract

Inputs:

- `product_id`: string — product identifier from `infra/products.json`.
- `niche`: string — niche identifier (kebab-case, e.g. "freshwater-bass-fishing").
  Must match a key in the `niches` map of the memory file.
- `mode`: enum — `full` (rewrite all artifacts from brief) or `incremental`
  (add new items, preserve existing). Default: `incremental`.

Outputs:

- `artifacts_updated`: list of string — paths to artifacts that were modified.
- `backlog_items_added`: int — count of new content backlog items.
- `mix_balanced`: bool — whether the backlog meets taxonomy target ratios.
- `mix_report`: string — summary of archetype distribution vs. targets.

## Allowed edit boundaries

- `docs/products/<product_id>/gtm/content-taxonomy.md`
- `docs/products/<product_id>/gtm/voice.md`
- `docs/products/<product_id>/gtm/hook-library.md`
- `docs/products/<product_id>/gtm/hashtag-strategy.md`
- `docs/products/<product_id>/gtm/content-backlog.yaml`
- `docs/products/<product_id>/gtm/campaign-calendar.md`
- `docs/products/<product_id>/gtm/niche-research-memory.yaml`

## Forbidden areas

- `apps/`
- `packages/`
- `infra/`
- `state/`
- `products/`
- `docs/products/<product_id>/gtm/niche-research-brief.md` (read-only input)
- `docs/products/<product_id>/gtm/performance-log.md` (read-only)

## Dependencies

- `docs/products/<product_id>/gtm/niche-research-brief.md` (required input)
- `docs/products/<product_id>/gtm/niche-research-memory.yaml` (read + write)
- `content-voice-guardrail` skill (for validating voice.md changes)
- `social-post-safety` skill (for validating hashtag changes)

---

## Instructions

### Phase 1 — Load inputs

1. **Read the niche research brief** at
   `docs/products/<product_id>/gtm/niche-research-brief.md`.
   If it does not exist, abort with error: "Run niche-research-brief first."

2. **Read the niche research memory** at
   `docs/products/<product_id>/gtm/niche-research-memory.yaml`.
   Locate the niche entry at `niches.<niche>`. If the niche key does not
   exist in the memory file, abort with error: "Niche '<niche>' not found
   in memory file. Run niche-research-brief for this niche first."

3. **Read all existing GTM artifacts:**
   - `content-taxonomy.md` (may not exist yet — that is OK)
   - `voice.md`
   - `hook-library.md`
   - `hashtag-strategy.md`
   - `content-backlog.yaml`
   - `campaign-calendar.md`

4. **Determine mode.** If `content-taxonomy.md` does not exist, force
   `mode: full` regardless of input — the taxonomy must be created before
   incremental updates make sense.

### Phase 2 — Create or update content-taxonomy.md

5. **Extract archetype performance data** from the memory file at
   `niches.<niche>.archetype_performance` and the topic registry at
   `niches.<niche>.topics`. Use the memory YAML as the primary data source
   for all structured data — the brief is the human-readable summary, the
   memory file is the machine-readable contract.

6. **Build the taxonomy.** For each of the 8 content archetypes:

   | Archetype | Description |
   |-----------|-------------|
   | Pain Point | Audience recognizes a frustration they have experienced |
   | Value / Educational | Viewer learns something actionable |
   | Identity / Tribal | Audience feels seen, "that's so me" |
   | Debate / Hot Take | Viewer has an opinion and wants to share it |
   | Aspirational / Aesthetic | Viewer wants that life or experience |
   | Humor / Relatable | Viewer wants to send this to someone |
   | Seasonal / Timely | Content is relevant right now |
   | Behind-the-scenes / Process | Viewer feels a personal connection |

   For each archetype, write:
   - Trigger (what psychological response drives engagement)
   - Primary engagement type (comments, saves, shares, follows)
   - Voice note (how to write this archetype in the brand voice)
   - Product proximity (high/medium/low/none — how naturally the product connects)
   - Target mix percentage (from `niches.<niche>.archetype_performance[].recommended_mix_pct`)
   - 2-3 example hooks drawn from `niches.<niche>.topics` (highest composite scores for that archetype)

7. **Set the target mix.** The percentages must sum to 100%. They come from
   `niches.<niche>.archetype_performance`. Include the composite scoring
   weights:

   ```
   Composite = (Virality x 0.30) + (Niche fit x 0.25) + (Content gap x 0.20)
             + (Timeliness x 0.15) + (Product alignment x 0.10)
   ```

   These weights live in the taxonomy so they can be tuned per niche.

8. **Set mix rules:**
   - Never post 3+ of the same archetype in a row
   - Every week must include at least 1 Debate and 1 Identity post
   - Seasonal content overrides the calendar when a real-world event is active
   - Product mentions only in Pain Point and Value posts, and only when natural

9. **Write `content-taxonomy.md`** with frontmatter:
   ```yaml
   product_id: <product_id>
   niche: "<niche>"
   generated_from: niche-research-brief.md
   last_updated: <date>
   ```

### Phase 3 — Update voice.md

10. **Merge credibility lexicon into preferred vocabulary.**
    Read from `niches.<niche>.lexicon` in the memory file (not from the
    brief markdown). Also read `product_context.cross_niche_vocabulary`
    for product-level terms.
    - Add high-confidence species names to preferred vocabulary
    - Add high-confidence technique terms
    - Add location names that signal insider knowledge
    - Add seasons/conditions terms (e.g. "pre-spawn") with context notes
    - Add insider slang as acceptable in casual content (note the context)
    - Add gear brand names that signal authenticity

    **Multi-niche merge rule:** If this product has multiple niches in the
    memory file, voice.md is shared across all niches. When adding lexicon
    terms, prefix niche-specific terms with a context note (e.g.
    "pre-spawn — bass fishing") so terms from different niches coexist
    clearly. Cross-niche and product-level terms need no prefix.

11. **Do not remove existing vocabulary or banned phrases.** Only add.
    The voice guide is append-only for safety — removing constraints requires
    explicit founder approval.

12. **Preserve the existing voice pillars and "Who we are" section unchanged.**
    These are founder-authored and not derived from research.

### Phase 4 — Update hook-library.md

13. **Extract hook patterns** from `niches.<niche>.topics` (sorted by
    composite score) and `niches.<niche>.sources.tiktok.top_creators`
    in the memory file.

    **Multi-niche merge rule:** Hook library is shared per product. Tag
    niche-specific hooks with the niche name: `"Hook text" — [Archetype]
    — Niche: freshwater-bass-fishing — Source: topic-id`. Hooks that
    apply across niches omit the niche tag.

14. **Tag each hook with its archetype.** New format for hook items:
    ```
    - "Hook text here" — [Archetype] — Source: topic-id
    ```

15. **In incremental mode:** append new hooks below existing ones. Do not
    remove existing hooks that are still in the campaign calendar or have been
    used in published content.

16. **In full mode:** rewrite the hook library entirely from the brief, but
    preserve any hooks that appear in the performance log with above-median
    engagement.

### Phase 5 — Update hashtag-strategy.md

17. **Merge hashtag clusters** from `niches.<niche>.sources.tiktok.hashtags_tracked`
    (and equivalent for other platforms) in the memory file.

    **Multi-niche merge rule:** Hashtag strategy is shared per product.
    Group hashtags by niche under labeled sections. Platform limits apply
    per-post, not per-section — the strategy file is a reference pool.

18. **Respect platform limits** already defined in the existing hashtag strategy:
    - Instagram: max 8
    - TikTok: max 5
    - Threads: max 3

19. **Replace low-volume hashtags** with higher-volume alternatives from the
    brief, but keep hashtags that have appeared in published content with good
    engagement.

### Phase 6 — Update content-backlog.yaml

This is the most complex update. The backlog is a YAML list where each item
has full slide text, visual direction, captions, and hashtags. The refresh
skill authors all content at this stage, when research context is richest.

20. **Read the existing backlog** from `content-backlog.yaml` (YAML list).
    Lock items with status in `{generated, scheduled}` — do not modify their
    slides, captions, or visual_hints, as the factory may have already
    produced images from them.

21. **Add new items from the brief's scored topic registry.**
    For each topic in the registry that has `used_in_content: false`:

    a. **Select the archetype-based slide template:**

       | Archetype | Slides | Layout |
       |-----------|--------|--------|
       | value_educational | 3 | headline + 3 bullets + closing question |
       | pain_point | 2 | provocative headline + resolution |
       | debate_hot_take | 2 | claim + counter-argument |
       | identity_tribal | 2 | identity statement + closer |
       | aspirational_aesthetic | 2 | short text + visual emphasis |
       | humor_relatable | 2 | setup + punchline |
       | seasonal_timely | 3 | headline + seasonal detail + closer |
       | behind_the_scenes | 3 | headline + data/insight + reflection |

    b. **Author full slide text** using research context (topic description,
       source evidence, lexicon vocabulary). Each slide gets:
       - `text.headline`: string (required)
       - `text.subhead`: string (optional — closers, taglines)
       - `text.bullets`: list of string (optional — for Value/Educational)
       - `text.body`: string (optional — for longer formats)

    c. **Write `visual_hint` per slide** — a short Gemini prompt string
       describing the background image. No text instructions. Example:
       "underwater bass approaching a lure, murky green water, dramatic lighting"

    d. **Write a platform-specific caption** consistent with the voice guide.

    e. **Select hashtags** from `hashtag-strategy.md` as a flat list. The
       content-scheduler will trim to platform limits at post time.

    f. **Campaign Zero items** must never contain app mentions in any field.
       If a slide 3 exists, use engagement closers: "Which one's your go-to?",
       "Save this for your next trip", "Drop your answer below."

    Each item follows this YAML schema:
    ```yaml
    - item_number: int
      hook: string
      archetype: enum
      platform: enum   # tiktok | instagram | threads
      campaign: enum   # zero | one
      composite_score: int
      topic_id: string | null
      status: draft
      slides:
        - slide: 1
          text:
            headline: string
            subhead: string | null
            bullets: list | null
            body: string | null
          visual_hint: string
      caption: string
      hashtags: list of string
    ```

22. **Check archetype mix balance** against the taxonomy's target percentages.
    Calculate distribution of all backlog items (including locked ones).

23. **If imbalanced:** generate additional items for under-represented
    archetypes. Do not remove existing items.

### Phase 7 — Update campaign-calendar.md

26. **Only adjust timing, not structure.** The campaign calendar's format
    (date, platform, hook, asset, owner) stays the same.

27. **Apply seasonal intelligence** from `niches.<niche>.seasonal_calendar`
    in the memory file. If a topic's `seasonal_relevance` months include
    the current month, move related backlog items earlier in the calendar.
    If a topic is out of season, push it later or note it for the next
    seasonal window.

28. **Do not reschedule items that are already published** (check performance log).

### Phase 8 — Update memory

29. **Update `niche-research-memory.yaml` at `niches.<niche>`:**
    - For every topic added to the backlog, set `used_in_content: true`
      AND set `backlog_item_number` to the item's number in content-backlog.yaml
    - Append a `refresh_runs` entry (per the schema) with: date, mode,
      artifacts_updated, backlog_items_added, mix_balanced, mix_report

### Phase 9 — Run validators

30. **Run the `content-voice-guardrail` skill** on the updated voice.md.
    Pass the full text of voice.md as `voice_guide` and a synthetic test
    draft using the newly added vocabulary as `draft`. If it returns
    `verdict: fail`, review and fix the voice.md changes before proceeding.

31. **Run the `social-post-safety` validator** on the updated
    hashtag-strategy.md. Confirm that per-platform hashtag counts respect
    the limits: Instagram max 8, TikTok max 5, Threads max 3.

### Phase 10 — Validate and output

32. **Run validation:**
    - All updated artifact files exist and are non-empty
    - Content backlog has at least 14 items (existing GTM chain requirement)
    - Every new backlog item has an archetype tag and score
    - Mix report generated and included in output
    - No files were modified outside allowed edit boundaries
    - Voice.md changes are additive only (no removals)
    - content-voice-guardrail passed on updated voice.md
    - social-post-safety passed on updated hashtag-strategy.md

33. **Output the mix report** so the caller can see the archetype distribution
    at a glance.

## Non-goals

- This skill does not perform research. It consumes the brief produced by
  `niche-research-brief`.
- This skill does not generate images or schedule posts.
- This skill does not publish anything to social platforms.
- This skill does not modify the niche research brief (read-only).
- This skill does not append to the performance log (read-only).
