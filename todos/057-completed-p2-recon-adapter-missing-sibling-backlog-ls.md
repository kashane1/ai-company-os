---
status: pending
priority: p2
issue_id: "057"
tags: [code-review, skills, audit-fork, recon, adapter]
dependencies: []
---

# Problem Statement

`skills/adapters/claude/simulator-polish-recon.md` pre-flight step lists `polish-*.md` and `ux-audit-*.md` files but does not list the sibling-emitted backlog files (`premium-feel-backlog-*.md` and `pro-value-backlog-*.md`). The shared scaffold says the 14-day cooling-off rule applies cross-skill — so recon's pre-flight must surface sibling backlog files to make that rule actionable.

Right now an LLM running recon sees only its own and the legacy ux-audit history, so the cross-skill rule is honor-system at best.

## Findings

- **architecture-strategist:** "The recon adapter currently lists only `polish-*.md` and `ux-audit-*.md`; it should also `ls premium-feel-backlog-*.md pro-value-backlog-*.md` so the model literally sees siblings. Currently `simulator-polish-recon.md` adapter step 3 misses two of three sibling outputs."

Note: this is symmetric — premium-feel-audit and pro-value-audit adapters should also list each other's backlog files plus recon's polish-backlog.

## Proposed Solutions

### Option 1: Update all three adapter pre-flight ls commands to be sibling-aware

For all three recon-family adapters:
- Pre-flight `ls` step should list ALL backlog file patterns: `polish-*.md`, `ux-audit-*.md`, `polish-backlog-*.md`, `premium-feel-backlog-*.md`, `pro-value-backlog-*.md`.
- The rationale ("the 14-day cooling-off rule applies cross-skill") is documented inline.

Pros: makes the rule visible to the LLM; uniform across siblings
Cons: minor adapter bloat
Effort: Trivial
Risk: None

## Recommended Action

Option 1. All three adapters get a unified `ls` command, with a brief inline comment naming the cross-skill cooling-off as the reason.

## Technical Details

- Files affected:
  - `skills/adapters/claude/simulator-polish-recon.md` (pre-flight step 3)
  - `skills/adapters/claude/premium-feel-audit.md` (pre-flight)
  - `skills/adapters/claude/pro-value-audit.md` (pre-flight)

## Acceptance Criteria

- [ ] All three adapters' pre-flight `ls` commands list the same five backlog file patterns
- [ ] Each adapter includes a one-line note: "Cross-skill cooling-off applies — list every sibling's backlog files."
- [ ] Existing fixture tests still pass (these are runtime adapter notes, not contract-frozen content).

## Work Log

(empty)
