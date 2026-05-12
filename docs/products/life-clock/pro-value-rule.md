# Life Clock — Pro-Value Rule

> **Status:** Observer rubric for `pro-value-audit`. Read-only product policy doc. The skill scores every Pro touchpoint against the criteria below and emits backlog prompts for gaps. This file operationalizes the Free/Pro rule from [MONETIZATION.md](MONETIZATION.md) into auditable categories.
>
> **Initialized:** 2026-05-12. Source docs: [MONETIZATION.md](MONETIZATION.md), [PaywallSheet.swift](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift), [vision.md](vision.md), [APP_STORE_ASO.md](APP_STORE_ASO.md).
>
> **Editing rule:** the operator owns this file. The audit skill reads it; it does not edit it. New audit criteria added here become new audit dimensions in the next `pro-value-audit` run.

---

## Why this rubric exists

`pro-value-audit` audits Pro discoverability, Pro justification, perceived depth of Pro features, paywall friction, upsell-moment usage, and value-claim accuracy. The Free/Pro rule from MONETIZATION.md is the source of truth for what Pro should be; this rubric is how the audit walks the app against that rule.

Specifically: MONETIZATION.md says "**Free = understanding, Pro = depth, archive, and correction power.**" That's a principle. The categories below turn the principle into checks the audit can score.

This file is product-scoped to Life Clock. Other products would author their own.

## The Free/Pro rule (verbatim from MONETIZATION.md)

- **Free = understanding**
- **Pro = depth, archive, and correction power**

Practical tests:

- If removing the feature would make the app feel confusing or emotionally empty, it probably belongs in Free.
- If the feature helps the user revisit, audit, compare, or correct past information, it probably belongs in Pro.
- If the feature is required for trust in the basic daily loop, it belongs in Free.
- If the feature rewards power users who want more history, more explanation, or more control, it belongs in Pro.

**Paywall timing rule:** Do not show a hard paywall before first value. Best conversion moments per MONETIZATION.md: (1) after first Life Clock reveal, (2) after the user taps locked detailed driver breakdown.

## Audit criteria (binding categories)

The audit walks every Pro touchpoint and scores each against:

### Discoverability

- **Is Pro signaled in the right surfaces?** The audit lists every Pro-gated feature and checks whether the user encounters a Pro signal in the natural daily flow. Pro that exists but the user never sees = `pro-invisible`.
- **Is signaling consistent?** Across surfaces, is the Pro signal visually consistent (icon, lock, color)? Per-surface reinvention = `pro-invisible` (visual fragmentation hurts discoverability).
- **Does the signal explain itself?** When the user sees a Pro lock, can they tell what's behind it without tapping? Vague locks = `pro-invisible`.

### Justification

- **Does every Pro gate have a "why" the user can read?** When the user encounters a Pro gate, is there in-context copy explaining what Pro adds? No-copy gates = `value-claim-unjustified`.
- **Is the justification concrete?** "Unlock Pro" alone is not justification. "See your full Time Ledger and edit imported HealthKit values" is. Generic copy = `value-claim-unjustified`.
- **Does justification match the practical tests?** A Pro gate that doesn't match the Free/Pro rule (e.g., gating something Free should have) gets flagged as `pro-rule-violation`.

### Perceived depth

- **Do Pro surfaces feel substantively deeper than Free?** When the user actually unlocks Pro (or sees the preview), does it feel like more information, more control, more history — or just Free behind a wall? Shallow Pro = `pro-thin`.
- **Does Pro reward the kind of user the rule describes?** Pro is for users who want depth, archive, correction power. Does the actual Pro experience deliver on that? Pro that doesn't match = `pro-thin`.
- **Is there visible Pro-only craft?** Pro screens should feel hand-tuned, not Free with extra rows. Pro that looks identical to Free in motion / typography / haptics = `pro-thin`.

### Friction-to-trial

- **How many taps from a Pro signal to trying Pro?** Best practice: 1–2 taps. More than 3 = `friction-too-high`.
- **Is there preview value before commit?** Can the user see something useful before being asked to pay? No preview = `friction-too-high`.
- **Is the trial offer (if any) clear?** If a free trial is offered, is the duration, what's included, and the conversion behavior obvious? Vague trial = `friction-too-high`.

### Upsell moments

- **Are the MONETIZATION.md best moments actually used?** The audit checks: (1) does a Pro signal appear after first Life Clock reveal, (2) does a Pro signal appear after the user taps a locked detail breakdown. Missing best moments = `upsell-missed`.
- **Are there over-aggressive moments?** Pro signals in surfaces where MONETIZATION.md says Free must own the moment (e.g., the basic daily-trajectory reveal) = `pro-rule-violation`.
- **Is the cadence respectful?** Pro upsells should not appear more than twice in a daily session without explicit user opt-in. Spammy upsell = `friction-too-high`.

### Trust

- **No dark patterns.** No fake-urgency timers, no pre-checked auto-renew, no buried cancel. Any dark pattern = `trust-gap` (high-severity).
- **Clear cancel path.** The user can find "how do I cancel?" within 3 taps from any Pro surface. Buried cancel = `trust-gap`.
- **Restore works.** Restore Purchases works on every relevant surface, errors are honest, and the restore path is audited within the last 30 days. Untested restore = `trust-gap`. (Cross-reference: recent polish logs covering `polish-2026-05-10-subscription-lifecycle-states.md` and `polish-2026-05-10-restore-failed-alert*.md`.)
- **No surprise charges.** Pricing displayed before the buy confirmation matches the actual charge. Any mismatch = `trust-gap` (submission-blocker tier, escalates).

### Value-claim accuracy

- **Does paywall copy promise what Pro delivers?** Every claim on the paywall is checked against the actual Pro experience. Paywall says "advanced HealthKit metrics" → the audit verifies those exist and are usable. Mismatch = `value-claim-unjustified`.
- **Is App Store copy aligned?** Pro-related claims in [APP_STORE_ASO.md](APP_STORE_ASO.md) match in-app Pro experience. Drift = `value-claim-unjustified`.
- **Are screenshots in store / paywall current?** Stale screenshots = `value-claim-unjustified`.

## Pro touchpoint inventory

The audit walks these surfaces. Update this list as Pro grows.

- **PaywallSheet.swift** — the canonical paywall. Audited in full each run.
- **Today** — Pro signal moments: after first Life Clock reveal (per MONETIZATION.md), after tapping a locked detailed-driver breakdown.
- **History** — Pro signals on entries older than 7 days (Pro unlocks the full archive).
- **Future tab** — Pro signals on long-horizon projections and detailed lever breakdowns.
- **WrapUp** — Pro signals on richer weekly/monthly wrap-up content.
- **Profile** — subscription status, restore button, cancel pointer (must be present per Trust criteria).
- **Settings / subscription management** — explicit Pro state, lifecycle controls.

A surface missing from this list that gates Pro features = `pro-invisible` (the inventory is wrong; the audit emits a prompt to update the inventory and audit the missing surface).

## Anti-signals (what is NOT good Pro value)

These appear on the backlog as Pro-value-audit prompts whenever encountered:

- Generic "Unlock Pro" with no specifics about what's behind the gate
- Pro that gates the first meaningful answer (forbidden by MONETIZATION.md — escalates to `pro-rule-violation`)
- Paywall before first value (forbidden by MONETIZATION.md — escalates)
- Dark patterns (any) — escalate to `trust-gap` and `submission-blocker`-tier
- Pro screens visually identical to Free
- Vague trial copy
- Buried cancel
- Pricing mismatch between paywall and confirmation
- Pro upsells more than twice per daily session
- Stale paywall screenshots

## Cadence

Re-audit cadence:

- After every Pro touchpoint change (immediate)
- Before every App Store submission push (mandatory — `focus: submission-readiness` mode)
- Monthly otherwise

Edits to this rubric:

- When a new Pro feature ships (add to "Pro touchpoint inventory")
- When MONETIZATION.md changes (mirror the change here)
- When an anti-signal recurs across audits (add to "Anti-signals")
- When subscription compliance rules change (update Trust criteria)

## How this rubric is enforced

The audit reads this file and walks the surfaces. Per Pro touchpoint:

1. Score every category `strong` / `partial` / `weak` / `absent`.
2. For every category that scores `weak` or `absent`, draft a category-specific prompt (`pro-thin` / `pro-invisible` / `upsell-missed` / `value-claim-unjustified` / `friction-too-high` / `trust-gap` / `pro-rule-violation`).
3. Cite this rubric file + the specific category + the specific Pro touchpoint as evidence in the prompt's `Evidence` field.
4. Escalate `trust-gap` and `pro-rule-violation` to submission-blocker tier and surface them prominently in the report's executive summary.
5. The consuming `simulator-driven-polish` session will tier the fix per its own decision layer — but most pro-value fixes are Stretch or Feature (rarely Polish), because monetization changes warrant operator review.
