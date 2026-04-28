---
description: Consume an existing founder pack at docs/products/<product_id>/ and produce a 4×6 matrix of candidate app names organized by emotional register × naming archetype, plus a 5-name shortlist that satisfies an archetype-spread rule. Each candidate scored on the canonical 8-dimension rubric. Hard gates auto-reject offensive cross-language collisions, App Store exact-match duplicates, and same-class trademark conflicts. Names only — taglines remain owned by app-store-positioning-pack.
canonical_source: skills/canonical/app-name-discovery/skill.md
---

# App Name Discovery

You are running the app-name-discovery skill from
`skills/canonical/app-name-discovery/skill.md`. Follow the canonical
definition. This adapter mirrors that body and adds Claude-runtime guidance.

## Quick reference

This skill turns a founder pack into a defensible app-name exploration. It
does not pick the name — it produces the matrix, applies hard gates, and
builds a shortlist that spans at least 3 archetypes. The founder picks; the
skill makes the picking honest.

**Prerequisite:** `docs/products/<product_id>/` must contain `founder-brief.md`,
`product-brief.md`, `brand-guidelines.md`, and `competitive-analysis.md`.
Optional: `app-store-positioning.md`. Abort if any required file is missing —
do not guess product context.

**Output:** `docs/products/<product_id>/naming/<YYYY-MM-DD>-candidates.md`.

**Boundaries:** read-only on the founder pack; write only inside
`docs/products/<product_id>/naming/`.

## Steps

### 1. Validate the founder pack and capture reproducibility

- Confirm `docs/products/<product_id>/` exists.
- Read the four required files. Abort with the missing list if any is absent.
- Read the optional positioning doc if present.
- Capture `git rev-parse HEAD` for the output header.
- If `git status --porcelain docs/products/<product_id>/` is non-empty, set
  `dirty: true` in the output front-matter.
- If the dir is not in a git repo, fall back to a SHA-256 over the four
  required files and set `git_sha: null`, `content_hash: <sha>`.

### 2. Synthesize the naming brief

Extract a one-paragraph naming brief from the founder pack covering: what
the product does, who it serves, the brand voice signals, the competitive
name landscape (what archetypes/registers are over-represented vs.
under-served), and any explicit naming constraints. This brief is the
positioning-fit reference for every score in the run.

### 3. Generate the matrix in fixed traversal order

Iterate registers outermost, archetypes innermost. Generate **8 candidates
per cell**, 24 cells total (4 × 6 = 24).

Registers: **Stark · Calm · Sharp · Playful**
Archetypes: **Descriptive · Evocative · Invented · Metaphor · Compound · Lexical**

Cell guidance lives in the canonical skill — read it before generating each
cell. Do not let one register or archetype dominate the run; the fixed order
is a bias-mitigation device.

### 4. Apply hard gates before scoring

- **Cross-language safety.** Reject any candidate that carries an offensive,
  taboo, or absurd meaning in any major language (ES, FR, DE, IT, PT, ZH,
  HI, AR, JA). Auto-reject at score 1/5.
- **App Store exact-match collision.** If a candidate is the exact display
  name of an existing iOS app, auto-reject.
- **Trademark (conditional).** Reject only when the candidate has a 1/5 score
  AND the conflict is in the same class (consumer software). A 2/5 trademark
  score sets `legal_review_required: true` but does NOT reject — adjacent-
  class friction is survivable.

Log every rejection with the candidate, the gate that fired, and a one-
sentence reason. These appear in the Discarded section of the output.

### 5. Score surviving candidates on the 8-dimension rubric

Score each surviving candidate 1–5 on every dimension. Default weights:

| Dimension | Weight |
|---|---|
| memorability | 1.5 |
| pronounceability | 1.0 |
| distinctiveness | 2.0 |
| positioning_fit | 2.0 |
| availability_estimate | 1.0 |
| trademark_risk | 1.0 |
| cross_language_safety | 1.0 |
| app_store_fitness | 1.5 |

Total = `Σ (score_i × weight_i)`. If the caller passed `weight_overrides`,
use those weights and record them in the output front-matter.

`app_store_fitness` covers four sub-signals: the 30-character display limit
(~12 before home-screen truncation), ASO discoverability vs. keyword-stuffing
rejection risk, phonetic uniqueness for Siri / voice search, and icon
coherence at 60pt wordmark.

### 6. Build the shortlist with the spread rule

- Rank surviving candidates by total, descending.
- Take the top 5.
- **Archetype-spread rule:** the shortlist must span at least 3 of the 6
  archetypes. If pure ranking violates that, swap the lowest-scoring duplicate
  archetype member out for the highest-scoring candidate from a missing
  archetype. Repeat until ≥3 archetypes are represented.
- Mark every shortlist row `needs_verification: true` for availability +
  trademark + App Store collision.

### 7. Write the output document

Write to `docs/products/<product_id>/naming/<YYYY-MM-DD>-candidates.md`
following `skills/canonical/app-name-discovery/output-template.md`. The doc
must contain: front-matter (with the reproducibility metadata from step 1),
the naming brief, the shortlist table with verification checklist, the
matrix (all 24 cells), and the Discarded section.

### 8. Validate

- File exists and is non-empty.
- Front-matter has all required fields.
- Shortlist has exactly 5 entries.
- Shortlist spans ≥3 archetypes.
- Matrix has 24 cells.
- No candidate appears in both the matrix and the Discarded list.
- `total_candidates + discarded_count` accounting checks out.

## Boundaries

- **May edit:** `docs/products/<product_id>/naming/*.md`.
- **Must not touch:** `apps/`, `packages/`, `infra/`, `state/`, `products/`,
  any other `docs/products/<product_id>/*` artifact.
- **Read-only:** the founder pack (`founder-brief.md`, `product-brief.md`,
  `brand-guidelines.md`, `competitive-analysis.md`, optional
  `app-store-positioning.md`).
- **Do not** pick the winning name, run live availability lookups, generate
  taglines, or write the chosen name back into the founder pack — those are
  separate operations.
