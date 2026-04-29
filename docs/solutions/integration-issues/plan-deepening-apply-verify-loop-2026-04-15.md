---
title: "Plan-Deepening + Technical-Review + Apply + Verify Loop"
category: integration-issues
date: 2026-04-15
tags:
  - workflow
  - planning
  - deepening
  - technical-review
  - replace-all-trap
  - reality-check
  - compound-engineering
  - meta-process
related:
  - docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md
  - docs/2026-04-14-everything-claude-code-gap-analysis.md
  - docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md
---

# Plan-Deepening + Technical-Review + Apply + Verify Loop

A four-pass workflow for taking a first-draft implementation plan to ship-ready state, captured from the 2026-04-15 development of [the ECC gap recommendations plan](/Users/simons/ai-company-os/docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md). The plan grew from 540 lines (first pass) to 794 lines (final), survived three rounds of multi-agent review, and surfaced ~45 raw findings that consolidated into 16 actionable todos. The workflow itself is the lesson.

## Problem statement

Single-pass plan writing produces plans that look complete but ship with hidden assumptions, missed constraints, and unspecified failure modes. Single-pass review catches obvious issues but misses cross-cutting concerns. The compound-engineering pipeline already has `/workflows:plan` and `/workflows:deepen-plan` and `/workflows:review` as separate skills, but the **interaction sequence** between them is not documented. Without an explicit loop, you either:

- Stop after `/workflows:plan` and ship a thin plan
- Stop after `/workflows:deepen-plan` and ship a deepened plan with no validation
- Run reviews ad hoc and don't apply the findings
- Apply findings without verifying the apply pass landed correctly

The pattern below was the one that produced a plan all reviewers signed off on without unresolved blockers.

## The four-pass loop

### Pass 1 — First draft (`/workflows:plan`)

Standard `/workflows:plan` invocation. Output: a structured but **explicitly first-pass** plan. Defer all deepening — get the structural skeleton right (phases, deliverables, DoD, risks, sources) without trying to anticipate every concern.

**Critical rule:** mark the plan as first-pass in the Overview. This sets reviewer expectations correctly downstream.

### Pass 2 — Deepening (`/workflows:deepen-plan`)

Launch 8-12 parallel review/research agents, each with a focused prompt. Use a mix of domain-specific reviewers (kieran-python-reviewer, security-sentinel, performance-oracle, data-integrity-guardian) and discovery agents (Explore for reality checks, learnings-researcher for `docs/solutions/` hits, framework-docs-researcher for current API surfaces).

**Rules that worked:**

- **Brief each agent like a smart colleague who just walked into the room.** Self-contained prompts, ~300-500 words each. Include exact file paths, exact concerns to verify, and an explicit word cap on the response.
- **Pair domain reviewers with discovery agents.** Domain reviewers tell you *what's wrong*; discovery agents tell you *whether the problem is real*. The Explore-agent reality check (see "Reality-check pattern" below) was one of the most load-bearing findings.
- **Synthesize, don't accumulate.** ~45 raw findings consolidated into ~12 binding edits. Skip findings that contradict each other; flag the contradiction for human resolution.
- **Add findings as new sections, not body rewrites.** Insert "Enhancement Summary" as a new top-level section after the title. Insert per-phase "Deepening Findings (date)" subsections at the end of each phase's existing content. The audit trail stays visible; the original plan stays intact.

Output: the plan grows by ~30-50%. Original is preserved underneath the deepening additions.

### Pass 3 — Technical review (`/workflows:review`)

Second-pass review against the **deepened** plan. Use a different agent mix:

- **Re-run the simplicity reviewer** specifically against the deepening additions. Deepening adds rigor; simplicity finds the parts that didn't need to be added. The pendulum swing is the point.
- **Run the spec-flow-analyzer** for the first time. Flow gaps are different from rigor gaps — they emerge once the substance is dense enough to compose.
- **Re-run the architecture strategist** to verify the deepening's architectural additions are sound. First-pass architecture review covered the body; second-pass covers the deepening.
- **Skip agents that already saturated** (kieran-python-reviewer at this stage will mostly echo first-pass findings).

Findings get written to `todos/` as numbered files: `NNN-pending-pX-description.md`. Each todo has a Problem Statement, Proposed Solutions, Recommended Action, Acceptance Criteria. Bundle small related findings into themed todos (e.g., "Python idiom conformance" bundles 5 small rules) — one todo per finding produces unmaintainable lists.

Output: 16 todos for the ECC gap plan. P1/P2/P3 split: 5/8/3.

### Pass 4 — Apply + verify

Apply all "best fit" recommendations from the todos to the plan body. Run **one more verification pass** with two-three agents whose explicit prompt is "verify the applied edits landed correctly, NOT find new findings".

**Critical rule:** the verification pass must explicitly close-or-reject every concern from the prior review. If the verification pass finds new concerns, decide whether to apply them in another loop or accept them as deferred. Don't let the loop run forever — each iteration should be smaller than the last.

**Output of the verification pass on the ECC plan:**
- 6/6 architecture concerns from prior review verified closed
- 4/4 simplicity-reviewer cuts verified applied
- 1 NEW concern found: residual `state/benchmarks/` references in Phase 4 (4 lines), broken self-replacements in the Revisions changelog (2 lines), duplicate god-object risk row (1 row) → all fixed in the same verification turn

The verification pass is the difference between "I think the plan is ready" and "two reviewers signed off and everything they checked is verifiably true."

## The replace_all-on-changelog trap

**The most concrete reusable lesson from this session.**

When applying a global rename to a markdown file via `Edit` with `replace_all=true`, the rename also fires inside any **Revisions / Changelog / Migration notes section** that documents the rename. The result is broken self-replacements like:

```
- `state/health/skill-estate/` replaced with `state/health/skill-estate/` in every reference.
- `system_prompt` lane renamed to `system_prompt` lane with expanded scope.
```

These are not visually obvious in a 794-line file. They survived the first verification pass and only got caught when the second verification pass explicitly looked for `system_prompt → system_prompt` style typos.

### How it bit me

The ECC gap plan's apply pass had two replace_all renames:

1. `state/benchmarks/skill-estate/` → `state/health/skill-estate/`
2. `claude_md` → `system_prompt`

Both happened **after** I had written a "Technical Review Revisions" section that documented the renames in prose ("`state/benchmarks/skill-estate/` replaced with `state/health/skill-estate/`"). The `replace_all` swept through the prose and produced self-replacements. Worse: the prose was the audit trail, so the broken self-replacements ALSO destroyed the documentation of what had changed.

### Workarounds (in order of preference)

1. **Write the changelog/revisions section AFTER applying the rename.** Best option. The new values are stable by then; nothing to break.
2. **Write the changelog with one of the values escaped or paraphrased.** Use "originally `claude_md`, now renamed" instead of literally writing both values. The grep pattern won't match the paraphrase.
3. **Use `replace_all=false` and edit each occurrence individually.** Slower but safer. Use this when the file contains documentation of the rename you're about to do.
4. **Diff-check after every replace_all on documentation files.** `grep -n "X → X\|X.*X.*every"` to catch self-replacements before they ship.

### The detection pattern

If you've done a `replace_all` on a markdown file that contains a Revisions/Changelog/Migration notes section, run this immediately after:

```bash
# Find self-replacements (the typo pattern)
grep -nE 'NEW_VALUE \(?-?>?\)? \*?\*?NEW_VALUE\*?\*?' file.md
grep -nE 'NEW_VALUE.*replaced with.*NEW_VALUE' file.md
grep -nE 'NEW_VALUE.*renamed to.*NEW_VALUE' file.md
```

If anything matches, you have broken self-replacements to fix manually.

## The reality-check Explore-agent pattern

**The most load-bearing finding from the deepening pass.**

When a plan claims "X is a real problem in this codebase that we need to fix", launch a focused Explore agent against the live repo to verify the claim. Cost: one agent invocation. Value: prevents building solutions to imaginary problems.

### How it worked on the ECC gap plan

The plan's Phase 2 (`skill-stocktake`, `context-budget`) was justified by the claim "the repo has skills with orphan files, dangling project-skill pointers, and CLAUDE.md trigger-phrase drift." An Explore agent ran the four checks:

| Check | Plan claimed | Actual |
| ----- | ------------ | ------ |
| Orphan canonical files not in registry | "common" | 0 |
| Dangling `project_skill` pointers | "common" | 0 (10/10 resolve) |
| Trigger phrases referencing missing adapters | "common" | 0 (10/10 valid) |
| Orphan adapter files with no registry entry | "common" | 0 |

**Verdict: drift pain is NOT REAL today.** Phase 2 stayed in the plan but was reframed from "corrective" to "preventive medicine". The DoD got trimmed accordingly: live-registry integration tests are allowed to fail on first landing because there's nothing to catch yet, and the threshold-setting ceremony got deferred entirely.

Without the reality check, Phase 2 would have shipped with thresholds set against the imaginary baseline and tests gated against the imaginary drift list. The plan would have looked complete but immediately failed on first run.

### When to launch a reality check

Any time a plan's Problem Statement contains a quantified or qualitative claim about the codebase. Examples:

- "Workers investigate the repo from scratch every time" → grep for evidence of duplication
- "Tests are flaky in module X" → run the test 10 times against main
- "Performance is bottlenecked at function Y" → profile before optimizing
- "The codebase has many instances of pattern Z" → grep for actual count

The reality check costs one agent invocation. The cost of building a solution to an imaginary problem is the entire implementation phase.

## The pendulum-swing rule for review passes

Each review pass alternates between **add detail** and **cut detail**. The plan oscillates toward a balance:

- Pass 1 (first draft): minimal, 540 lines
- Pass 2 (deepening): adds rigor, ~30-50% growth, 730 lines
- Pass 3 (technical review): cuts what didn't carry weight, 16 todos including 6 P3 simplifications
- Pass 4 (apply + verify): nets the cuts and the rigor, 794 lines

If a pass only adds OR only cuts, you're not running the loop right. Deepening that doesn't get trimmed produces an overengineered plan; trimming that doesn't get re-deepened produces a thin plan.

The simplicity reviewer is the load-bearing component here — running it specifically against the **deepened** plan (not the original) is what makes the cut pass land on the right targets. A simplicity review of the first-pass plan tells you what the plan should NOT add; a simplicity review of the deepened plan tells you what was added that didn't carry weight. Both are valuable; neither substitutes for the other.

## The "audit trail as new sections" pattern

Rather than rewriting the plan body during deepening or technical review, **add new top-level sections that document the changes**:

```
# Plan Title
## Enhancement Summary           ← deepening pass adds this
## Technical Review Revisions    ← technical review adds this
## Overview                      ← original first-pass content begins here
## Problem Statement
## Phase 0
   ### Deepening Findings        ← deepening adds per-phase subsection
   ### Technical Review Edits    ← technical review adds per-phase subsection
## Phase 1
...
```

Why this works:

- **Audit trail is visible** without diff archaeology
- **Original first-pass content stays intact** so the reasoning that produced it is still readable
- **Reviewers can see the history** of why each rule was added
- **Future plan-deepening sessions** can reference the sections by name when evaluating "did the prior pass close this concern?"

Cost: the plan is ~30% longer than a freshly-rewritten version would be. Benefit: every line of additional length is institutional memory, not rewrite churn.

## Outcome on the ECC gap plan

- **Plan size:** 540 → 794 lines (47% growth across all four passes)
- **Reviewers run:** ~17 unique agents across deepening + technical review + verification
- **Findings raised:** ~45 raw findings consolidated into 16 actionable todos (5 P1, 8 P2, 3 P3)
- **Verification result:** 6/6 architecture concerns closed, 4/4 simplicity cuts applied, 1 new concern found (residual rename references) and fixed in the same pass
- **Ship-readiness:** both verification reviewers signed off without unresolved blockers
- **Time cost:** estimated ~3-4 hours of agent execution + synthesis, vs ~1 hour for a single-pass plan

The 3x time cost produced a plan that has no known unresolved questions before Phase 1 implementation begins. The implementation can proceed against a stable target instead of discovering gaps mid-build.

## When to use this loop

- **Yes:** non-trivial implementation plans (>200 LOC of new platform code, multi-phase, touches policy / orchestration / persistence)
- **Yes:** plans that ship policy primitives (anything under `packages/policies/`)
- **Yes:** plans that introduce new canonical skills (anything under `skills/canonical/`)
- **No:** small bug fixes (use the standard plan workflow, single pass)
- **No:** UI tweaks that have a clear visual outcome (the visual is the verification)
- **No:** spike work where the goal is exploration, not commitment

## Prevention strategies

For future plans that go through this loop:

1. **Mark first-pass plans explicitly** in the Overview section. Sets reviewer expectations.
2. **Brief deepening agents like colleagues**, not like CLI tools. Self-contained prompts with file paths and word caps.
3. **Always pair domain reviewers with discovery agents.** The reality check is non-negotiable.
4. **Add findings as new sections**, never as body rewrites.
5. **Run the simplicity reviewer twice** — once against first-pass, once against deepened.
6. **The verification pass is mandatory.** "I think the plan is ready" is not the same as "two reviewers signed off and everything they checked is verifiably true."
7. **When applying replace_all to a doc with a changelog section**, write the changelog AFTER the rename or use paraphrase patterns to avoid self-replacements.

## Cross-references

- [The ECC gap plan that produced this learning](/Users/simons/ai-company-os/docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md) — see Enhancement Summary + Technical Review Revisions sections for the in-place audit trail
- [The Hermes platform upgrade plan](/Users/simons/ai-company-os/docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md) — first plan in this repo to use the deepening pass, ~1300 lines, 12 parallel deepening agents
- [The everything-claude-code gap analysis](/Users/simons/ai-company-os/docs/2026-04-14-everything-claude-code-gap-analysis.md) — the source document that motivated the ECC gap plan
- The 16 todos generated by the technical review: `todos/004-pending-p1-*.md` through `todos/019-pending-p3-*.md`
