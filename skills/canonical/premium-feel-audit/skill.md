---
id: premium-feel-audit
name: Premium Feel Audit
purpose: Audit a product's current state against `premium-bar.md`, vision, prior polish coverage, fixture knobs, and operator memory; emit a ranked, variety-balanced backlog of `simulator-driven-polish` prompts focused on elevation, not remediation. Read-only counterpart that runs BEFORE polish sessions when the operator's goal is to elevate quality.
owner_agent: ios
target_runtimes: [claude]
stage: active
inputs:
  - product_id (e.g. life-clock)
  - baseline (branch or commit; default origin/main)
  - depth (quick | standard | deep — default standard)
  - focus (optional — motion-only | haptics-only | typography-only | transitions-only | empty-states-only | <free-form>)
  - minimum_prompts (default 10; absolute floor regardless of depth)
outputs:
  - one report file at docs/products/<product-id>/premium-feel-backlog-<YYYY-MM-DD>-<focus-slug>.md
  - 9 binding output sections per shared/recon-scaffolding.md output skeleton, with premium-readiness flag as the readiness flag
allowed_edit_boundaries:
  - docs/products/<product-id>/premium-feel-backlog-*.md (write)
  - skills/adapters/claude/premium-feel-audit.md (read; only edit when explicitly editing the skill itself)
forbidden_areas:
  - products/<product-id>-ios/** (read-only — this skill never edits app sources)
  - packages/policies/
  - state/
  - other products under products/
  - docs/products/<product-id>/premium-bar.md (read-only — operator owns the rubric)
  - docs/products/<product-id>/vision.md (entirely read-only — including Open Questions)
preconditions:
  - docs/products/<product-id>/premium-bar.md exists (REFUSE if missing — operator must author the rubric first; this skill scores against the rubric, it does not invent one)
  - docs/products/<product-id>/vision.md exists
  - skills/canonical/shared/recon-scaffolding.md exists (the shared spine this skill references)
  - docs/products/<product-id>/ contains at least one prior polish-*.md OR ux-audit-*.md (otherwise emit a bootstrap-prompt backlog: "run freeform-polish first to establish baseline")
  - working tree clean OR operator explicitly authorized dirty start
dependencies:
  - canonical/shared/recon-scaffolding (foundational contract — per-prompt template, variety mandate shape, operator-memory pass, output structure, cooling-off rule, anti-patterns)
  - packages/schemas/polish_prompt.py (mechanical schema for the per-prompt template — POLISH_PROMPT_FIELDS)
  - canonical/simulator-driven-polish (this skill's output is consumed by that skill)
  - canonical/simulator-polish-recon (sibling — recon does remedial discovery, this skill does elevation discovery)
  - operator auto-memory at .claude/projects/-Users-simons-ai-company-os/memory/ (mandatory read pass)
validation_steps:
  - report file exists at the expected path with all 9 required sections (per shared/recon-scaffolding.md output skeleton)
  - prompt count >= minimum_prompts AND <= depth ceiling (quick=20, standard=40, deep=60)
  - variety mandate satisfied OR explicit operator override logged in the report
  - per-prompt template adheres to packages/schemas/polish_prompt.py POLISH_PROMPT_FIELDS (9 fields, in order)
  - every emitted prompt cites premium-bar.md + a specific category as evidence
  - no emitted prompt's slug overlaps a session log dated within the last 14 days (cooling-off rule applies cross-skill — polish-*.md, premium-feel-backlog-*.md, pro-value-backlog-*.md)
  - every file path mentioned in any emitted prompt resolves in the worktree
  - coverage matrix has no empty cells (each surface gets at least a "no recent coverage — drift candidate" diagnosis)
  - memory pass was performed and the memory ledger section is present in the report
handoff_contract:
  what_is_handed_off: a dated premium-feel-backlog-*.md file containing N prompts the operator can copy-paste into fresh chats invoking simulator-driven-polish
  handed_to: operator → simulator-driven-polish
  channel: docs/products/<product-id>/premium-feel-backlog-<YYYY-MM-DD>-<focus-slug>.md (the report IS the handoff)
---

# Premium Feel Audit

This skill is the **elevation counterpart** to `simulator-polish-recon`. Recon diffs against *prior polish coverage* and skews remedial. This skill diffs against `premium-bar.md` and produces elevation prompts. A surface that has prior polish coverage may still score badly here — and that's the point. "Polished" is not "premium." Premium is a coherent **system** across motion, haptics, typography, transitions, and microcopy.

This skill is a member of the **recon-family** of audit/backlog skills. The shared contract surface — per-prompt template, variety mandate shape, operator-memory pass, output structure, 14-day cooling-off, anti-patterns — lives in [`skills/canonical/shared/recon-scaffolding.md`](../shared/recon-scaffolding.md). The mechanical per-prompt field set is locked by [`packages/schemas/polish_prompt.py`](../../../packages/schemas/polish_prompt.py). This file defines what makes premium-feel-audit **elevation-specific**: its observer (`premium-bar.md`), its tier vocabulary, its premium-readiness flag.

Use it when:

- The operator says "make the app feel more premium" / "elevate the app" / "premium audit" / "premium-feel audit" / "what would 10x this" / "find premium gaps" / "compare to the bar".
- The app has shipped enough polish that recon is producing thin/remedial backlogs (per operator memory `feedback_simulator_polish_recon_calibration.md`).
- Before a Pro launch, a press push, or any moment where the bar matters more than the regression surface.

Do NOT use it when:

- The operator wants a regression audit — route to `simulator-polish-recon`.
- The operator wants to audit Pro / monetization — route to `pro-value-audit`.
- `premium-bar.md` doesn't exist or is a stub — refuse and ask the operator to author/flesh out the rubric first.
- The operator has a specific fix in mind — route to `simulator-driven-polish` in `fix-list` mode.

## Observer

The observer that distinguishes premium-feel-audit from its siblings is **the diff against `premium-bar.md`**. The skill reads the rubric, walks every surface listed in the rubric's "Surface-level rubric" section, and scores each surface against every category (Motion / Haptics / Typography / Transitions / Empty states / Loading states / Color and lighting / Microcopy).

Read in this order:

### 1. Premium-bar rubric (elevation-specific — this IS the observer)

- `Read` `docs/products/<product-id>/premium-bar.md` in full.
- Extract the binding category list (one section per category).
- Extract the "Surface-level rubric" — the list of surfaces to walk.
- Extract "Anti-signals" — these become elevation-prompt seeds.

### 2. Vision (universal)

Per `shared/recon-scaffolding.md`. Premium-feel-audit must respect vision tone modes and Decided constraints. A prompt that contradicts tone mode constraints escalates to vision-question tier instead.

### 3. Haptics spec (elevation-specific)

- `Read` `docs/products/<product-id>/haptics-spec.md` if present. Used as supplementary observer input for the Haptics category.

### 4. Brand guidelines (elevation-specific)

- `Read` `docs/products/<product-id>/brand-guidelines.md` if present. Used as supplementary observer input for Motion / Typography / Color categories.

### 5. Prior polish coverage (universal)

Per `shared/recon-scaffolding.md`. Cross-skill cooling-off rule applies — check `polish-*.md`, `ux-audit-*.md`, `polish-backlog-*.md`, `premium-feel-backlog-*.md`, `pro-value-backlog-*.md` for 14-day overlaps.

### 6. Surface inventory (universal)

Per `shared/recon-scaffolding.md`. Cross-reference each surface in `premium-bar.md`'s "Surface-level rubric" with the source-tree inventory under `products/<product-id>-ios/Sources/Features/**/*.swift`.

### 7. Fixture knobs (universal)

Per `shared/recon-scaffolding.md`.

### 8. Operator memory pass (universal; mandatory)

Per `shared/recon-scaffolding.md`. Hard refusal on contradiction.

### 9. Per-surface rubric pass (elevation-specific — the core scoring)

For every surface in `premium-bar.md`'s "Surface-level rubric":

- For every category in `premium-bar.md`: score `strong` / `partial` / `weak` / `absent`.
- For every category that scores `weak` or `absent`: draft a category-specific prompt using the tier vocabulary below.

## Coverage matrix (elevation-specific columns)

Every surface in the rubric's "Surface-level rubric" gets a row. Columns:

| Column | Possible values |
|---|---|
| Last polish session | YYYY-MM-DD or "never" |
| Motion | strong / partial / weak / absent |
| Haptics | strong / partial / weak / absent |
| Typography | strong / partial / weak / absent |
| Transitions | strong / partial / weak / absent |
| Empty states | strong / partial / weak / absent |
| Loading states | strong / partial / weak / absent |
| Color and lighting | strong / partial / weak / absent |
| Microcopy | strong / partial / weak / absent |
| Open Questions touching this surface | list of #N references or none |
| Verdict | premium-aligned / premium-gap / motion-incoherence / haptic-thin / typography-drift / transition-snag / empty-state-flat / loading-bare / lighting-gap / microcopy-flab |

A cell that's `weak` or `absent` on any category contributes to the surface's verdict.

## Tier vocabulary (binding — elevation-specific)

| Tier | Meaning | Variety floor (at standard depth) |
|---|---|---|
| `premium-gap` | Surface falls short of the rubric in a named category not covered by a more-specific tier | ≥1 |
| `motion-incoherence` | Animation curves / durations / hierarchy inconsistent across surfaces | — |
| `haptic-thin` | Haptics spec category covered weakly or not at all | — |
| `typography-drift` | Type scale / weight / line-height / Dynamic Type inconsistent | — |
| `transition-snag` | Between-screen coherence broken; flash-of-empty-state on push | — |
| `empty-state-flat` | Empty state present but generic / dead-end / tone-mismatched | — |
| `loading-bare` | Loading state absent / generic spinner / dishonest | — |
| `lighting-gap` | Light+dark parity broken / lighting-convention drift / off-palette hues | — |
| `microcopy-flab` | Copy wordy / tone-mismatched / hedged | — |
| `vision-question` | Premium category not addressed by vision; two valid directions exist | ≥1 |
| `nice-to-have` | Quality-bar improvement with no urgency | — |

## Variety mandate (elevation-specific floors at standard depth)

Per the shape defined in `shared/recon-scaffolding.md`, premium-feel-audit declares these floors at standard depth:

- **≥2 `fix-list`** prompts (concrete premium-gap fixes — single category on a single surface)
- **≥3 `freeform-polish`** prompts (motion / typography / transition / haptic coherence sweeps across multiple surfaces)
- **≥2 `reference-match`** prompts (compare a surface against a named premium reference — App Store competitor, brand asset, or operator-supplied target)
- **≥1 `vision-driven`** prompt (premium that's currently vision-question — e.g., is this app trying to feel "premium minimalist" or "premium dramatic"?)

If `focus` would force the mandate to slip, stop and ask per the shared rule.

## Per-prompt template (inherited)

Use the binding 9-field template defined in [`shared/recon-scaffolding.md`](../shared/recon-scaffolding.md) verbatim. Field names match `packages/schemas/polish_prompt.py` `POLISH_PROMPT_FIELDS`. Every emitted prompt MUST cite `premium-bar.md` + a specific category as its `Evidence` field — generic "premium gap" without rubric reference is invalid.

## Anti-patterns (inherited)

All anti-patterns in `shared/recon-scaffolding.md` apply. Plus elevation-specific:

- Do NOT emit a prompt without naming a `premium-bar.md` category as evidence. "This feels premium-thin" is not an audit finding; "Today fails Motion: animation curves vary across the reveal sequence" is.
- Do NOT introduce a new category not in `premium-bar.md`. If a gap doesn't fit an existing category, escalate to `vision-question` tier and propose the operator add the category to the rubric.
- Do NOT contradict the rubric's "Anti-signals" section. The rubric is the bar; the audit reads it.

## Output structure (inherited; 9 sections)

Use the 9-section structure from `shared/recon-scaffolding.md` verbatim. The readiness flag for this skill is **premium-readiness** — see next section for criteria.

## Premium-readiness flag — strict mode (elevation-specific)

The flag is **green** only if ALL of the following hold:

- Every `premium-bar.md` category has at least one polish session log (under `docs/products/<product-id>/polish-*.md`) covering it in the last 30 days
- Zero unresolved `motion-incoherence` prompts in the emitted backlog
- Zero unresolved `typography-drift` prompts
- Zero unresolved `lighting-gap` prompts
- Every Decided constraint in `vision.md` has at least one polish session log demonstrating premium-bar compliance
- The lifecycle-pinned lighting convention (operator memory `feedback_life_clock_lighting_convention.md` for life-clock) is verifiably applied on every rotating/dial surface

**Yellow** = some categories thin; ≤3 unresolved category-specific tier prompts.
**Red** = ≥3 categories with zero recent coverage OR any `lighting-gap` / `typography-drift` going unaddressed for >30 days.

The flag is stable across sessions — if last week's flag was green and the rubric hasn't changed and no surface regressed, this week's is green.

## Operator interactions

This skill is mostly silent — its output is the report. The two times it should ask:

1. **Variety mandate conflict.** If `focus` would force the mandate to slip, ask before relaxing.
2. **Rubric stub or missing categories.** If `premium-bar.md` exists but reads as stub headers without category content, refuse and ask the operator to flesh it out. The skill is not authorized to invent rubric content.

All other findings flow into the report. The skill does not chat them mid-run.

## Failure modes (elevation-specific)

- **Missing `premium-bar.md`** — refuse with a one-line message routing the operator to author the rubric first. The skill is not authorized to bootstrap a rubric.
- **`premium-bar.md` has only stub headers** — emit a one-prompt bootstrap backlog: "flesh out premium-bar.md before audit can be meaningful."
- **Missing `shared/recon-scaffolding.md`** — refuse; the shared spine is a hard dependency.
- **No prior polish coverage** — emit a 1-prompt backlog: "run `freeform-polish` first to establish a baseline; re-run premium-feel-audit afterward."
- **Memory pass produces a contradiction** — escalate to operator immediately.
- **Operator's intent is regression audit** — route to `simulator-polish-recon`.
- **Operator's intent is monetization audit** — route to `pro-value-audit`.

## Same-day collision rule

Inherited from `shared/recon-scaffolding.md`: append `-2`, `-3`, etc. to the filename slug, not to the date.

## Cadence

Recommended invocation cadence:

- Monthly on main when no surfaces have regressed since last audit
- Before a Pro launch, press push, or App Store featured-app push
- After significant motion / typography / brand-guidelines updates
- When recon is producing thin remedial backlogs (per operator memory)

Do not invoke daily — the 14-day cooling-off rule will produce thin, repetitive backlogs.
