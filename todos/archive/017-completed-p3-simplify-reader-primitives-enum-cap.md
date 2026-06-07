---
status: completed
priority: p3
issue_id: "017"
tags: [code-review, simplicity, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The second-pass simplicity review argued the deepening spent roughly half of its 60% scope cut back on defense-in-depth rigor for threats that aren't in the threat model. Several items are candidates for a pre-implementation trim. None are blocking (hence P3), but worth revisiting before Phase 1 kickoff.

## Findings

Code-simplicity-reviewer second pass ranked cuts (most aggressive first):

1. **Collapse four reader primitives into one `skill_reader.py`, or defer three of them.** Agent-native parity argument is cargo-culted from Hermes `dispatch_health_reader.py`. Prove each is needed by a real Codex/ACP caller before shipping. Agent-native reviewer disagrees — their position is "ship them so the boundary is documented". Tension unresolved; flag for human decision.

2. **Merge `AREA_NOT_FOUND` + `AREA_OUTSIDE_REPO` into `INVALID_AREA_PATH`.** Same skill, same raise site, same operator response. Five enum members instead of six.

3. **Drop `max_changed_files = 200` + `CHANGED_SURFACE_TOO_LARGE`.** Theoretical performance concern with no measured bottleneck. Current repo PRs nowhere near 200 files. Add the cap if a run blows the 3s budget.

4. **Delete the Phase 3 diff-audit DoD line.** `git diff HEAD~1..HEAD -- <paths>` is a wishful constraint; nothing enforces it mechanically. Either wire it into CI or drop the pretense.

5. **Drop the Phase 4 Hermes-observation-window precondition.** Theoretical coordination concern. Record the SHA in the baseline and proceed. If a real collision surfaces, defer then.

6. **Prune duplicate risk-table rows.** Path-traversal, AREA_OUTSIDE_REPO, and secrets-redaction rows all re-assert content from Enhancement Summary bullets 7–9.

## Proposed Solutions

### Option 1: Apply cuts 2, 3, 4, 6 and keep 1, 5

- Merge AREA enum members (trivial)
- Drop max_changed_files cap (add back if Phase 3 smoke shows 3s budget pressure)
- Delete diff-audit DoD line (replace with a Phase 3 checklist bullet: "reviewer manually checks that post-run-validation + reconciliation are unchanged")
- Prune duplicate risk rows (editorial)
- Keep all four reader primitives (agent-native parity argument still applies)
- Keep Hermes observation-window precondition (architecture strategist makes the same point — not purely theoretical)

Pros:
- Reduces surface by ~4 small items
- Preserves the structural decisions that had independent support from multiple reviewers

Cons:
- Doesn't fully adopt the simplicity reviewer's cut list

Effort: trivial (plan doc edits)
Risk: low

### Option 2: Apply all simplicity cuts aggressively

Trim everything the simplicity reviewer flagged. Bigger scope reduction but loses some independently-justified items.

Pros:
- Maximum simplification

Cons:
- Undoes architecture strategist and agent-native reviewer recommendations

Effort: small
Risk: medium (loses defense in depth)

## Recommended Action

Option 1. Apply cuts 2-6 before Phase 1 kickoff as a plan-doc edit. Flag cut 1 (reader primitives collapse) for human decision since it's a multi-reviewer tension.

## Acceptance Criteria

- [ ] `AREA_NOT_FOUND` + `AREA_OUTSIDE_REPO` merged into `INVALID_AREA_PATH`
- [ ] `max_changed_files` cap removed from Phase 3 contract (add back if smoke shows 3s pressure)
- [ ] Phase 3 diff-audit DoD line replaced with a reviewer checklist bullet
- [ ] Risk-table rows deduplicated against Enhancement Summary bullets
- [ ] Decision captured: reader-primitive count stays at 4, documented rationale in Phase 2a section
- [ ] Hermes observation-window precondition stays (architecturally justified)

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Second-pass simplicity reviewer's cut list surfaces as P3 because none of the items are blocking — they are pre-implementation trimming opportunities.
