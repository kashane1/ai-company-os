---
description: Audit a product's current state (vision, prior polish coverage, fixture knobs, operator memory, submission readiness) and emit a ranked, variety-balanced backlog of `simulator-driven-polish` prompts. Read-only counterpart that runs BEFORE polish sessions.
canonical_source: skills/canonical/simulator-polish-recon/skill.md
---

# Simulator-Polish Recon — Claude adapter

Follow the canonical procedure at `skills/canonical/simulator-polish-recon/skill.md`. This adapter is Claude-specific runtime guidance — read it once at session start, then drive off the canonical body for the contract.

This is the **discovery** counterpart to `simulator-driven-polish`. That skill drives the app live and edits. This one is read-only and produces a backlog of prompts the operator picks from.

## Confirm before you start

Surface these inputs explicitly (do not silently guess):

- `product_id` and the product path under `products/<product-id>-ios/`
- `baseline` — branch or commit (default `origin/main`)
- `depth` — `quick` (≤20) | `standard` (≤40, default) | `deep` (≤60)
- `focus` (optional) — `submission-readiness` | `vision-questions-only` | `newest-surfaces-only` | `branch-drift` | `regression-sweep` | free-form
- `also_audit_branches` (optional list — opt-in; default empty per the operator's stated discipline)
- `minimum_prompts` (default 10 — hard floor)

If the operator says "audit the app" with no qualifiers, assume `standard` depth, no focus, no branch audit. Confirm by stating the assumed inputs in your first message and proceeding unless corrected.

## Pre-flight checks

Before reading anything:

1. **Vision doc exists?** `test -f docs/products/<product-id>/vision.md`. If missing → refuse; route the operator to `simulator-driven-polish` in `vision-driven` mode to bootstrap.
2. **Prior polish coverage exists?** `ls docs/products/<product-id>/polish-*.md docs/products/<product-id>/ux-audit-*.md 2>/dev/null | wc -l`. If zero → emit a one-prompt bootstrap backlog and stop.
3. **Working tree state.** `git status --short`. Clean is fine. Dirty → ask before proceeding.
4. **gh available?** Only if `also_audit_branches` is non-empty. Run `gh --version`.

## Tools to reach for, in order

**Read the evidence stack (canonical step order — do not reorder):**

- `git log --oneline -30 <baseline>` + `git branch -a` + per-branch `git log --oneline <baseline>..<branch>` (step 1)
- `Read` on `docs/products/<product-id>/vision.md` — full file (step 2)
- `ls docs/products/<product-id>/polish-*.md` + `Read` the most recent 3 in full, the rest by heading skim (step 3)
- `ls` the Features dir + `ls` Tests + UITests; build a surface→last-touched map (steps 4–5)
- `grep -rn "<PRODUCT_ENV_PREFIX>_" products/<product-id>-ios/Sources/` — catalog fixture knobs (step 6)
- `Read` the most recent `ux-audit-*.md` for status-addendum check (step 7)
- `ls ~/.claude/projects/-Users-simons-ai-company-os/memory/` + `Read` every relevant `feedback_*.md` — MANDATORY, never skipped (step 8)
- Only if opted in: per-branch `git log` + `git diff --stat` + `gh pr view` to capture branch state (step 9)

**Skill chaining you may want:**

- `canonical/repo-onboarding` — only if recon is being run on a product you haven't touched in this session. Recon is usually run in an established context, so this is rare.
- `canonical/context-budget` — never inline; only if the report itself is bloating the lane.

## The rhythm (no per-iteration loop — this is a single pass)

Recon is single-pass, not loop-based. Order of operations:

1. Run pre-flight checks. If any fail, stop and report.
2. Run the evidence stack steps 1 through 9 (or 1 through 8 if no branch audit). Capture observations in scratch as you go.
3. Build the coverage matrix from the surface inventory cross-referenced against polish coverage.
4. Build the Open Questions ledger from vision.md.
5. Build the Memory ledger from step 8.
6. Build the fixture knob catalog from step 6.
7. Enumerate gaps. Tier each gap.
8. Draft prompts using the binding template. Hit the variety mandate floors. Respect the 14-day cooling-off rule.
9. Compute the submission-readiness flag against the strict criteria.
10. Write the report to `docs/products/<product-id>/polish-backlog-<YYYY-MM-DD>-<focus-slug>.md`.
11. Surface the report path + state-summary paragraph + readiness color + prompt count to the operator. That's your reply. Do not chat the prompts inline — the file is the deliverable.

## Decision tier reminders (carried from simulator-driven-polish)

The emitted prompts will be classified Polish / Stretch / Feature / Vision-question by the *consuming* simulator-driven-polish session. Recon's job is to make sure that classification is easy: each emitted prompt should make it obvious which tier its findings will land in.

Specifically:

- `fix-list` prompts → almost entirely Polish-tier work
- `freeform-polish` prompts → Polish + Stretch mix
- `vision-driven` prompts → Feature + Vision-question mix
- `reference-match` prompts → Polish + Stretch (since reference is intent, not new feature)

## Quality checks before writing the report

Before writing the file, verify:

- [ ] Prompt count `>= minimum_prompts` and `<= depth_ceiling`
- [ ] Variety floors met (≥2 fix-list, ≥3 freeform-polish, ≥2 vision-driven, ≥1 reference-match if applicable)
- [ ] Every prompt has all 8 binding fields
- [ ] Every prompt cites at least one piece of evidence
- [ ] No 14-day overlap unless prior log explicitly deferred
- [ ] Memory ledger present (even if empty, must state "no relevant entries")
- [ ] Coverage matrix has no empty cells
- [ ] Submission-readiness flag computed against strict criteria
- [ ] No contradictions with vision Decided constraints or operator memory

If any check fails, fix before writing. Do not write a half-valid report and apologize in the body.

## What to surface in your reply (after writing)

Keep it to a tight summary, not a re-statement of the report:

- Report path
- One-line state summary (the same one you wrote into the report's section 1)
- Submission-readiness color
- Prompt count + tier distribution as a one-line table
- A 1–3-prompt "if you only run three this week" callout pulled from recommended-sequencing
- One paragraph of "patterns I noticed" if any cut across multiple prompts (this is the Stretch-tier observation the operator might miss by skimming)

Total reply length: aim for under 30 lines. The file is the artifact; the chat reply is the cover letter.

## Failure modes specific to Claude

- **Vision.md drift between worktrees.** If you're on a worktree branch, double-check `git status` shows you're reading the vision.md you expect.
- **Memory directory missing on a fresh machine.** The path `~/.claude/projects/.../memory/` may not exist for new operators. Treat absent directory as "no relevant entries" and proceed; do not refuse.
- **Stale fixture-knob grep when env-var prefix differs.** Default to `LIFECLOCK_` only for life-clock. For other products, grep for the product slug uppercased + underscore, or let the operator declare the prefix in the input.
- **PR-comment context is high-signal but high-cost.** If `also_audit_branches` is opted in, only fetch full PR comments for branches that have an open PR. Skip closed/draft.
- **Multi-product future.** When this skill grows beyond life-clock, `also_audit_branches` may legitimately include branches that touch a different product than the one being audited. Drop those at intake — recon is scoped to one product per invocation.
