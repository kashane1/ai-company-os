---
description: Audit a product's Pro discoverability, justification, perceived depth, friction-to-trial, upsell-moment usage, trust signals, and value-claim accuracy against `pro-value-rule.md` (which operationalizes MONETIZATION.md's Free/Pro rule); emit a ranked, variety-balanced backlog of `simulator-driven-polish` prompts focused on monetization quality. Sibling of `simulator-polish-recon` (remedial) and `premium-feel-audit` (elevation).
canonical_source: skills/canonical/pro-value-audit/skill.md
---

# Pro-Value Audit — Claude adapter

Follow the canonical procedure at `skills/canonical/pro-value-audit/skill.md`. Shared contract (per-prompt template, variety mandate shape, operator-memory pass, output structure, cooling-off, anti-patterns) is in `skills/canonical/shared/recon-scaffolding.md`. Read both at session start.

## Confirm before you start

Surface these inputs explicitly: `product_id`, `baseline` (default `origin/main`), `depth` (default `standard`), `focus` (optional: paywall-only / discoverability-only / trust-only / value-claim-accuracy / upsell-moments / free-form), `minimum_prompts` (default 10). If the operator says "audit Pro" with no qualifiers, assume `standard` depth, no focus.

## Pre-flight checks

1. `test -f docs/products/<product-id>/pro-value-rule.md` — REFUSE if missing; operator must author rubric first.
2. `test -f docs/products/<product-id>/MONETIZATION.md` — REFUSE if missing; the rubric references it as source of truth.
3. `test -f docs/products/<product-id>/vision.md` — refuse if missing.
4. `test -f skills/canonical/shared/recon-scaffolding.md` — refuse if missing.
5. `ls docs/products/<product-id>/polish-*.md docs/products/<product-id>/ux-audit-*.md 2>/dev/null | wc -l` — if zero, emit one-prompt bootstrap.
6. Rubric stub check: `wc -l docs/products/<product-id>/pro-value-rule.md` should be ≥80 with category content + Pro touchpoint inventory; stub-headers-only → one-prompt bootstrap.
7. Rubric/MONETIZATION drift check: verify `pro-value-rule.md` "Free/Pro rule (verbatim)" section matches MONETIZATION.md. Drift → refuse with explicit report.

## Tools to reach for, in order

Walk the 9-step observer in `skill.md` § "Observer." Steps 1, 2, 4, 5, 9 are monetization-specific; steps 3, 6, 7, 8 are universal (inherited from `shared/recon-scaffolding.md`).

## The rhythm

Single-pass. After the observer steps: build monetization-specific coverage matrix → Open Questions ledger → memory ledger → fixture-knob catalog → enumerate gaps per category per touchpoint → tier each gap → ESCALATE trust-gap and pro-rule-violation to submission-blocker tier → draft prompts hitting variety floors → compute pro-value-readiness flag → write the report.

## Decision-tier reminders

Emitted prompts will be classified by the consuming `simulator-driven-polish` session. Most pro-value prompts land in Stretch or Feature tier (rarely Polish) — monetization changes warrant operator review even when small. `trust-gap` and `pro-rule-violation` always land in Feature (Always Ask) tier; the operator must approve before changes.

## Quality checks before writing

Verify against `shared/recon-scaffolding.md` § "Quality checks before writing the report" — every item binding. Plus monetization-specific:

- Every prompt cites `pro-value-rule.md` + a specific category + a specific Pro touchpoint as `Evidence`.
- No prompt proposes a Free→Pro move that violates MONETIZATION.md's Free/Pro rule (if needed, escalate to `vision-question` proposing a MONETIZATION.md edit).
- `trust-gap` and `pro-rule-violation` findings are surfaced in the executive summary, not buried in the prompt list.
- Pro-value-readiness flag computed per `skill.md` strict criteria.

## What to surface in your reply

Under 30 lines: report path, one-line state summary, pro-value-readiness color, prompt count + tier distribution, a 1-3 prompt "if you only run three this month" callout (always include any trust-gap or pro-rule-violation findings first regardless of count), one paragraph of cross-cutting monetization themes if any.

## Failure modes specific to Claude

- **Rubric stub** — refuse politely; route operator to flesh out the rubric.
- **Rubric/MONETIZATION drift** — refuse with explicit drift report; do not pick a side.
- **Operator wants regression audit** — route to `simulator-polish-recon`.
- **Operator wants premium-feel audit** — route to `premium-feel-audit`.
- **Memory directory missing on fresh machine** — treat as "no relevant entries"; do not refuse.
