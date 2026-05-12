---
status: pending
priority: p3
issue_id: "060"
tags: [code-review, simplicity, skills, audit-fork]
dependencies: []
---

# Problem Statement

The siblings (`premium-feel-audit/skill.md` 233 lines, `pro-value-audit/skill.md` 243 lines) are LONGER than the slimmed recon (~200 lines), and the shared scaffold (`recon-scaffolding.md` 150 lines) is on top of that. The "shared spine reduced duplication" claim is partially aspirational — each sibling still carries full output schemas, anti-patterns, and operator-memory-pass language inline.

Also some content in the shared scaffold itself duplicates rules that are binding elsewhere: the "Quality checks before writing" checklist restates rules already covered by anti-patterns and per-prompt template; the "Cadence guidance" prose is advisory commentary, not contract.

## Findings

- **code-simplicity-reviewer:** "Each sibling's 'Anti-patterns' and 'Operator memory pass' sections should be a one-line 'see shared/recon-scaffolding.md §X' reference, not full restatement. ~30 LOC each... CUT the 'Quality checks before writing' checklist (lines 117–129) [in scaffold] — every item restates a rule already binding above. And CUT the 'Cadence guidance' prose (lines 131–140) — it's advisory commentary, not contract. Net: ~25 LOC."

## Proposed Solutions

### Option 1: Aggressive collapse

In each sibling skill body, replace inline restatements with one-line "See `shared/recon-scaffolding.md` § X" references for:
- Anti-patterns (already says "(inherited)" but still restates ~10 lines each)
- Operator memory pass
- Same-day collision rule
- Per-prompt template

In the shared scaffold itself:
- Cut "Quality checks before writing" (already covered by anti-patterns + per-prompt template)
- Cut "Cadence guidance" (advisory, not contract)

Pros: ~80 LOC saved across the family; cleaner separation of contract (spine) vs sibling-specific (observer + tier + readiness)
Cons: less self-contained — siblings can't be read without the spine
Effort: Small
Risk: Low (the "see spine" references are valid because the spine itself exists)

### Option 2: Conservative trim

Only cut the shared scaffold's duplications (~25 LOC). Leave sibling bodies as-is.

Pros: smallest change
Cons: doesn't fix the larger duplication concern
Effort: Trivial
Risk: None

## Recommended Action

**Option 1.** The "shared spine" pattern is justified ONLY if it actually reduces sibling bloat. As shipped, the spine is additive (new doc + slimmed recon) without significantly slimming the new siblings. Trimming the sibling restatements is what makes the abstraction pay off.

## Technical Details

- Files affected:
  - `skills/canonical/shared/recon-scaffolding.md` (cut two sections)
  - `skills/canonical/simulator-polish-recon/skill.md` (one-line references where applicable)
  - `skills/canonical/premium-feel-audit/skill.md` (collapse inline restatements to references)
  - `skills/canonical/pro-value-audit/skill.md` (collapse inline restatements to references)
- Fixture tests must continue to pass — any section heading that is currently locked in a fixture must remain present in the slimmed body.

## Acceptance Criteria

- [ ] Each sibling skill body ≤ ~180 lines
- [ ] Shared scaffold ≤ ~120 lines
- [ ] All fixture tests pass
- [ ] No anti-patterns or memory-pass rules are LOST from the contract — only relocated to single-source-of-truth

## Work Log

(empty)
