---
id: pro-value-audit
name: Pro-Value Audit
purpose: Audit a product's Pro discoverability, justification, perceived depth, friction-to-trial, upsell-moment usage, trust signals, and value-claim accuracy against `pro-value-rule.md` (which operationalizes MONETIZATION.md's Free/Pro rule); emit a ranked, variety-balanced backlog of `simulator-driven-polish` prompts focused on monetization quality. Read-only counterpart that runs BEFORE polish sessions when the operator's goal is to audit Pro value.
owner_agent: ios
target_runtimes: [claude]
stage: active
inputs:
  - product_id (e.g. life-clock)
  - baseline (branch or commit; default origin/main)
  - depth (quick | standard | deep — default standard)
  - focus (optional — paywall-only | discoverability-only | trust-only | value-claim-accuracy | upsell-moments | <free-form>)
  - minimum_prompts (default 10; absolute floor regardless of depth)
outputs:
  - one report file at docs/products/<product-id>/pro-value-backlog-<YYYY-MM-DD>-<focus-slug>.md
  - 9 binding output sections per shared/recon-scaffolding.md output skeleton, with pro-value-readiness flag as the readiness flag
allowed_edit_boundaries:
  - docs/products/<product-id>/pro-value-backlog-*.md (write)
  - skills/adapters/claude/pro-value-audit.md (read; only edit when explicitly editing the skill itself)
forbidden_areas:
  - products/<product-id>-ios/** (read-only — this skill never edits app sources)
  - packages/policies/
  - state/
  - other products under products/
  - docs/products/<product-id>/pro-value-rule.md (read-only — operator owns the rubric)
  - docs/products/<product-id>/MONETIZATION.md (read-only — source of truth for the Free/Pro rule)
  - docs/products/<product-id>/vision.md (entirely read-only — including Open Questions)
preconditions:
  - docs/products/<product-id>/pro-value-rule.md exists (REFUSE if missing — operator must author the rubric first)
  - docs/products/<product-id>/MONETIZATION.md exists (REFUSE if missing — the rubric references it as source of truth)
  - docs/products/<product-id>/vision.md exists
  - skills/canonical/shared/recon-scaffolding.md exists (the shared spine this skill references)
  - docs/products/<product-id>/ contains at least one prior polish-*.md OR ux-audit-*.md (otherwise emit a bootstrap-prompt backlog)
  - working tree clean OR operator explicitly authorized dirty start
dependencies:
  - canonical/shared/recon-scaffolding (foundational contract — per-prompt template, variety mandate shape, operator-memory pass, output structure, cooling-off rule, anti-patterns)
  - packages/schemas/polish_prompt.py (mechanical schema for the per-prompt template — POLISH_PROMPT_FIELDS)
  - canonical/simulator-driven-polish (this skill's output is consumed by that skill)
  - canonical/simulator-polish-recon (sibling — recon does remedial discovery)
  - canonical/premium-feel-audit (sibling — premium-feel-audit does elevation discovery)
  - operator auto-memory at .claude/projects/-Users-simons-ai-company-os/memory/ (mandatory read pass)
validation_steps:
  - report file exists at the expected path with all 9 required sections (per shared/recon-scaffolding.md output skeleton)
  - prompt count >= minimum_prompts AND <= depth ceiling (quick=20, standard=40, deep=60)
  - variety mandate satisfied OR explicit operator override logged in the report
  - per-prompt template adheres to packages/schemas/polish_prompt.py POLISH_PROMPT_FIELDS (9 fields, in order)
  - every emitted prompt cites pro-value-rule.md + a specific category + a specific Pro touchpoint as evidence
  - no emitted prompt's slug overlaps a session log dated within the last 14 days (cooling-off rule applies cross-skill)
  - every file path mentioned in any emitted prompt resolves in the worktree
  - coverage matrix has no empty cells (each Pro touchpoint gets a verdict)
  - memory pass was performed and the memory ledger section is present in the report
  - trust-gap and pro-rule-violation findings are escalated to submission-blocker tier and surfaced in the report's executive summary
handoff_contract:
  what_is_handed_off: a dated pro-value-backlog-*.md file containing N prompts the operator can copy-paste into fresh chats invoking simulator-driven-polish
  handed_to: operator → simulator-driven-polish
  channel: docs/products/<product-id>/pro-value-backlog-<YYYY-MM-DD>-<focus-slug>.md (the report IS the handoff)
---

# Pro-Value Audit

This skill is the **monetization counterpart** to `simulator-polish-recon` and `premium-feel-audit`. Recon diffs against prior polish coverage (remedial). Premium-feel-audit diffs against the premium bar (elevation across motion/typography/etc.). This skill diffs against `pro-value-rule.md` (which operationalizes MONETIZATION.md's Free/Pro rule) and produces prompts about Pro discoverability, Pro justification, perceived depth of Pro features, paywall friction, upsell-moment usage, trust signals, and value-claim accuracy.

This skill is a member of the **recon-family** of audit/backlog skills. The shared contract surface — per-prompt template, variety mandate shape, operator-memory pass, output structure, 14-day cooling-off, anti-patterns — lives in [`skills/canonical/shared/recon-scaffolding.md`](../shared/recon-scaffolding.md). The mechanical per-prompt field set is locked by [`packages/schemas/polish_prompt.py`](../../../packages/schemas/polish_prompt.py). This file defines what makes pro-value-audit **monetization-specific**: its observer (`pro-value-rule.md` + MONETIZATION.md), its tier vocabulary, its pro-value-readiness flag.

Use it when:

- The operator says "audit Pro value" / "make Pro stand out" / "where is Pro thin" / "Pro feels weak" / "audit the paywall" / "audit Pro discoverability" / "pro-value audit".
- Before a Pro launch or pricing change.
- Before App Store submission (Pro features are reviewed; mismatched claims trigger rejection).
- After a Pro feature ships, to verify discoverability and value-claim accuracy.

Do NOT use it when:

- The operator wants a regression audit — route to `simulator-polish-recon`.
- The operator wants a premium-feel audit (motion/typography/etc.) — route to `premium-feel-audit`.
- `pro-value-rule.md` or `MONETIZATION.md` doesn't exist or is a stub — refuse and ask the operator to author/flesh them out first.
- The operator has a specific Paywall fix in mind — route to `simulator-driven-polish` in `fix-list` mode.

## Observer

The observer that distinguishes pro-value-audit is **the diff against `pro-value-rule.md`** with MONETIZATION.md as the source-of-truth backstop. The skill reads both, walks every Pro touchpoint enumerated in the rubric's inventory, and scores each Pro touchpoint against every category in the rubric.

Read in this order:

### 1. Pro-value rubric (monetization-specific — this IS the observer)

- `Read` `docs/products/<product-id>/pro-value-rule.md` in full.
- Extract the binding category list (Discoverability / Justification / Perceived depth / Friction-to-trial / Upsell moments / Trust / Value-claim accuracy).
- Extract the Pro touchpoint inventory — the list of surfaces to walk.
- Extract "Anti-signals" — these become audit-prompt seeds.

### 2. MONETIZATION.md (monetization-specific — source of truth)

- `Read` `docs/products/<product-id>/MONETIZATION.md` in full.
- Verify the Free/Pro rule in the rubric matches MONETIZATION.md verbatim. Drift between the two = `pro-rule-violation` prompt (escalates).
- Note the "Paywall timing" rule and the "Best conversion moments" — these become upsell-moment audit criteria.

### 3. Vision (universal)

Per `shared/recon-scaffolding.md`. Pro-value-audit must respect vision tone modes (the paywall and Pro copy must match active tone).

### 4. App Store ASO (monetization-specific)

- `Read` `docs/products/<product-id>/APP_STORE_ASO.md` if present.
- Cross-reference: does the app's Pro-related copy match what App Store copy promises? Drift = `value-claim-unjustified`.

### 5. Paywall + Pro-gated source files (monetization-specific)

- `Read` `products/<product-id>-ios/Sources/Features/Paywall/**/*.swift` — the canonical paywall surface.
- For every Pro touchpoint in the rubric's inventory: grep the source for the Pro gate, capture the gate's copy and the surface it lives on.
- A Pro touchpoint in the rubric without a matching source-tree gate = inventory drift → `pro-invisible` prompt.

### 6. Prior polish coverage (universal)

Per `shared/recon-scaffolding.md`. Special attention to `polish-2026-*-subscription-lifecycle-*.md` and any `polish-*-paywall-*.md` or `polish-*-restore-*.md` logs.

### 7. Surface inventory (universal)

Per `shared/recon-scaffolding.md`. Used for cross-referencing against the Pro touchpoint inventory.

### 8. Operator memory pass (universal; mandatory)

Per `shared/recon-scaffolding.md`. Hard refusal on contradiction. Special attention to any `feedback_*subscription*` or `feedback_*paywall*` or `feedback_*pro*` memory entries.

### 9. Per-touchpoint rubric pass (monetization-specific — the core scoring)

For every Pro touchpoint in `pro-value-rule.md`'s inventory:

- For every category in the rubric: score `strong` / `partial` / `weak` / `absent`.
- For every category that scores `weak` or `absent`: draft a category-specific prompt using the tier vocabulary below.
- `trust-gap` and `pro-rule-violation` findings escalate to submission-blocker tier.

## Coverage matrix (monetization-specific columns)

Every Pro touchpoint in the rubric's inventory gets a row. Columns:

| Column | Possible values |
|---|---|
| Last polish session | YYYY-MM-DD or "never" |
| Discoverability | strong / partial / weak / absent |
| Justification | strong / partial / weak / absent |
| Perceived depth | strong / partial / weak / absent |
| Friction-to-trial | strong / partial / weak / absent |
| Upsell moments used | yes / partial / no |
| Trust | strong / partial / weak / absent |
| Value-claim accuracy | strong / partial / weak / absent |
| Free/Pro rule violation? | none / suspected / confirmed |
| Verdict | pro-aligned / pro-thin / pro-invisible / upsell-missed / value-claim-unjustified / friction-too-high / trust-gap / pro-rule-violation |

## Tier vocabulary (binding — monetization-specific)

| Tier | Meaning | Escalation | Variety floor (at standard depth) |
|---|---|---|---|
| `pro-thin` | Pro surface feels shallow — Free behind a wall | normal | — |
| `pro-invisible` | Pro exists but isn't signaled in the natural daily flow | normal | — |
| `upsell-missed` | A best-moment upsell from MONETIZATION.md isn't used | normal | — |
| `value-claim-unjustified` | Paywall / App Store copy promises X; app delivers Y | normal | — |
| `friction-too-high` | Too many taps to try Pro; spammy upsells; vague trial | normal | — |
| `trust-gap` | Dark pattern / buried cancel / restore broken / pricing mismatch | **submission-blocker** | ≥1 surfaced if any present |
| `pro-rule-violation` | Pro gates content that Free should own per the Free/Pro rule | **submission-blocker** | ≥1 surfaced if any present |
| `vision-question` | Pro positioning touches an unresolved vision Open Question | normal | ≥1 if any unresolved |
| `nice-to-have` | Quality-bar improvement with no urgency | normal | — |

## Variety mandate (monetization-specific floors at standard depth)

Per the shape defined in `shared/recon-scaffolding.md`, pro-value-audit declares these floors at standard depth:

- **≥3 `fix-list`** prompts (most pro-value findings are concrete — a specific Pro touchpoint failing a specific category)
- **≥2 `freeform-polish`** prompts (paywall sweeps, cross-touchpoint discoverability)
- **≥1 `reference-match`** prompt (compare paywall against a named premium SaaS, e.g., a Health & Fitness category leader)
- **≥1 `vision-driven`** prompt (Pro positioning questions that touch vision tone or Decided constraints)

If `focus` would force the mandate to slip, stop and ask per the shared rule.

## Per-prompt template (inherited)

Use the binding 9-field template defined in [`shared/recon-scaffolding.md`](../shared/recon-scaffolding.md) verbatim. Field names match `packages/schemas/polish_prompt.py` `POLISH_PROMPT_FIELDS`. Every emitted prompt MUST cite `pro-value-rule.md` + a specific category + a specific Pro touchpoint as its `Evidence` field.

## Anti-patterns (inherited)

All anti-patterns in `shared/recon-scaffolding.md` apply. Plus monetization-specific:

- Do NOT emit a prompt without naming a `pro-value-rule.md` category AND a specific Pro touchpoint as evidence. "Paywall feels weak" is not an audit finding; "Paywall fails Justification: 'advanced HealthKit metrics' copy is generic and doesn't say which metrics" is.
- Do NOT propose changes that violate the Free/Pro rule in MONETIZATION.md. If a finding would require moving a Free feature behind Pro, escalate to `vision-question` proposing a MONETIZATION.md edit.
- Do NOT silently downgrade `trust-gap` findings. They escalate to submission-blocker tier always.

## Output structure (inherited; 9 sections)

Use the 9-section structure from `shared/recon-scaffolding.md` verbatim. The readiness flag for this skill is **pro-value-readiness** — see next section for criteria.

## Pro-value-readiness flag — strict mode (monetization-specific)

The flag is **green** only if ALL of the following hold:

- Every Pro touchpoint in the rubric's inventory has at least one polish session log covering it in the last 30 days
- Zero unresolved `trust-gap` prompts in the emitted backlog
- Zero unresolved `pro-rule-violation` prompts
- Zero unresolved `value-claim-unjustified` prompts
- Every MONETIZATION.md "Best conversion moment" is actually used in the implementation (verified by source-tree grep)
- Restore Purchases path audited within the last 30 days
- Subscription lifecycle (cancel, expire, refund) audited within the last 30 days
- Paywall pricing copy matches the actual charge (verified via test flow or recent log)

**Yellow** = some categories thin; ≤3 unresolved category-specific tier prompts (excluding trust-gap and pro-rule-violation which always escalate).
**Red** = any unresolved `trust-gap` OR `pro-rule-violation` OR `value-claim-unjustified` prompt.

The flag is stable across sessions — if last week's flag was green and MONETIZATION.md / the rubric / the paywall source haven't changed, this week's is green.

## Operator interactions

This skill is mostly silent — its output is the report. The two times it should ask:

1. **Variety mandate conflict.** If `focus` would force the mandate to slip, ask before relaxing.
2. **Rubric or MONETIZATION.md disagreement.** If the rubric's "Free/Pro rule (verbatim)" section drifts from MONETIZATION.md, stop and surface the drift — operator must reconcile before audit proceeds.

All other findings flow into the report. Trust-gap and pro-rule-violation findings are surfaced in the report's executive summary regardless of operator preference.

## Failure modes (monetization-specific)

- **Missing `pro-value-rule.md`** — refuse; operator must author the rubric first.
- **Missing `MONETIZATION.md`** — refuse; the rubric references it as source of truth.
- **Rubric stub** — emit one-prompt bootstrap: "flesh out pro-value-rule.md before audit can be meaningful."
- **Rubric drifts from MONETIZATION.md** — refuse with explicit drift report; operator reconciles before audit re-runs.
- **Pro touchpoint inventory is empty** — emit one-prompt bootstrap: "inventory Pro touchpoints in the rubric first."
- **Missing `shared/recon-scaffolding.md`** — refuse; the shared spine is a hard dependency.
- **Memory pass produces a contradiction** — escalate to operator immediately.
- **Operator's intent is regression audit** — route to `simulator-polish-recon`.
- **Operator's intent is premium-feel audit** — route to `premium-feel-audit`.

## Same-day collision rule

Inherited from `shared/recon-scaffolding.md`: append `-2`, `-3`, etc. to the filename slug, not to the date.

## Cadence

Recommended invocation cadence:

- After every Pro feature change (immediate)
- Before every App Store submission push (mandatory — `focus: submission-readiness`)
- Before a pricing change
- Monthly otherwise

Do not invoke daily — the 14-day cooling-off rule will produce thin, repetitive backlogs.
