---
title: Fork simulator-polish-recon into premium-feel-audit and pro-value-audit sibling skills
type: feat
status: active
date: 2026-05-12
origin: in-chat audit conversation 2026-05-12 (no brainstorm doc — origin is the capability-audit reply that established Option B as the chosen path)
---

# Fork simulator-polish-recon into premium-feel-audit and pro-value-audit sibling skills

## Overview

The Life Clock product is approaching submission-readiness and the operator's vague-but-strategic prompts ("make the app feel more premium," "make Pro stand out and provide value") have no dedicated routing today. The existing `simulator-polish-recon` skill is the closest fit, but its observer diffs against *prior polish coverage* — which is exactly why operator memory entry `feedback_simulator_polish_recon_calibration.md` already captured: *"recon on a polished product skews remedial; pivot to brainstorming when the operator wants to elevate the app, not just stop regressions."*

This plan ships **Option B** from the in-chat audit (2026-05-12): extract the truly shared scaffolding from `simulator-polish-recon` into `skills/canonical/shared/recon-scaffolding.md`, then fork two sibling skills (`premium-feel-audit`, `pro-value-audit`) that reuse the spine and swap only the **observer** and **tier vocabulary**. Both siblings emit prompts in the exact format `simulator-driven-polish` already consumes — **zero glue code** in the polish loop.

Ships as a single PR with **four** significant commits (revised from six during the 2026-05-12 deepening pass — see "Deepening Review Findings" below) so review is incremental and any commit can be reverted independently if reconciliation fails.

> **Deepening pass run 2026-05-12.** Six parallel agents reviewed this plan (architecture-strategist, code-simplicity-reviewer, pattern-recognition-specialist, learnings-researcher, git-history-analyzer, repo-research-analyst). Findings are at the end of this doc under "Deepening Review Findings (2026-05-12)." Material revisions are flagged in the affected sections with `[REVISED 2026-05-12]` callouts. The body content below is the original plan; the deepening section is the binding follow-up.

## Problem Statement

### The capability gap

Two recurring operator prompts have no first-class skill path:

1. **"Make the app feel more premium."** Today this routes to `simulator-driven-polish` in `vision-driven` mode. The skill works but the iteration cap is 6 and the decision tiers bias toward in-session fixes, not toward emitting a *backlog* of premium-elevation prompts. There is no skill that proactively scores motion / haptics / typography / transitions as a coherent system against a target premium bar.
2. **"Make Pro features stand out and provide value."** Today there is no skill at all. The operator must reason ad-hoc over `MONETIZATION.md`'s Free/Pro rule, the paywall implementation, and Pro-gated surfaces. `MVP_VS_FOUNDER_PACK_AUDIT_2026-04-28.md` exists as a one-off audit precedent but is not a repeatable skill.

### Why recon is the right backbone

`simulator-polish-recon` already encodes 80% of what these audits need:

- 8-step evidence stack (binding read order)
- 9-section output schema (state-summary, coverage matrix, open-questions ledger, memory ledger, fixture-knob catalog, prompts, variety check, recommended sequencing, readiness flag)
- Per-prompt template with 9 binding fields, identical to what `simulator-driven-polish` consumes
- 14-day cooling-off rule
- Mandatory operator-memory pass with hard-refusal on contradiction
- Variety mandate (≥N prompts per mode/tier)
- Anti-patterns block

The *only* thing the siblings change is **what the coverage matrix scores against** and **which tier vocabulary populates the prompts.** Recon today scores against "diff vs prior coverage." Premium scores against `premium-bar.md`. Pro-value scores against `MONETIZATION.md`'s Free/Pro rule + paywall implementation.

### Why fork (not edit in place)

Three options were considered in the audit conversation:

- **Option A — Edit recon in place, add `focus: elevation` and `focus: pro-value`.** Rejected: the skill body is already 273 lines; mixing remedial and elevation framings risks the elevation mode getting silently overridden by remedial defaults — the exact failure mode operator memory already warned about.
- **Option B — Fork into siblings after extracting shared spine.** **Chosen.** Matches the existing sibling pattern (`ios-simulator-ux-audit` and `simulator-polish-recon` already share scaffolding by convention and differ only in observer). Crisp separation. Per-sibling fixture surfaces narrow and stable.
- **Option C — Add rubric docs only; let `simulator-driven-polish` in `vision-driven` mode do everything.** Rejected: loses the breadth-first read-only discovery pass that is the whole point of recon. For vague prompts like "make Pro stand out," the operator needs 10–40 candidate prompts before committing to in-session edits.

## Proposed Solution

Six commits, all in one PR, sequenced so any commit can be reverted without breaking the build or the `test_skill_reconciliation.py` hard gate:

1. **Extract shared scaffolding** — new `skills/canonical/shared/recon-scaffolding.md`; slim `simulator-polish-recon/skill.md` to reference it. Adapter updated. No-behavior-change refactor.
2. **Add `docs/products/life-clock/premium-bar.md`** — observer rubric for `premium-feel-audit`.
3. **Add `docs/products/life-clock/pro-value-rule.md`** — observer rubric for `pro-value-audit`.
4. **Add `premium-feel-audit`** — canonical + claude adapter + registry entry + fixture + `.claude/skills/` pointer + reconciliation test.
5. **Add `pro-value-audit`** — same five surfaces.
6. **Update routing docs** — `docs/skills-index.md` trigger phrases; verify `CLAUDE.md` needs no edit (it points to skills-index already).

## Technical Approach

### Architecture

The shared spine lives in one flat-file canonical doc (matches the `app-store-positioning-pack.md` and `repo-sync.md` pattern in `skills/canonical/shared/`). It is **referenced**, not **imported** — skill bodies cite specific sections by anchor. This keeps each sibling skill body coherent on its own while eliminating the multi-hundred-line duplication.

```
skills/canonical/shared/recon-scaffolding.md         # NEW — shared spine
skills/canonical/simulator-polish-recon/skill.md     # MODIFIED — slimmed
skills/canonical/premium-feel-audit/                 # NEW
  ├── skill.md
  └── fixtures/
      └── happy_path.yaml
skills/canonical/pro-value-audit/                    # NEW
  ├── skill.md
  └── fixtures/
      └── happy_path.yaml
skills/adapters/claude/simulator-polish-recon.md     # MODIFIED — slimmed
skills/adapters/claude/premium-feel-audit.md         # NEW
skills/adapters/claude/pro-value-audit.md            # NEW
skills/registry.yaml                                  # MODIFIED — 2 new entries
.claude/skills/premium-feel-audit.md                 # NEW — pointer
.claude/skills/pro-value-audit.md                    # NEW — pointer
docs/products/life-clock/premium-bar.md              # NEW — observer rubric
docs/products/life-clock/pro-value-rule.md           # NEW — observer rubric
docs/skills-index.md                                  # MODIFIED — trigger phrases
tests/python/unit/test_premium_feel_audit_fixtures.py # NEW
tests/python/unit/test_pro_value_audit_fixtures.py    # NEW
```

### What goes into `shared/recon-scaffolding.md` vs stays per-skill

**Shared (universal):**

- Per-prompt template (the 9 binding fields, in order — exact schema `simulator-driven-polish` consumes)
- Variety mandate language (the *idea* of floors; per-skill specifies the numbers)
- 14-day cooling-off rule
- Operator-memory pass + hard-refusal on contradiction
- Output skeleton (9-section structure with names; per-skill fills the criteria)
- Cadence guidance template
- Anti-patterns block (the generic ones: no editing outside boundary, no Feature-tier hidden as fix-list, no evidence-free prompts, no skipping memory pass)
- Evidence-stack universal steps: branch survey, vision read, prior polish coverage, surface inventory, operator memory

**Per-skill (sibling-specific):**

- The observer (what to diff against)
- Tier vocabulary
- Variety floor numbers
- Readiness-flag criteria (submission-readiness, premium-readiness, pro-value-readiness)
- Observer-specific evidence-stack steps (e.g., `premium-feel-audit` reads `premium-bar.md` + `haptics-spec.md`; `pro-value-audit` reads `MONETIZATION.md` + every Paywall/Pro-gated surface)
- Skill-specific failure modes
- Allowed-edit boundaries + forbidden areas

### Implementation Phases

#### Phase 1 — Commit 1: Extract shared scaffolding (no-behavior-change refactor)

**Goal:** lift the universal contract surface into `shared/recon-scaffolding.md`; slim recon to its observer-specific bits; keep all current recon behavior intact.

**Files created:**

- `skills/canonical/shared/recon-scaffolding.md`

**Files modified:**

- `skills/canonical/simulator-polish-recon/skill.md` (slim from ~273 → ~150 lines; replace lifted sections with cross-references to the shared doc by named anchor)
- `skills/adapters/claude/simulator-polish-recon.md` (update "Tools to reach for" and "Quality checks" sections to cite shared/recon-scaffolding.md where applicable; recon's depth ceilings and submission-readiness flag stay in the adapter)

**Validation:**

- `simulator-polish-recon` has `fixture_status: missing` today, so no fixture regression risk
- Adapter quality-check enumerations still match the slimmed canonical body
- All cross-references resolve (file path + heading anchor exists)
- `test_skill_reconciliation.py` still passes (recon was not in the passing set; new shared doc is not a skill)

**Risk callout:** the shared doc must not become a place where the per-prompt template can drift from what `simulator-driven-polish` consumes. The template is **binding** for both producer (recon/siblings) and consumer (polish). The shared doc carries an explicit annotation: "If you edit the per-prompt template, you MUST also update `skills/canonical/simulator-driven-polish/skill.md` consumption logic and bump the consumer-contract version comment in both files."

**Recommended stretch (NOT in this PR scope unless trivial):** add a contract-freeze fixture for `simulator-polish-recon` at `skills/canonical/simulator-polish-recon/fixtures/happy_path.yaml` that pins the depth ceilings (20/40/60), variety mandate floors, 14-day cooling-off rule, and submission-readiness strict criteria. This was already flagged as "v1.1 follow-up" in the registry comment. Adding it now would protect the slimmed canonical body. Leaving it out is acceptable because the registry entry still says `fixture_status: missing`. **Decision deferred to /workflows:work.**

#### Phase 2 — Commit 2: Add `docs/products/life-clock/premium-bar.md`

**Goal:** define the observer rubric `premium-feel-audit` will score against. This is product-scoped (lives under `docs/products/life-clock/`) even though the audit skill is generic. Future products will get their own `premium-bar.md`; the skill defaults to `docs/products/<product-id>/premium-bar.md`.

**Contents (binding sections — fixture will lock these):**

```markdown
# Life Clock Premium Bar

## Why this doc exists
[Where the rubric came from; how it stays current.]

## The signals (binding categories)
### Motion
- Animation curves, durations, hierarchy across surfaces
- "Premium" means coherent timing across screens, not one-off bursts

### Haptics
- Density, semantic correctness, integration with motion
- Cross-reference: haptics-spec.md

### Typography
- Scale, weight hierarchy, line-height
- One typographic system across surfaces

### Transitions
- Between-screen coherence
- Return-to-state preservation
- No flash-of-empty-state on push/pop

### Empty states
- Quality, copy specificity, no dead-ends

### Loading states
- Present, on-brand, not generic spinners

### Color and lighting
- Light + dark parity
- Lifecycle-pinned lighting convention (cross-reference: operator memory `feedback_life_clock_lighting_convention.md`)

### Microcopy
- Density, voice, tone-mode coherence

## Surface-level rubric
[For each surface, what "premium" means in context. References vision.md tone.]

## Anti-signals (what is NOT premium)
[Generic spinners, mismatched corner radii, copy that's chatty when the tone says terse, etc.]

## Cadence
[How often this rubric should be re-read by audits; how it evolves.]
```

**Validation:**

- File parses as valid markdown
- All cross-references resolve (haptics-spec.md, vision.md, operator memory paths)
- Sections match what `premium-feel-audit`'s fixture will lock as `required_observer_signals`

#### Phase 3 — Commit 3: Add `docs/products/life-clock/pro-value-rule.md`

**Goal:** define the observer rubric `pro-value-audit` will score against. Codifies `MONETIZATION.md`'s "Free = understanding, Pro = depth/archive/correction" rule into auditable criteria.

**Contents (binding sections — fixture will lock these):**

```markdown
# Life Clock Pro-Value Rule

## Source of truth
[Pointer to MONETIZATION.md; this doc is the operational rubric for audits.]

## The Free/Pro rule (verbatim from MONETIZATION.md)
- Free = understanding
- Pro = depth, archive, and correction power
[+ the four practical tests]

## Audit criteria (binding categories)
### Discoverability
- Where is Pro signaled in the app?
- Is signaling consistent across surfaces or ad-hoc?

### Justification
- Does every Pro gate have a "why this is Pro" answer the user can read?
- Is justification copy concrete or generic?

### Perceived depth
- Do Pro surfaces feel substantively deeper than Free?
- Or does Pro feel like Free behind a wall?

### Friction-to-trial
- How many taps from Today → trying Pro?
- Is there preview value before commit?

### Upsell moments
- Where in the daily loop is Pro shown?
- Best moments per MONETIZATION.md: after first Life Clock reveal, after tapping locked detail
- Are those moments actually used in the implementation?

### Trust
- No dark patterns
- Clear cancel path
- Restore path works (cross-reference: operator memory `feedback_life_clock_subscription_lifecycle.md` if present, otherwise the polish log)

### Value-claim accuracy
- Does paywall copy promise what Pro actually delivers?
- Cross-reference: every Pro-gated surface listed below

## Pro touchpoint inventory
[List every Pro-gated surface in Life Clock today. Updated as Pro grows.]

## Anti-signals (what is NOT good Pro value)
[Surprise charges, hidden cancel, generic "Pro" copy without specifics, Pro that gates the first meaningful answer — explicitly forbidden by MONETIZATION.md.]
```

**Validation:**

- File parses as valid markdown
- Cross-references resolve (MONETIZATION.md, Paywall source, operator memory)
- Sections match what `pro-value-audit`'s fixture will lock

#### Phase 4 — Commit 4: `premium-feel-audit` skill (all five surfaces)

**Files created:**

- `skills/canonical/premium-feel-audit/skill.md`
- `skills/canonical/premium-feel-audit/fixtures/happy_path.yaml`
- `skills/adapters/claude/premium-feel-audit.md`
- `.claude/skills/premium-feel-audit.md`
- `tests/python/unit/test_premium_feel_audit_fixtures.py`

**Files modified:**

- `skills/registry.yaml` (new entry, fixture_status: passing)

**Canonical skill structure (binding):**

```markdown
---
id: premium-feel-audit
name: Premium Feel Audit
purpose: Audit a product's current state against premium-bar.md, vision, prior polish coverage, fixture knobs, and operator memory; emit a ranked, variety-balanced backlog of `simulator-driven-polish` prompts focused on elevation, not remediation. Read-only counterpart that runs BEFORE polish sessions when the operator's goal is to elevate quality, not stop regressions.
owner_agent: ios
target_runtimes: [claude]
stage: active
inputs:
  - product_id (e.g. life-clock)
  - baseline (branch or commit; default origin/main)
  - depth (quick | standard | deep — default standard)
  - focus (optional — motion-only | haptics-only | typography-only | transitions-only | empty-states-only | <free-form>)
  - minimum_prompts (default 10)
outputs:
  - one report file at docs/products/<product-id>/premium-feel-backlog-<YYYY-MM-DD>-<focus-slug>.md
  - sections defined by shared/recon-scaffolding.md output skeleton, with premium-readiness flag replacing submission-readiness
allowed_edit_boundaries: ...
forbidden_areas: ...
preconditions:
  - docs/products/<product-id>/premium-bar.md exists (REFUSE if missing — operator must author rubric first)
  - docs/products/<product-id>/vision.md exists
  - shared/recon-scaffolding.md exists
  - at least one prior polish-*.md or ux-audit-*.md log (otherwise emit bootstrap backlog)
dependencies:
  - canonical/shared/recon-scaffolding (foundational contract)
  - canonical/simulator-driven-polish (consumer of emitted prompts)
---

# Premium Feel Audit

This skill is a sibling of `simulator-polish-recon`. Both share the spine in
`skills/canonical/shared/recon-scaffolding.md`. They differ only in observer
and tier vocabulary.

## Observer
Read in this order:
1. docs/products/<product-id>/premium-bar.md (the rubric)
2. docs/products/<product-id>/vision.md (tone + decided constraints)
3. docs/products/<product-id>/haptics-spec.md (if present)
[then proceed through shared/recon-scaffolding.md evidence stack steps]

## Tier vocabulary (binding)
- premium-gap — surface falls short of the rubric in a named category
- motion-incoherence — animation curves/timing inconsistent across surfaces
- haptic-thin — haptic-spec category covered weakly or not at all
- typography-drift — scale/weight/hierarchy inconsistent
- transition-snag — between-screen coherence broken
- empty-state-flat — empty state present but generic
- nice-to-have — improvements with no urgency

## Variety mandate (sibling-specific)
- ≥2 fix-list prompts (concrete premium-gap fixes)
- ≥3 freeform-polish prompts (motion / typography / transition coherence sweeps)
- ≥2 reference-match prompts (compare a surface against a named premium reference)
- ≥1 vision-driven prompt (premium that's currently vision-question — e.g. is this app trying to feel "premium minimalist" or "premium dramatic"?)

## Premium-readiness flag
- green: every premium-bar category has ≥1 polish log covering it in the last 30 days AND no open premium-gap prompts in the emitted backlog
- yellow: some categories thin
- red: ≥3 categories with zero recent coverage

## Failure modes
- premium-bar.md missing → refuse, route operator to author rubric first
- premium-bar.md has only stub headers → emit one-prompt bootstrap "flesh out premium-bar.md before audit can be meaningful"
- [+ inherit shared failure modes]

[+ inherit shared recon-scaffolding.md anti-patterns, per-prompt template,
operator-memory pass, 14-day cooling-off, output skeleton]
```

**Adapter** (`skills/adapters/claude/premium-feel-audit.md`):

Mirrors the structure of `skills/adapters/claude/simulator-polish-recon.md`:

- Confirm-before-start input enumeration
- Pre-flight checks (premium-bar.md exists, vision.md exists, prior coverage exists)
- Tools-to-reach-for ordered by canonical evidence stack
- Single-pass rhythm (recon-style, not loop-style)
- Tier reminders for what consuming simulator-driven-polish will do
- Quality checks before writing the report
- What to surface in reply (under 30 lines)
- Failure modes specific to Claude

**Fixture** (`skills/canonical/premium-feel-audit/fixtures/happy_path.yaml`):

```yaml
- name: happy_path
  description: Canonical body still exposes the premium-feel-audit contract.
  input:
    skill_file: canonical/premium-feel-audit/skill.md
  expected:
    required_section_headings:
      - "## Observer"
      - "## Tier vocabulary (binding)"
      - "## Variety mandate (sibling-specific)"
      - "## Premium-readiness flag"
      - "## Failure modes"
    required_input_fields:
      - "product_id"
      - "baseline"
      - "depth"
      - "focus"
      - "minimum_prompts"
    required_preconditions:
      - "docs/products/<product-id>/premium-bar.md exists"
      - "docs/products/<product-id>/vision.md exists"
      - "shared/recon-scaffolding.md exists"
    required_tier_vocabulary:
      - "premium-gap"
      - "motion-incoherence"
      - "haptic-thin"
      - "typography-drift"
      - "transition-snag"
      - "empty-state-flat"
      - "nice-to-have"
    required_variety_floors:
      fix_list: 2
      freeform_polish: 3
      reference_match: 2
      vision_driven: 1
    required_observer_inputs:
      - "premium-bar.md"
      - "vision.md"
      - "haptics-spec.md"
    required_failure_modes:
      - "premium-bar.md missing"
      - "premium-bar.md has only stub headers"
    required_readiness_flag: "premium-readiness"
    required_handoff_channel: "docs/products/<product-id>/premium-feel-backlog-<YYYY-MM-DD>-<focus-slug>.md"
    references_shared_scaffolding: true
```

**Registry entry:**

```yaml
- id: premium-feel-audit
  name: Premium Feel Audit
  path: canonical/premium-feel-audit/skill.md
  owner_agent: ios
  target_runtimes: [claude]
  stage: active
  kind: agentic
  fixture_status: passing
  source: internal
  adapters:
    claude: adapters/claude/premium-feel-audit.md
  project_skill: .claude/skills/premium-feel-audit.md
```

**Reconciliation test** (`tests/python/unit/test_premium_feel_audit_fixtures.py`):

Pattern-match `test_ios_simulator_ux_audit_fixtures.py`. Asserts the fixture's `expected.required_section_headings` are all present in the canonical body; same for `required_tier_vocabulary`, `required_preconditions`, `required_failure_modes`. Belt-and-suspenders alongside the shared reconciliation test.

#### Phase 5 — Commit 5: `pro-value-audit` skill (all five surfaces)

Symmetric with Phase 4 but observer is `pro-value-rule.md` and tier vocabulary is pro-value-specific.

**Canonical skill differences:**

- Observer reads: `pro-value-rule.md` (rubric) → `MONETIZATION.md` (source) → `vision.md` (tone constraints) → every Paywall source file + every Pro-gated surface inventory
- Tier vocabulary: `pro-thin` (Pro surface feels shallow), `pro-invisible` (Pro exists but isn't signaled), `upsell-missed` (loop moment isn't used per MONETIZATION.md), `value-claim-unjustified` (paywall copy promises X, app delivers Y), `friction-too-high` (too many taps to try Pro), `trust-gap` (dark pattern or unclear cancel), `nice-to-have`
- Variety floors: ≥3 fix-list (most pro-value findings are concrete), ≥2 freeform-polish, ≥1 reference-match (compare paywall against a named premium SaaS), ≥1 vision-driven (Pro positioning questions that touch vision)
- Pro-value-readiness flag: green when every Pro touchpoint has discoverability + justification + value-claim coverage in recent polish logs AND no open `value-claim-unjustified` or `trust-gap` prompts; yellow / red otherwise

**Failure modes:**

- `pro-value-rule.md` missing → refuse
- `MONETIZATION.md` missing → refuse
- Pro touchpoint inventory in rubric is empty → emit bootstrap "inventory Pro touchpoints first"
- Inherit shared failure modes

#### Phase 6 — Commit 6: Routing docs

**Files modified:**

- `docs/skills-index.md`
- `CLAUDE.md` (verify only — likely no change since it points to skills-index)

**`docs/skills-index.md` additions:**

In "Available Claude project skills" list:

```markdown
- **premium-feel-audit** — discovery counterpart to `simulator-driven-polish` focused on elevation, not remediation. Read-only audit against `premium-bar.md` rubric. Emits a backlog of prompts targeting motion / haptics / typography / transition coherence.
- **pro-value-audit** — discovery counterpart focused on Pro discoverability, justification, perceived depth, and value-claim accuracy. Read-only audit against `pro-value-rule.md` rubric (which operationalizes `MONETIZATION.md`'s Free/Pro rule). Emits a backlog of paywall + Pro-touchpoint prompts.
```

In "Trigger phrases → skills":

```markdown
- "make it feel premium" / "elevate the app" / "premium audit" / "what would 10x this" / "find premium gaps" / "compare to the bar" / "premium-feel audit" → `skills/adapters/claude/premium-feel-audit.md`
- "audit Pro value" / "make Pro stand out" / "where is Pro thin" / "Pro feels weak" / "audit the paywall" / "audit Pro discoverability" / "pro-value audit" → `skills/adapters/claude/pro-value-audit.md`
```

**Disambiguation rule (binding) callout:** the trigger phrases for these two skills, `simulator-polish-recon`, and `simulator-driven-polish` overlap in spirit ("audit the app" → all of them might apply). Add an explicit disambiguation note to `docs/skills-index.md`:

> When a request is ambiguous between `simulator-polish-recon` (remedial), `premium-feel-audit` (elevation), `pro-value-audit` (monetization), and `simulator-driven-polish` (editing in-session) — ASK before routing. The user-intent split is: "what regressed or what's incomplete" (recon) vs "what would feel more premium" (premium-feel-audit) vs "where does Pro fall short" (pro-value-audit) vs "let's fix things live" (simulator-driven-polish).

**CLAUDE.md verification:** the file currently delegates trigger-phrase routing to `docs/skills-index.md`. The skill catalog list there mentions categories but not individual skills. **Decision:** no edit needed to CLAUDE.md unless verification step finds an inline trigger list. If found, mirror the new entries.

## Alternative Approaches Considered

### A — Edit `simulator-polish-recon` in place

Add two new values to the existing `focus` parameter (`elevation`, `pro-value`). Add corresponding tier vocabulary, variety mandate updates, and readiness flag variants inside the existing skill body.

**Rejected because:**

- Skill body already 273 lines; mixing remedial and elevation framings risks the elevation mode getting silently overridden by remedial defaults (operator memory `feedback_simulator_polish_recon_calibration.md` warned about this exact failure mode)
- Contract-freeze fixture (when eventually added) would become noisy and brittle
- Disambiguation between focus modes becomes harder, not easier, for the agent

### C — Rubric docs only, no new skills

Add `premium-bar.md` and `pro-value-rule.md`, drop them into `docs/products/life-clock/`, run `simulator-driven-polish` in `vision-driven` mode with the rubric injected as a pre-read.

**Rejected because:**

- Vision-driven mode's iteration cap is 6 and its tiers bias toward in-session fixes
- Loses the breadth-first read-only discovery pass that is the whole point of recon (operator gets a backlog of 10–40 candidates before committing to in-session edits)
- For vague prompts like "make Pro stand out," there is no agent path that surfaces *where* Pro is thin across the entire app — the polish skill would only see the screens it happens to drive

### D — Single unified `elevation-audit` skill with rubric selector

One sibling skill that accepts a `rubric` parameter pointing to either `premium-bar.md` or `pro-value-rule.md`.

**Rejected because:**

- Tier vocabularies are genuinely different (motion-incoherence ≠ value-claim-unjustified)
- Variety floors differ (premium needs reference-match floor; pro-value needs fix-list floor)
- Failure modes differ
- The rubric selector would need to drive too much downstream behavior, defeating the simplicity goal

## System-Wide Impact

### Interaction Graph

- Operator types "make Pro stand out" → `docs/skills-index.md` trigger match → `skills/adapters/claude/pro-value-audit.md` (or `premium-feel-audit.md`)
- Adapter routes to `skills/canonical/pro-value-audit/skill.md`
- Canonical body references `skills/canonical/shared/recon-scaffolding.md` for spine
- Skill reads observer: `docs/products/life-clock/pro-value-rule.md` → `docs/products/life-clock/MONETIZATION.md` → `docs/products/life-clock/vision.md` → Paywall sources
- Skill writes backlog: `docs/products/life-clock/pro-value-backlog-2026-MM-DD-<focus>.md`
- Operator copy-pastes a prompt from the backlog into a fresh chat invoking `simulator-driven-polish`
- `simulator-driven-polish` consumes the prompt unchanged (because the per-prompt template is the shared spine)

### Error & Failure Propagation

- Missing `premium-bar.md` → skill refuses with explicit message; no half-result written
- Missing operator memory directory (fresh machine) → treated as "no relevant entries"; not a refusal
- Reconciliation test failure on new fixture → blocks CI; commits 4 and 5 are independently revertable if either fixture is malformed
- Drift between shared per-prompt template and `simulator-driven-polish` consumption logic → silent failure mode; mitigated by the consumer-contract version comment annotation added in commit 1

### State Lifecycle Risks

- Backlog files are timestamped; multiple invocations on the same day with the same focus generate slug collisions — resolved per existing recon pattern by appending `-2`, `-3` (validated by the cooling-off-rule logic)
- No persistent state outside written backlog files; skills are read-only by design

### API Surface Parity

- `simulator-polish-recon`, `premium-feel-audit`, `pro-value-audit` all expose the same per-prompt template — this IS the API surface parity. Any future skill that emits a polish backlog MUST use the shared template.
- `simulator-driven-polish` is the sole consumer of all three skills' output — it does not need any code change because the template is unchanged.

### Integration Test Scenarios

These are scenarios unit tests with mocks would never catch:

1. **End-to-end backlog → polish cycle for premium-feel-audit.** Run premium-feel-audit on life-clock; pick one emitted prompt; run simulator-driven-polish on it; verify the polish skill accepts every field without complaint.
2. **End-to-end backlog → polish cycle for pro-value-audit.** Same as (1) but the prompt targets Paywall + Pro-gated surfaces; verify simulator-driven-polish recognizes the prompt's intent as falling into Stretch or Feature tier (Pro changes usually require an Ask).
3. **Cross-skill memory-pass consistency.** Run all three audit skills back-to-back on life-clock; verify all three respect the same memory entries (e.g. `feedback_life_clock_wake_animation.md` — no skill should emit a prompt that contradicts the once-per-day wake decision).
4. **Disambiguation under ambiguous prompts.** Operator types "audit the app" — Claude must ask which skill, not silently route to the first match (binding disambiguation rule).
5. **Rubric absence refusal.** Delete `premium-bar.md`; invoke `premium-feel-audit`; verify refusal with a clear pointer to author the rubric, not a half-result.

## Acceptance Criteria

### Functional Requirements

- [ ] `skills/canonical/shared/recon-scaffolding.md` exists, contains the universal spine, and is referenced by `simulator-polish-recon`, `premium-feel-audit`, and `pro-value-audit`
- [ ] `simulator-polish-recon/skill.md` is slimmed (target: ≤170 lines) with no behavior change — every prior contract surface still resolves (inline or by cross-reference)
- [ ] `docs/products/life-clock/premium-bar.md` exists with all binding sections from Phase 2
- [ ] `docs/products/life-clock/pro-value-rule.md` exists with all binding sections from Phase 3 and references `MONETIZATION.md`
- [ ] `premium-feel-audit` skill exists across all 5 surfaces: canonical + adapter + registry entry + fixture + `.claude/skills/` pointer
- [ ] `pro-value-audit` skill exists across all 5 surfaces
- [ ] Both new skills have `fixture_status: passing` in `registry.yaml`
- [ ] Both new fixture files parse as valid YAML with non-empty `input` and `expected` fields
- [ ] `tests/python/unit/test_premium_feel_audit_fixtures.py` exists and passes
- [ ] `tests/python/unit/test_pro_value_audit_fixtures.py` exists and passes
- [ ] `docs/skills-index.md` lists both new skills with trigger phrases and includes the disambiguation note
- [ ] Both new skills' per-prompt template matches the shared spine exactly (so `simulator-driven-polish` consumes them unchanged)

### Non-Functional Requirements

- [ ] `test_skill_reconciliation.py` passes after every commit (incremental safety — any commit revertable)
- [ ] All cross-references in new files resolve (file paths + heading anchors exist)
- [ ] Python coverage stays at or above 55% (the staged floor)
- [ ] No edits to `vision.md`, `MONETIZATION.md`, or any `products/<id>-ios/` source — this PR is docs + skills only

### Quality Gates

- [ ] `./scripts/test_python.sh` passes locally before commit 6
- [ ] `verification-loop` skill produces a clean verdict on the worktree
- [ ] `skill-stocktake` produces no new drift items
- [ ] `context-budget` shows the Claude skill lane has not exceeded its budget (the two new skills should add roughly the same per-skill weight as `simulator-polish-recon`; total lane growth should be sub-linear because of the shared spine)

## Success Metrics

- **Time-to-first-elevation-prompt**: when the operator types "make the app feel more premium" or "make Pro stand out," the agent produces a written backlog of ≥10 evidence-cited prompts in a single skill invocation. Today, this takes a back-and-forth dialogue.
- **Backlog → polish consumption rate**: at least one prompt from a `premium-feel-audit` backlog should be runnable in `simulator-driven-polish` within 30 days of this PR landing, with zero code changes to the polish skill. Validates the consumer-contract parity.
- **Operator memory regressions**: zero prompts from the new skills should contradict a memory entry (hard-refusal contract surface).

## Dependencies & Prerequisites

- **No new dependencies** — both siblings are pure docs + Python test files
- **Requires**: `skills/canonical/shared/recon-scaffolding.md` (created in commit 1) before commits 4 and 5 can land
- **Requires**: `premium-bar.md` (commit 2) before commit 4 fixture can lock its observer-input expectation
- **Requires**: `pro-value-rule.md` (commit 3) before commit 5 fixture can lock its observer-input expectation

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Shared per-prompt template drifts from `simulator-driven-polish` consumption | Medium | High (silent skill chain break) | Annotation in commit 1: "edits here must update polish consumer + bump version comment" |
| `simulator-polish-recon` behavior changes during the slim refactor | Medium | High (existing operator workflow breaks) | Commit 1 is no-behavior-change; every lifted section gets a cross-reference; manual verification step in /workflows:work |
| New fixtures fail reconciliation | Low | Medium (CI blocks PR) | Pattern-match `test_ios_simulator_ux_audit_fixtures.py` exactly; run fixture parse locally before commit |
| Trigger phrase ambiguity between four sibling-ish skills | Medium | Medium (agent routes incorrectly) | Explicit disambiguation note in commit 6; binding "ask before guessing" rule already in CLAUDE.md |
| `premium-bar.md` / `pro-value-rule.md` start as stubs and never get fleshed out | Medium | Medium (audits become hollow) | Both skills' fixture locks "rubric is fleshed out" via required section count; bootstrap-prompt failure mode covers the stub case |
| Operator's vague prompts still get misrouted to old recon out of habit | Low | Low (fixable in chat) | Disambiguation note + memory entry update can be a follow-up |
| One of the six commits fails the per-commit reconciliation gate | Low | Low (rollback by commit) | Six-commit structure exists specifically to make rollback granular |

## Resource Requirements

- **Implementation effort**: ~4–6 hours of agent-driven work + ~30 minutes operator review per commit
- **No team changes** — solo operator
- **No infra changes**
- **No new dependencies**

## Future Considerations

### Extensibility

- The shared spine in `recon-scaffolding.md` is designed to support more siblings. Future audit skills (e.g., `accessibility-audit`, `performance-audit`, `onboarding-funnel-audit`) follow the same pattern: own rubric + own tier vocabulary + own readiness flag, reuse the spine.
- Multi-product future: when life-clock is no longer the only product, each product gets its own `premium-bar.md` and `pro-value-rule.md`. The skills are already product-parameterized via `product_id` input.
- Variety-mandate floors per sibling are explicit and modifiable; future siblings can declare their own.

### Long-term vision

- The full audit suite (`recon`, `premium-feel`, `pro-value`, future siblings) produces a stack of backlogs the operator can sequence into a release campaign. A meta-skill (`audit-orchestrator`) could later compose all sibling outputs into a single ranked plan-of-attack — explicitly out of scope for this PR.
- Premium-readiness and pro-value-readiness flags eventually feed into a release-gate dashboard alongside submission-readiness. Out of scope here.

## Documentation Plan

- `docs/skills-index.md` — updated with both new skills' trigger phrases + disambiguation note (commit 6)
- `skills/WIRING.md` — no change needed (the new skills follow the documented pattern)
- `skills/registry.yaml` — two new entries (commit 4 and 5)
- `CLAUDE.md` — verify only; no change expected
- Inline within shared/recon-scaffolding.md — the consumer-contract version annotation

## Sources & References

### Origin

- **In-chat audit conversation 2026-05-12** — Option B was selected from a three-option capability audit. Key decisions carried forward:
  - Fork (not edit-in-place) because mixing remedial and elevation framings risks failure mode already in operator memory
  - Extract shared spine first to keep skill bodies coherent and under their context-budget weight
  - Per-prompt template MUST stay identical to `simulator-driven-polish` consumption (zero glue code)
  - Each sibling owns its own rubric, tier vocabulary, variety floors, and readiness flag

### Internal references

- `skills/canonical/simulator-polish-recon/skill.md` — the template being forked
- `skills/canonical/simulator-driven-polish/skill.md` — the consumer of all sibling outputs
- `skills/canonical/ios-simulator-ux-audit/skill.md` — the existing sibling pattern proof-of-concept
- `skills/canonical/ios-simulator-ux-audit/fixtures/happy_path.yaml` — fixture pattern to mirror
- `skills/WIRING.md` — binding wire-up procedure for new Claude project skills
- `skills/registry.yaml` — registry schema and `fixture_status` semantics
- `tests/python/unit/test_skill_reconciliation.py` — the hard gate every passing fixture must satisfy
- `tests/python/unit/test_ios_simulator_ux_audit_fixtures.py` — fixture-test pattern to mirror
- `docs/skills-index.md` — trigger-phrase catalog
- `docs/products/life-clock/MONETIZATION.md` — source of truth for the Free/Pro rule
- `docs/products/life-clock/vision.md` — tone and Decided Constraints
- `docs/products/life-clock/haptics-spec.md` — cross-referenced observer input
- `docs/products/life-clock/MVP_VS_FOUNDER_PACK_AUDIT_2026-04-28.md` — one-off audit precedent
- Operator memory entry `feedback_simulator_polish_recon_calibration.md` — the failure mode that motivates this fork
- ADR `docs/adr/2026-04-14-canonical-skill-layout.md` — per-skill-directory layout decision

### Related work

- `simulator-polish-recon` registry comment notes "v1.1 follow-up" for adding a contract-freeze fixture — this PR optionally satisfies that follow-up (stretch goal, deferred to /workflows:work decision)
- The `compound-engineering:brainstorming` skill exists but is not product-aware — a future PR could wire a Life-Clock-aware brainstorming wrapper that reads the new rubrics as context. Out of scope here.

---

## Deepening Review Findings (2026-05-12)

Six parallel agents reviewed the plan above. This section captures their findings, the synthesis decisions, and the resulting revisions to the plan. The original plan body is preserved; this section is binding for implementation.

### Agent panel

1. **`compound-engineering:research:repo-research-analyst`** — researched skill-system conventions (fixture format, registry semantics, adapter conventions, layout ADR, disambiguation enforcement).
2. **`compound-engineering:research:learnings-researcher`** — searched `docs/solutions/` and operator memory for past skill-related learnings.
3. **`compound-engineering:research:git-history-analyzer`** — traced sibling-skill split history.
4. **`compound-engineering:review:architecture-strategist`** — architectural review of the shared-spine pattern.
5. **`compound-engineering:review:code-simplicity-reviewer`** — YAGNI / over-engineering pressure-test.
6. **`compound-engineering:review:pattern-recognition-specialist`** — conformance audit against existing patterns.

### Critical findings (binding revisions)

#### 1. Fixture keys must use recognized `_GROUP_LABELS` (repo-research-analyst)

**Severity: critical. Silent-pass risk.**

The fixture keys proposed in Phase 4 (`required_tier_vocabulary`, `required_variety_floors`, `required_observer_inputs`, `required_readiness_flag`, `references_shared_scaffolding`) are **NOT** in the `_GROUP_LABELS` dictionary at `tests/python/unit/_skill_contract_freeze.py:37-67`. The contract-freeze helper silently no-ops on unrecognized keys. The fixtures would pass the reconciliation gate (because `input` is non-empty) but the assertions on these custom keys would never actually check anything.

**Recognized keys (use these):** `required_section_headings`, `required_input_fields`, `required_preconditions`, `required_checklist_items`, `required_failure_modes`, `required_handoff_channel`, `required_output_sections`, `required_modes`, `required_decision_tiers`, `required_strong_v1_capabilities`, `required_vision_sections`, `required_stop_conditions`, `required_forbidden_areas`, `required_allowed_edit_paths`, `required_helper_dependencies`, `required_hard_gate_references`, `required_record_fields`, `required_status_values`, `required_severity_labels`, `required_verdict_values`, `required_safety_clauses`, `required_pack_sections`, `required_lane_coverage_keys`, `required_character_limits`, `required_validation_steps`, `required_output_fields`, `required_phase_headings`.

**Revision (binding):**

- In commit 1 (foundation), extend `tests/python/unit/_skill_contract_freeze.py:37-67` with two new group labels: `required_tier_vocabulary` and `required_variety_floors`. This is a one-time, repo-wide extension that benefits all future audit skills with sibling-specific contract surfaces.
- All other plan-proposed keys must remap to recognized ones:
  - `required_observer_inputs` → `required_input_fields` (add the observer file paths as input-field strings)
  - `required_readiness_flag` → `required_section_headings` (the readiness-flag section heading is what gets locked)
  - `references_shared_scaffolding` → `required_section_headings` (assert a "References shared scaffolding" subsection or cross-reference exists)

#### 2. Plan overclaims existing-pattern precedent (pattern-recognition-specialist + git-history-analyzer)

**Severity: high. Documentation correctness.**

The plan asserts "Matches the existing sibling pattern (`ios-simulator-ux-audit` and `simulator-polish-recon` already share scaffolding by convention)." **This is false.** Git history confirms: `simulator-polish-recon` shipped 2 days ago (`b70b1a6`, 2026-05-10) as a standalone authored file with zero shared content. `ios-simulator-ux-audit` and `simulator-driven-polish` are also standalone. No refactor has ever extracted shared content between simulator-* skills.

**Revision (binding):** the plan's Overview and Proposed Solution sections must be corrected to say "this PR INTRODUCES the shared-spine pattern for the simulator-polish family. Prior art for the cite-by-anchor pattern exists in `skills/canonical/shared/` for infrastructure skills (`bounded-codex-implementation.md` → `post-run-validation.md`, `app-store-positioning-pack.md` → `handoffs/ios-to-appstore-handoff.md`) but not for the polish/audit family." This is new precedent for this skill family, justified by the three-caller threshold.

#### 3. The "audit the app" trigger phrase already routes to recon — collision (pattern-recognition-specialist)

**Severity: high. Routing ambiguity.**

`docs/skills-index.md` currently lists "audit the app" / "build me a backlog" / "what should we work on" / "what gaps does the app have" as triggers for `simulator-polish-recon`. The new skills will create direct ambiguity. The plan's commit 6 only ADDS trigger lines; it must also EDIT the recon line to remove or qualify "audit the app."

**Revision (binding):** in commit covering routing docs:

- Change recon's trigger line to use qualifiers: "audit the app for regressions / drift / submission gaps" instead of bare "audit the app."
- Add an explicit four-way disambiguation paragraph to the top-level "Disambiguation rule (binding)" section in `docs/skills-index.md` (not a parallel paragraph near the trigger list — that creates two disambiguation surfaces).
- Trigger phrases for the new skills must be specific: "make it feel premium" / "elevate the app's premium feel" / "premium-feel audit" / "premium-feel backlog" (not bare "audit the app").

#### 4. Adapter slimming required, not just canonical slimming (learnings-researcher → `skill-estate-adapter-mirror-and-batch-todo-resolution`)

**Severity: high. Anti-pattern repetition.**

The existing recon adapter is 114 lines; ux-audit adapter is 41 lines. The documented anti-pattern (`docs/solutions/architecture/skill-estate-adapter-mirror-and-batch-todo-resolution.md`) explicitly calls out adapters that mirror canonical content. **Adapters should be 20-30 line quick-references**, not parallel skill bodies.

**Revision (binding):**

- In commit 1 (foundation), slim the recon adapter from 114 → 30–40 lines. Replace mirrored canonical content with "See canonical Phase X" pointers.
- New skill adapters in commits 3 and 4 MUST be ≤30 lines. Add this as an acceptance criterion.

#### 5. The "consumer-contract version comment" mitigation is performative (simplicity-reviewer)

**Severity: medium. Cut performative ritual.**

The plan proposes a comment annotation saying "if you edit the per-prompt template, also update simulator-driven-polish consumption and bump a version comment." Comments are not enforcement. Nobody bumps version comments in markdown.

**Revision (binding):** cut the version-comment ritual entirely. Replace with the schema-driven enforcement in finding #6.

#### 6. Per-prompt template needs a typed schema, not prose (architecture-strategist)

**Severity: high. The only real mechanical enforcement option.**

The plan calls the per-prompt template "binding" 14 times but enforces it only via prose. A 10th template field could be added in one skill body and silently break the producer-consumer contract with `simulator-driven-polish`. The shared markdown spine documents the template; nothing mechanically detects drift.

**Revision (binding):** in commit 1 (foundation), add:

- `packages/schemas/polish_prompt.schema.yaml` — typed schema declaring the 9 binding fields of the per-prompt template (tier, evidence, idea, surfaces, fixture-knobs, prior-context, success-criteria, iteration-cap, final-computer-use-checkpoint). YAML, not JSON, to match repo convention. Validation rules per field where applicable (e.g., `iteration_cap: type=int, min=1, max=10`).
- `shared/recon-scaffolding.md` cites the schema as the canonical contract; the markdown is documentation.
- `simulator-driven-polish/skill.md` adds a one-line "consumes prompts conforming to `packages/schemas/polish_prompt.schema.yaml`" annotation (the consumer parser is prose, but the producer schema is mechanical).
- Each producer fixture's `required_input_fields` lists the schema fields verbatim — this gives us field-level reconciliation without building a parser.
- **Out of scope:** a runtime parser that validates emitted prompts against the schema. That's a future PR.

#### 7. Six commits is bureaucratic; collapse to four (simplicity-reviewer + git-history-analyzer)

**Severity: medium. Granularity vs review burden.**

Git history's strongest pattern for new skills is "registry-flip + fixture + per-skill test + adapter + canonical in ONE atomic commit" (`acefe50`, `06bbfa3`, `3398669`). The plan's six-commit split is more bureaucratic than the repo habit. Pure docs (rubrics) and pure skill-package commits naturally bundle.

**Revision (binding): four-commit structure replaces six:**

1. **Commit 1 — Foundation (LARGE).** New typed schema (`packages/schemas/polish_prompt.schema.yaml`) + extension to `_skill_contract_freeze.py` with two new group labels + new `skills/canonical/shared/recon-scaffolding.md` + slim `simulator-polish-recon/skill.md` (273 → ~150 lines) + slim recon adapter (114 → 30–40 lines) + add contract-freeze fixture for `simulator-polish-recon` (closes the v1.1 tech debt from `b70b1a6`) + flip recon's `fixture_status: missing → passing` + edit existing recon trigger line in `docs/skills-index.md` to remove "audit the app" overlap.

   *Justification for size: every piece in this commit is interdependent. Schema and group labels enable the fixture. The fixture closes existing tech debt. The slimming validates the shared-spine works against a real skill before forking new ones from it.*

2. **Commit 2 — Rubric docs.** `docs/products/life-clock/premium-bar.md` + `docs/products/life-clock/pro-value-rule.md`. Paired because they are symmetric product policy docs and the next two commits depend on both existing.

3. **Commit 3 — `premium-feel-audit` (atomic).** Canonical + ≤30-line adapter + registry entry (`fixture_status: passing` from day one — no repeating the recon anti-pattern) + fixture using recognized group labels + per-skill contract-freeze test + `.claude/skills/` pointer.

4. **Commit 4 — `pro-value-audit` + routing (atomic).** Symmetric with commit 3, plus: trigger phrases for both new skills in `docs/skills-index.md` + extension to the top-level "Disambiguation rule (binding)" section.

#### 8. Don't repeat the recon "ship without fixture" anti-pattern (git-history-analyzer)

**Severity: high. Already-realized tech debt.**

`simulator-polish-recon` shipped 2 days ago with `fixture_status: missing` and a comment promising "v1.1 follow-up." That follow-up has never landed. The strongest repo pattern (`acefe50`, `06bbfa3`, `3398669`) is fixture + test + registry-flip in the same commit.

**Revision (binding):**

- Both new skills land with `fixture_status: passing` in their introducing commit.
- Recon's existing missing-fixture debt is closed in commit 1 (this is now in-scope, not stretch).

### Non-binding findings (acknowledged, not actionable in this PR)

- **Unified release-readiness rollup (architecture-strategist).** Per-sibling readiness flags (submission / premium / pro-value) will overlap in practice. A future `audit-orchestrator` skill should roll them up. Already noted as future work in the plan; keep as-is.
- **Rubric-shape enforcement at the skill level (architecture-strategist).** Skill-scoped rubric templates would prevent a new product from silently dropping rubric categories. Useful when life-clock is no longer the only product. Defer to future PR.
- **Retrofit `ios-simulator-ux-audit` and `simulator-polish-recon` to share scaffolding (pattern-recognition-specialist).** For true symmetry. Defer — recon refactor is already in commit 1; ux-audit can follow in a separate PR.
- **Adapter quick-reference template extraction (learnings-researcher).** Documenting the 25-line adapter shape as a reusable template lives in a separate hygiene PR.
- **Per-skill state tracking via YAML memory (learnings-researcher → content-intelligence-skill-pair-design).** If audit skills ever need to suppress prompts from prior runs, that goes in per-skill YAML memory, not the shared scaffold. Not needed at v1.

### Revised acceptance criteria

Additions / changes to the original Acceptance Criteria block:

**Functional additions:**

- [ ] `packages/schemas/polish_prompt.schema.yaml` exists with the 9 binding template fields; valid YAML; loadable
- [ ] `tests/python/unit/_skill_contract_freeze.py` extends `_GROUP_LABELS` with `required_tier_vocabulary` and `required_variety_floors`
- [ ] `simulator-polish-recon` is flipped to `fixture_status: passing` with a real contract-freeze fixture at `skills/canonical/simulator-polish-recon/fixtures/happy_path.yaml`
- [ ] `simulator-polish-recon` adapter slimmed to ≤40 lines
- [ ] Both new skill adapters are ≤30 lines (quick-reference shape)
- [ ] All proposed fixture keys map to recognized `_GROUP_LABELS` (after the extension lands)
- [ ] Existing recon trigger line in `docs/skills-index.md` edited to remove "audit the app" overlap
- [ ] Top-level "Disambiguation rule (binding)" section in `docs/skills-index.md` extended with the four-way carve-out (recon / premium-feel-audit / pro-value-audit / simulator-driven-polish)
- [ ] `simulator-driven-polish/skill.md` has the one-line schema-reference annotation
- [ ] Plan-body overclaim about "matches existing sibling pattern" is corrected to "introduces shared-spine pattern for the simulator-polish family"

**Non-functional additions:**

- [ ] No `re.compile()` at module level anywhere in new code (AST-convention test compliance — see `multi-phase-plan-shipping-primitives-skills.md`)
- [ ] No word-wrapped strings in binding fixture assertions (see same learning)
- [ ] Each atomic commit's message says "Atomic: X + Y + Z" when more than two surfaces are touched in one commit

### Closure of original plan's open issues

- **"Recommended stretch: add fixture for simulator-polish-recon"** → **CLOSED.** Promoted to in-scope and bundled into commit 1.
- **"CLAUDE.md may not need changes but should verify"** → **CLOSED.** Confirmed: CLAUDE.md delegates to `docs/skills-index.md`. No CLAUDE.md edit needed.
- **"Per-fixture tests redundant?" (simplicity-reviewer raised)** → **REJECTED as proposed cut.** The shared reconciliation test only checks structural validity (non-empty `input`/`expected`). The per-skill contract-freeze tests assert content via `_GROUP_LABELS`. Keep per-skill tests; they're load-bearing, not redundant. (The simplicity reviewer was wrong here — they didn't read `_skill_contract_freeze.py`.)

### Risk table additions

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Schema/markdown drift over time | Medium | Medium | Cite schema as canonical from shared spine; the markdown is documentation |
| New group labels (`required_tier_vocabulary`, `required_variety_floors`) become orphans if no other skill ever uses them | Low | Low | Acceptable — they encode the audit-skill contract surface, designed for future siblings |
| Commit 1 size raises review friction | Medium | Low | Document the interdependency explicitly in the commit message; reviewer can land it atomically or request a split |
| `_skill_contract_freeze.py` extension breaks an existing passing skill silently | Low | High | Run `./scripts/test_python.sh` after the group-label extension; all existing fixture tests must still pass before fixture work begins |

### Implementation order

The four commits must land in order. Within commit 1, the implementation order is:

1. Add the schema file first (it's referenced by everything downstream)
2. Extend `_skill_contract_freeze.py` (must precede any fixture work)
3. Write `shared/recon-scaffolding.md` (cites the schema)
4. Slim recon's canonical body (cites the spine)
5. Slim recon's adapter (mirrors the canonical slimming)
6. Author recon's contract-freeze fixture (using both recognized and new group labels)
7. Flip recon's `fixture_status` in `registry.yaml`
8. Edit recon's trigger line in `docs/skills-index.md`
9. Run full test suite — must be green before commit

Commits 2, 3, 4 then proceed in stated order with each landing fully green.
