---
description: Audit a product's elevation gaps against `premium-bar.md` rubric, vision, prior polish coverage, and operator memory; emit a ranked, variety-balanced backlog of `simulator-driven-polish` prompts focused on motion / haptics / typography / transitions / empty-state / loading / lighting / microcopy coherence. Sibling of `simulator-polish-recon` (which does remedial discovery).
canonical_source: skills/canonical/premium-feel-audit/skill.md
---

# Premium Feel Audit — Claude adapter

Follow the canonical procedure at `skills/canonical/premium-feel-audit/skill.md`. Shared contract (per-prompt template, variety mandate shape, operator-memory pass, output structure, cooling-off, anti-patterns) is in `skills/canonical/shared/recon-scaffolding.md`. Read both at session start.

## Confirm before you start

Surface these inputs explicitly: `product_id`, `baseline` (default `origin/main`), `depth` (default `standard`), `focus` (optional: motion-only / haptics-only / typography-only / transitions-only / empty-states-only / free-form), `minimum_prompts` (default 10). If the operator says "make it feel premium" with no qualifiers, assume `standard` depth, no focus.

## Pre-flight checks

1. `test -f docs/products/<product-id>/premium-bar.md` — REFUSE if missing; operator must author rubric first.
2. `test -f docs/products/<product-id>/vision.md` — refuse if missing.
3. `test -f skills/canonical/shared/recon-scaffolding.md` — refuse if missing.
4. `ls docs/products/<product-id>/polish-*.md docs/products/<product-id>/ux-audit-*.md 2>/dev/null | wc -l` — if zero, emit one-prompt bootstrap backlog.
5. Rubric stub check: `wc -l docs/products/<product-id>/premium-bar.md` should be ≥80 with category content; stub-headers-only → emit one-prompt bootstrap.

## Tools to reach for, in order

Walk the 9-step observer in `skill.md` § "Observer." Steps 1, 3, 4, 9 are elevation-specific; steps 2, 5, 6, 7, 8 are universal (inherited from `shared/recon-scaffolding.md`).

## The rhythm

Single-pass. After the observer steps: build elevation-specific coverage matrix → Open Questions ledger → memory ledger → fixture-knob catalog → enumerate gaps category-by-category → tier each gap → draft prompts hitting variety floors → compute premium-readiness flag → write the report. The file is the deliverable.

## Decision-tier reminders

Emitted prompts will be classified by the consuming `simulator-driven-polish` session. Most premium-feel prompts land in Stretch tier (auto-with-note) rather than Polish — premium changes deserve operator review even when small. `vision-driven` prompts always land in Feature or Vision-question tier.

## Quality checks before writing

Verify against `shared/recon-scaffolding.md` § "Quality checks before writing the report" — every item binding. Plus elevation-specific:

- Every prompt cites `premium-bar.md` + a specific category as `Evidence`.
- No prompt introduces a category not in the rubric (if needed, escalate to `vision-question` proposing the operator add the category).
- Premium-readiness flag computed per `skill.md` strict criteria.

## What to surface in your reply

Under 30 lines: report path, one-line state summary, premium-readiness color, prompt count + tier distribution, a 1-3 prompt "if you only run three this month" callout, one paragraph of cross-cutting elevation themes if any.

## Failure modes specific to Claude

- **Rubric stub** — refuse politely; the audit can't manufacture rubric content. Route the operator to flesh out `premium-bar.md`.
- **Operator wants regression audit** — route to `simulator-polish-recon`.
- **Operator wants Pro audit** — route to `pro-value-audit`.
- **Memory directory missing on fresh machine** — treat as "no relevant entries"; do not refuse.
