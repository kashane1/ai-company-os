---
description: Audit a product's current state (vision, prior polish coverage, fixture knobs, operator memory, submission readiness) and emit a ranked, variety-balanced backlog of `simulator-driven-polish` prompts. Read-only counterpart that runs BEFORE polish sessions.
canonical_source: skills/canonical/simulator-polish-recon/skill.md
---

# Simulator-Polish Recon — Claude adapter

Follow the canonical procedure at `skills/canonical/simulator-polish-recon/skill.md`. Shared contract surface (per-prompt template, variety mandate shape, operator-memory pass, output structure, cooling-off, anti-patterns) lives in `skills/canonical/shared/recon-scaffolding.md`. Read both at session start.

## Confirm before you start

Surface these inputs explicitly: `product_id`, `baseline` (default `origin/main`), `depth` (default `standard`), `focus` (optional), `also_audit_branches` (default empty), `minimum_prompts` (default 10). If the operator says "audit the app for regressions" with no qualifiers, assume `standard` depth, no focus, no branch audit. State the assumed inputs and proceed unless corrected.

## Pre-flight checks

1. `test -f docs/products/<product-id>/vision.md` — refuse if missing; route to `simulator-driven-polish` vision-driven mode.
2. `test -f skills/canonical/shared/recon-scaffolding.md` — refuse if missing; the spine is a hard dependency.
3. `ls docs/products/<product-id>/polish-*.md docs/products/<product-id>/ux-audit-*.md 2>/dev/null | wc -l` — if zero, emit a one-prompt bootstrap backlog and stop.
4. `git status --short` — clean is fine; dirty → ask.
5. `gh --version` — only if `also_audit_branches` is non-empty.

## Tools to reach for, in order

Walk the 9-step evidence stack in `skill.md` § "Observer." Steps 2, 4, 5, 6, 8 are universal (inherited from `shared/recon-scaffolding.md`); steps 1, 3, 7, 9 are recon-specific. The full read order is in the canonical body — do not reorder.

## The rhythm

Single-pass, not loop-based. After the evidence stack: build coverage matrix → Open Questions ledger → memory ledger → fixture-knob catalog → enumerate gaps → tier each gap → draft prompts hitting variety floors and the 14-day rule → compute submission-readiness flag → write the report. The file is the deliverable; the chat reply is the cover letter.

## Decision-tier reminders

Emitted prompts will be classified by the consuming `simulator-driven-polish` session. Make classification easy: `fix-list` → mostly Polish-tier; `freeform-polish` → Polish+Stretch; `vision-driven` → Feature+Vision-question; `reference-match` → Polish+Stretch.

## Quality checks before writing

Verify against `shared/recon-scaffolding.md` § "Quality checks before writing the report" — every item is binding. Plus recon-specific: submission-readiness flag computed per `skill.md` strict criteria.

## What to surface in your reply

Under 30 lines: report path, one-line state summary, submission-readiness color, prompt count + tier distribution, a 1-3 prompt "if you only run three this week" callout, one paragraph of cross-cutting patterns if any.

## Failure modes specific to Claude

- Vision.md drift between worktrees — verify `git status` matches the expected vision.md.
- Memory directory missing on fresh machine — treat as "no relevant entries"; do not refuse.
- Operator's intent is elevation or monetization — route to `premium-feel-audit` or `pro-value-audit` respectively. Recon's observer skews remedial (operator memory `feedback_simulator_polish_recon_calibration.md`).
