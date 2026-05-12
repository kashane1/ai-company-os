---
status: pending
priority: p3
issue_id: "059"
tags: [code-review, simplicity, rubrics, life-clock]
dependencies: []
---

# Problem Statement

Both rubric files carry meta-prose that doesn't earn its keep. The audit skills don't need it; the operator doesn't need it on every read. Roughly 70 LOC of trim potential across the pair.

## Findings

- **code-simplicity-reviewer:** "In `premium-bar.md`: 'Why this rubric exists' (11–17), 'Cadence' (111–120), 'How this rubric is enforced' (122–129) are all explanation for humans, not scoreable categories. The audit doesn't need them to score; the operator doesn't need them on every read. Cut ~35 lines from each by collapsing meta-sections to a 3-line preamble."

- Same applies to `pro-value-rule.md` parallel sections.

## Proposed Solutions

### Option 1: Collapse meta-sections to a 3-line preamble each

Replace "Why this rubric exists", "Cadence", and "How this rubric is enforced" sections with a single 3-line preamble at the top:

```
> Observer rubric for [skill-id]. Operator-owned; audit reads only.
> Scoring: each category → strong / partial / weak / absent.
> Cadence: re-edit when categories change; full edit policy in CLAUDE.md.
```

Pros: ~70 LOC saved across both rubrics; faster operator scanning; binding content (categories, anti-signals, surface map) preserved
Cons: loses some context for first-time readers — partially mitigated by the audit skills' canonical bodies which explain the cadence
Effort: Small
Risk: Low

## Recommended Action

Option 1. Both rubrics are read by the audit on every invocation; meta-prose adds tokens without adding scoring grip.

## Technical Details

- Files affected:
  - `docs/products/life-clock/premium-bar.md`
  - `docs/products/life-clock/pro-value-rule.md`
- Do NOT cut: the binding scoring content (category list, anti-signals, surface-level rubric, Pro touchpoint inventory).

## Acceptance Criteria

- [ ] Each rubric ≤ ~95 lines (down from 129/132)
- [ ] All binding scoring categories preserved
- [ ] Surface-level rubric and Pro touchpoint inventory preserved
- [ ] Anti-signals preserved
- [ ] No audit-skill fixture test fails

## Work Log

(empty)
