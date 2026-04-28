# Skill: app-name-discovery

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

Consume an existing founder pack at `docs/products/<product_id>/` and produce a
defensible, multi-faceted exploration of candidate app names. Output is a
4 × 6 matrix of candidates organized by emotional register × naming archetype,
each scored against a fixed 8-dimension rubric, plus a shortlist of 5 that
satisfies an archetype-spread rule. The skill does not pick the name — it
makes the picking honest by surfacing the alternatives a founder would
otherwise never see.

Run this skill *after* the founder pack exists (founder-brief, product-brief,
brand-guidelines, competitive-analysis, optional positioning doc) and *before*
App Store metadata is locked in. Taglines remain owned by
`app-store-positioning-pack`; this skill emits names only.

## Contract

Inputs:

- `product_id`: string — product identifier matching a directory under
  `docs/products/`.

Outputs:

- `candidates_path`: string — path to
  `docs/products/<product_id>/naming/<YYYY-MM-DD>-candidates.md`.
- `shortlist_count`: int — always 5.
- `total_candidates`: int — count of candidates that survived the hard gates
  and entered the matrix (≤ 192).
- `discarded_count`: int — count auto-rejected by hard gates.
- `archetype_count`: int — always 6 in this version.
- `register_count`: int — always 4 in this version.

## Allowed edit boundaries

- `docs/products/<product_id>/naming/*.md`

## Forbidden areas

- `apps/`
- `packages/`
- `infra/`
- `state/`
- `products/`

The skill must not read or write any other artifact under
`docs/products/<product_id>/` — the founder pack is read-only input.

## Dependencies

- `docs/products/<product_id>/founder-brief.md` (read-only, required)
- `docs/products/<product_id>/product-brief.md` (read-only, required)
- `docs/products/<product_id>/brand-guidelines.md` (read-only, required)
- `docs/products/<product_id>/competitive-analysis.md` (read-only, required)
- `docs/products/<product_id>/app-store-positioning.md` (read-only, optional)
- Git CLI (for capturing the founder-pack SHA)

## Instructions

### Phase 0 — Load and validate the founder pack

1. **Confirm product directory exists** at `docs/products/<product_id>/`. If
   not, abort with the missing path.
2. **Load the four required files.** If any are missing, abort with the full
   list of missing paths — do not guess product context.
3. **Load optional positioning doc** if present.
4. **Capture reproducibility metadata:**
   - Git SHA of `HEAD` at the time of the run.
   - Path to the product directory.
   - If `git status --porcelain docs/products/<product_id>/` is non-empty,
     mark `dirty: true` for the output header.

### Phase 1 — Synthesize the naming brief

5. **Extract from the founder pack** a one-paragraph naming brief covering:
   - What the product does (one sentence).
   - Who it serves (target user / archetype).
   - Tone and brand voice signals from `brand-guidelines.md`.
   - Competitive name landscape from `competitive-analysis.md` — what
     archetypes and registers are over-represented (avoid) vs. under-served
     (favor).
   - Any explicit naming constraints in the founder brief or positioning
     doc.

This brief is the positioning-fit reference for the rest of the run. Do not
proceed without it.

### Phase 2 — Generate the matrix (per cell, in fixed order)

6. **Generate candidates per cell** in this fixed traversal order to prevent
   archetype-bias. Iterate registers outermost, archetypes innermost:

   Registers (4): Stark · Calm · Sharp · Playful
   Archetypes (6): Descriptive · Evocative · Invented · Metaphor · Compound · Lexical

   For each of the 24 cells, generate **8 candidate names** that fit both
   the register's emotional voice and the archetype's linguistic strategy.

   Cell guidance:

   - **Stark** — confronting, slightly heavy. Memento mori-adjacent.
   - **Calm** — gentle, journaling-adjacent, sustainable for daily opens.
   - **Sharp** — productivity-coded, drives action, motivating.
   - **Playful** — friendly, warm, lowers stakes so people use it.

   - **Descriptive** — says what it is (Salesforce, JetBlue).
   - **Evocative** — suggests a feeling or domain (Patagonia, Amazon).
   - **Invented** — coined word with no prior meaning (Spotify, Kodak).
   - **Metaphor** — borrows an unrelated concept (Apple, Oracle).
   - **Compound / Portmanteau** — two parts fused (Pinterest, Instagram).
   - **Lexical / Real-word** — one common word repurposed (Slack, Square, Block).

### Phase 3 — Apply hard gates (auto-reject before scoring)

7. **Cross-language safety hard gate.** For every candidate, evaluate:
   does the name carry an offensive, taboo, or absurd meaning in any of
   the major languages (Spanish, French, German, Italian, Portuguese,
   Mandarin, Hindi, Arabic, Japanese)? If yes, score 1/5 and **auto-reject
   before the matrix.** Reason: Chevy-Nova-class disasters auto-reject.

8. **App Store exact-match collision hard gate.** If a candidate is the
   exact display name of an existing iOS app and the founder is targeting
   iOS, auto-reject. Apple won't approve duplicates. (Note: this is
   estimated from common-knowledge plus founder-pack signals; the
   shortlist still gets `needs_verification: true` regardless.)

9. **Trademark hard gate (conditional).** A 1/5 trademark score
   auto-rejects **only for same-class conflicts** (consumer software vs.
   another consumer software product). A 2/5 score does **not** auto-reject;
   instead, mark the candidate `legal_review_required: true` and let it
   continue to the matrix. Adjacent-class friction is survivable; legal
   review is the right next step, not rejection.

10. **Log every rejection** with the candidate name, gate fired, and a one-
    sentence reason. These appear in the Discarded section of the output.

### Phase 4 — Score surviving candidates on the 8-dimension rubric

11. **Score each surviving candidate** on all 8 dimensions, integer 1–5:

    | Dimension | Default weight | Notes |
    |---|---|---|
    | `memorability` | 1.5 | Sticks after one exposure? |
    | `pronounceability` | 1.0 | Easy to say without hesitation? |
    | `distinctiveness` | 2.0 | Distinct names *become* memorable; the inverse is not true. |
    | `positioning_fit` | 2.0 | Matches the founder pack — the heaviest dimension. |
    | `availability_estimate` | 1.0 | Estimated risk that name is taken (App Store, domain). |
    | `trademark_risk` | 1.0 | Estimated. Hard gate at 1 only for same-class. |
    | `cross_language_safety` | 1.0 | Already a hard gate at 1; otherwise just a score. |
    | `app_store_fitness` | 1.5 | 30-char display limit (~12 before truncation), ASO discoverability vs. keyword-stuffing rejection risk, phonetic uniqueness for Siri / voice search, icon coherence at 60pt wordmark. |

12. **Compute total** as the weighted sum: `Σ (score_i × weight_i)`.

### Phase 5 — Build the shortlist with the spread rule

13. **Rank all surviving candidates by total score, descending.**
14. **Take the top 5.** This is the candidate shortlist.
15. **Apply the archetype-spread rule:** the shortlist must contain
    candidates from **at least 3 of the 6 archetypes.** If pure ranking
    yields a shortlist with fewer than 3 archetypes represented:
    - Identify the two highest-scoring archetypes already in the shortlist
      and the lowest-scoring shortlist member among them.
    - Swap that lowest-scoring member out for the highest-scoring candidate
      from a missing archetype.
    - Repeat until the shortlist spans ≥3 archetypes.
16. **Mark every shortlist row** `needs_verification: true` for
    availability + trademark + App Store collision — the founder runs the
    actual lookups, not the skill.

### Phase 6 — Write the output

17. **Write** to `docs/products/<product_id>/naming/<YYYY-MM-DD>-candidates.md`
    using the structure in `output-template.md`. The output must include:

    - YAML front-matter: `product_id`, `generated_at`, `founder_pack_git_sha`,
      `founder_pack_path`, optional `dirty: true`, `archetype_count` (6),
      `register_count` (4), `total_candidates`, `discarded_count`.
    - **Naming brief** synthesized in Phase 1 (one paragraph).
    - **Shortlist (5)** — table of name / archetype / register / total /
      `needs_verification` / per-dimension score breakdown / one-line
      rationale tied to the founder pack.
    - **Matrix** — 24 cells, each headed `### <Register> × <Archetype>`,
      each containing 8 candidates with per-dimension scores and total.
    - **Discarded** — every auto-rejected candidate with the gate that
      fired and a one-sentence reason.

### Phase 7 — Validate

18. Shortlist has exactly 5 entries.
19. Shortlist spans at least 3 distinct archetypes.
20. Matrix has 24 cells (4 registers × 6 archetypes).
21. Every shortlist entry has `needs_verification: true`.

## Failure modes

- **Founder pack incomplete** — abort listing the missing files. Do not
  guess context from a one-line description.
- **All candidates in a cell hard-gated** — the cell may be empty in the
  matrix; report it explicitly. The shortlist spread rule still applies
  across surviving cells.
- **Shortlist would have <3 archetypes even after swaps** — rare; means
  generation collapsed. Report as a generation-quality failure and ask the
  caller to re-run with broader prompting.
- **Founder-pack git SHA capture fails** (e.g. dir is not in a git repo) —
  abort with a clear error. The skill assumes the product directory lives
  in a git tree; reproducibility metadata depends on it.

## Non-goals

- This skill does not pick the winning name. The founder picks.
- This skill does not run live availability lookups (App Store search,
  USPTO, domain WHOIS). Those are flagged on the shortlist for manual
  verification.
- This skill does not generate taglines, brand voice docs, or App Store
  copy. Those belong to `app-store-positioning-pack`.
- This skill does not write the chosen name back into the founder pack.
  That is a separate operation owned by the founder workflow.
