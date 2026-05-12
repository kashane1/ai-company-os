---
status: pending
priority: p2
issue_id: "056"
tags: [code-review, skills, audit-fork, contract, tier-vocabulary]
dependencies: []
---

# Problem Statement

`submission-blocker` is a recon-specific tier listed in recon's locked vocabulary, but pro-value-audit's canonical body describes "trust-gap" and "pro-rule-violation" as escalating "to submission-blocker tier" — without `submission-blocker` being a named tier in pro-value's locked vocabulary. This makes "submission-blocker" a fourth-class concept shared across siblings but only named in one place.

## Findings

- **architecture-strategist:** "Pro-value's locked tier list does NOT contain `submission-blocker` literal — the escalation is described in prose. Two risks: (a) 'submission-blocker' becomes a fourth-class concept shared across siblings but never named in the schema; (b) future operators may add it to pro-value's tier list, breaking the contract-freeze."

## Proposed Solutions

### Option 1: Add `submission-blocker` to pro-value's locked tier vocabulary

Treat `submission-blocker` as a cross-sibling tier that any sibling can emit when a finding crosses the App Store submission threshold. Pro-value's tier list becomes 10 entries (existing 9 + `submission-blocker`). Premium-feel-audit's tier list could likewise add it.

Pros: makes the cross-sibling escalation explicit and locked; future siblings can adopt it
Cons: slight tier-vocabulary inflation
Effort: Trivial
Risk: Low

### Option 2: Rename the escalation target in pro-value language

Change "to submission-blocker tier" to "to **the top of the report's executive summary**, marked as `submission-critical`." This avoids naming the recon-specific tier in pro-value's body.

Pros: keeps pro-value's tier list narrow
Cons: introduces a new term (`submission-critical`); inconsistent with recon's naming
Effort: Trivial
Risk: Low

### Option 3: Promote `submission-blocker` to the shared scaffold

Add a section to `skills/canonical/shared/recon-scaffolding.md` titled "## Cross-sibling escalation tier" defining `submission-blocker` as universal across recon-family siblings. Then each sibling's locked tier vocabulary doesn't need to list it; it's inherited.

Pros: clean architecture; matches how other universal contract surfaces are handled (per-prompt template, output skeleton, anti-patterns)
Cons: requires touching the shared spine again
Effort: Small
Risk: Low

## Recommended Action

**Option 3.** The "submission-blocker tier" is a cross-skill convention worth lifting to the shared spine, where every other cross-sibling rule already lives. Treating it as inherited mirrors how the per-prompt template and output skeleton are handled.

## Technical Details

- Files affected:
  - `skills/canonical/shared/recon-scaffolding.md` (add "Cross-sibling escalation tier" section)
  - `skills/canonical/simulator-polish-recon/skill.md` (remove `submission-blocker` from local vocabulary, note inheritance)
  - `skills/canonical/pro-value-audit/skill.md` (explicit reference to the inherited tier where escalation language appears)
  - `skills/canonical/premium-feel-audit/skill.md` (note inheritance if relevant)
  - Three fixtures may need adjustment depending on how `required_tier_vocabulary` interacts with inherited tiers.

## Acceptance Criteria

- [ ] `submission-blocker` is defined once in the shared spine
- [ ] Each sibling's body references it consistently
- [ ] All fixture tests pass
- [ ] No fixture locks `submission-blocker` in a sibling's local tier list that doesn't actually emit it directly

## Work Log

(empty)
