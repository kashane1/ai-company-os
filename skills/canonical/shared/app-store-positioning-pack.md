---
id: app-store-positioning-pack
name: App Store Positioning Pack
purpose: Turn durable product artifacts into App Store positioning-ready outputs including name direction, subtitle, screenshot story, and metadata angle.
owner_agent: appstore
target_runtimes: [claude]
stage: active
inputs:
  - product-id from infra/products.json
  - existing product artifacts (founder-brief.md, product-brief.md, mvp-spec.md, app-store-positioning.md)
outputs:
  - positioning pack document at state/artifacts/appstore/<product-id>/positioning-pack.md
  - contains: name direction, subtitle candidates, screenshot story, keyword angle, metadata notes
allowed_edit_boundaries:
  - state/artifacts/appstore/
  - docs/products/<product-id>/app-store-positioning.md (update only if gaps found)
forbidden_areas:
  - products/
  - packages/
  - apps/
  - infra/
dependencies:
  - docs/products/<product-id>/founder-brief.md must exist
  - docs/products/<product-id>/product-brief.md must exist
  - docs/products/<product-id>/mvp-spec.md must exist
  - docs/products/<product-id>/app-store-positioning.md must exist
validation_steps:
  - positioning pack document exists at the expected path
  - every section references specific product artifacts as sources
  - no claims exceed what the product actually does (per mvp-spec.md)
  - screenshot story matches real screens from mvp-spec.md
  - name and subtitle candidates respect Apple's character limits (30 chars name, 30 chars subtitle)
handoff_contract:
  what_is_handed_off: positioning pack path with name direction, subtitle candidates, screenshot story, keyword angle, and metadata notes
  handed_to: appstore worker for metadata drafting and submission preparation
claude_adaptation_notes: |
  Claude is a natural fit for this skill — it reads product docs, reasons about
  positioning angles, and produces structured marketing-adjacent output. The
  adapter should enforce brevity and artifact-grounding to prevent generic
  marketing copy.
---

## Instructions

### 1. Load product artifacts

Read `infra/products.json` to find the product's `docs_root`.

Load these artifacts in order (each one grounds the next):

1. `founder-brief.md` — founder's vision, target user, product principles
2. `product-brief.md` — product thesis, value proposition, MVP boundaries
3. `mvp-spec.md` — actual screens, features, acceptance criteria
4. `app-store-positioning.md` — existing positioning direction

### 2. Assess existing positioning

Read `app-store-positioning.md` and check for completeness. The doc may use slightly different section names — match by content, not headings:

- Positioning statement (may be titled "Positioning")
- Category direction (primary and secondary)
- Messaging angle or pillars
- Name direction (existing name candidates)
- Subtitle direction (existing subtitle candidates)
- Screenshot story
- Metadata notes

If any section is missing or thin, note the gap. You may update `app-store-positioning.md` to fill clear gaps, but do not invent product decisions — flag uncertainties.

**If the doc already contains name, subtitle, or screenshot candidates**: use them as a starting point. Refine or extend rather than generating from scratch.

### 3. Generate name direction

Produce 3-5 name candidates. Each must:

- Be 30 characters or fewer
- Reflect the product's core identity (from founder-brief.md)
- Not promise features the product doesn't have (per mvp-spec.md)
- Avoid generic app-store filler words ("ultimate", "pro", "best")

Include a brief rationale for each candidate explaining which product principle it reflects.

### 4. Generate subtitle candidates

Produce 3-5 subtitle candidates. Each must:

- Be 30 characters or fewer
- Complement the name (not repeat it)
- Communicate the primary job-to-be-done (from product-brief.md)
- Be specific enough to differentiate from competitors

**Pairing check**: After generating both names and subtitles, evaluate them as name+subtitle pairs. Flag combinations where a word appears in both (e.g. "Catchbook" + "Private Catch & Spot Log" — "catch" is redundant). Note the strongest 2-3 pairings.

### 5. Build the screenshot story

Using the mvp-spec.md screen list, define an ordered screenshot sequence (typically 6-8 frames):

| Frame | Screen | Caption | What it proves |
|-------|--------|---------|----------------|
| 1     | ...    | ...     | ...            |

Each frame must:
- Reference a real screen from mvp-spec.md
- Have a caption under 40 characters
- Demonstrate a concrete user benefit (not a feature list)
- Follow the narrative arc: hook → core loop → payoff

### 6. Define keyword angle

Based on the product artifacts, identify:

- **Primary keywords** (3-5): terms the target user would search for
- **Secondary keywords** (3-5): related terms for discovery
- **Avoid keywords**: terms that attract the wrong audience

Ground every keyword choice in the founder-brief.md target user description.

### 7. Compile metadata notes

Summarize positioning guidance for the App Store metadata fields:

- **Description angle**: what story to tell in the first 3 lines (above the fold)
- **What's New framing**: how to frame the initial release
- **Promotional text**: seasonal or launch-specific angle (if applicable)
- **Privacy messaging**: what to emphasize given the product's privacy stance

### 8. Produce the positioning pack

Write the complete pack to `state/artifacts/appstore/<product-id>/positioning-pack.md`:

```markdown
# Positioning Pack: <product name>

## Source artifacts
- founder-brief.md: <one-line summary of vision>
- product-brief.md: <one-line summary of thesis>
- mvp-spec.md: <one-line summary of scope>
- app-store-positioning.md: <one-line summary of existing direction>

## Name direction
| Candidate | Rationale |
|-----------|-----------|
| ...       | ...       |

## Subtitle candidates
| Candidate | Complements |
|-----------|-------------|
| ...       | ...         |

## Screenshot story
| Frame | Screen | Caption | Proves |
|-------|--------|---------|--------|
| ...   | ...    | ...     | ...    |

## Keyword angle
- Primary: ...
- Secondary: ...
- Avoid: ...

## Metadata notes
- Description angle: ...
- What's New framing: ...
- Promotional text: ...
- Privacy messaging: ...

## Gaps and uncertainties
- <anything requiring founder input>
```

### 9. Validate

- Document exists and all sections are populated
- Every claim traces to a specific product artifact
- No feature claims exceed mvp-spec.md scope
- Character limits respected for name and subtitle candidates
- Screenshot story references only real screens
