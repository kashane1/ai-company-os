---
id: simulator-polish-recon
name: Simulator-Polish Recon
purpose: Audit a product's current state against vision, prior polish coverage, fixture knobs, operator memory, and submission readiness; emit a ranked, variety-balanced backlog of `simulator-driven-polish` prompts ready to copy-paste. Read-only counterpart that runs BEFORE simulator-driven-polish sessions to decide what to run.
owner_agent: ios
target_runtimes: [claude]
stage: active
inputs:
  - product_id (e.g. life-clock)
  - baseline (branch or commit; default origin/main)
  - depth (quick | standard | deep — default standard)
  - focus (optional — submission-readiness | vision-questions-only | newest-surfaces-only | branch-drift | regression-sweep | <free-form>)
  - also_audit_branches (optional list — opt-in; default empty)
  - minimum_prompts (default 10; absolute floor regardless of depth)
outputs:
  - one report file at docs/products/<product-id>/polish-backlog-<YYYY-MM-DD>-<focus-slug>.md
  - 9 binding output sections per shared/recon-scaffolding.md output skeleton, with submission-readiness flag as the readiness flag
allowed_edit_boundaries:
  - docs/products/<product-id>/polish-backlog-*.md (write)
  - skills/adapters/claude/simulator-polish-recon.md (read; only edit when explicitly editing the skill itself)
forbidden_areas:
  - products/<product-id>-ios/** (read-only — this skill never edits app sources)
  - packages/policies/
  - state/
  - other products under products/
  - vision.md (entirely read-only — including Open Questions; this skill PROPOSES vision-questions in emitted prompts but does not append them itself; the operator-driven simulator-driven-polish session does the append)
preconditions:
  - docs/products/<product-id>/vision.md exists (this skill does NOT bootstrap vision.md — operator must run simulator-driven-polish in vision-driven mode first if missing)
  - docs/products/<product-id>/ contains at least one prior polish-*.md OR ux-audit-*.md (otherwise the coverage matrix is too thin — emit a one-prompt backlog telling the operator to run an initial freeform-polish pass instead)
  - skills/canonical/shared/recon-scaffolding.md exists (the shared spine this skill references)
  - working tree clean OR operator explicitly authorized dirty start
  - gh available when also_audit_branches is non-empty
dependencies:
  - canonical/shared/recon-scaffolding (foundational contract — per-prompt template, variety mandate shape, operator-memory pass, output structure, cooling-off rule, anti-patterns)
  - packages/schemas/polish_prompt.py (mechanical schema for the per-prompt template — `POLISH_PROMPT_FIELDS`)
  - canonical/simulator-driven-polish (this skill's output is consumed by that skill)
  - canonical/ios-simulator-ux-audit (older sister; recon may cite its findings as evidence)
  - operator auto-memory at .claude/projects/-Users-simons-ai-company-os/memory/ (mandatory read pass)
validation_steps:
  - report file exists at the expected path with all 9 required sections (per shared/recon-scaffolding.md output skeleton)
  - prompt count >= minimum_prompts AND <= depth ceiling (quick=20, standard=40, deep=60)
  - variety mandate satisfied OR explicit operator override logged in the report
  - per-prompt template adheres to packages/schemas/polish_prompt.py POLISH_PROMPT_FIELDS (9 fields, in order)
  - no emitted prompt's slug overlaps a polish-*.md session log dated within the last 14 days UNLESS that prior log marked "Outstanding (next session)" or "deferred"
  - every emitted prompt cites at least one piece of evidence (file_path:line, commit SHA, vision Open Question #, or prior session log slug)
  - every file path mentioned in any emitted prompt resolves in the worktree
  - coverage matrix has no empty cells (each surface gets at least a "no recent coverage — drift candidate" diagnosis)
  - memory pass was performed and the memory ledger section is present in the report (even if empty, must state "no relevant memory entries")
handoff_contract:
  what_is_handed_off: a dated polish-backlog-*.md file containing N prompts the operator can copy-paste into fresh chats invoking simulator-driven-polish
  handed_to: operator → simulator-driven-polish
  channel: docs/products/<product-id>/polish-backlog-<YYYY-MM-DD>-<focus-slug>.md (the report IS the handoff)
---

# Simulator-Polish Recon

This skill is the **discovery counterpart** to `simulator-driven-polish`. That skill drives the app live and edits. This skill reads-only, audits state, and emits the backlog of prompts the operator picks from.

This skill is a member of the **recon-family** of audit/backlog skills. The shared contract — per-prompt template, variety mandate shape, operator-memory pass, output structure, 14-day cooling-off, anti-patterns — lives in [`skills/canonical/shared/recon-scaffolding.md`](../shared/recon-scaffolding.md). The mechanical per-prompt field set is locked by [`packages/schemas/polish_prompt.py`](../../../packages/schemas/polish_prompt.py). This file defines what makes recon **recon-specific**: its observer (diff against prior polish coverage), its tier vocabulary, its readiness flag (submission-readiness).

Use it when:

- Main is up to date with no outstanding feature branches (the operator's stated discipline) and you want to know what's incomplete or regressed.
- The operator asks "audit the app for regressions / drift / submission gaps" / "what regressed" / "what's incomplete" / "build me a submission-readiness backlog" / "polish recon".
- It is the start of a new push toward App Store submission (`focus: submission-readiness`).
- A merge just landed and you want a "what regressed or what gaps are newly exposed" pass (`focus: regression-sweep`).

Do NOT use it when:

- The operator wants the app to feel **more premium** — route to `premium-feel-audit` instead. Recon's observer skews remedial; it will surface drift, not elevation gaps.
- The operator wants to audit **Pro / Paywall value** — route to `pro-value-audit` instead. Recon's tier vocabulary doesn't cover monetization-perception gaps.
- The operator has a specific fix in mind — go straight to `simulator-driven-polish` in `fix-list` mode.
- The product has zero polish session history — recon needs a baseline of prior coverage to diff against. Emit a single bootstrap-prompt backlog telling the operator to run `freeform-polish` first.

## Observer

The observer that distinguishes recon from its elevation siblings is the **diff against prior polish coverage**. Recon asks: what surfaces have been touched recently? what surfaces have NOT been touched and may have rotted? what audit-doc findings are unresolved? what branches are drifting from main?

Read in order (steps marked **shared** are defined in `shared/recon-scaffolding.md` and are universal to the recon-family; recon-specific steps are inline below):

### 1. Branch survey (recon-specific)

- `git log --oneline -30 <baseline>` (default `origin/main`)
- `git branch -a` — list local + remote branches
- For each non-merged branch: `git log --oneline <baseline>..<branch>` + `git diff --stat <baseline>..<branch>`
- Flag branches with ≥5 commits ahead as "drift candidates"
- If `also_audit_branches` is opt-in non-empty, audit each branch in depth and produce one `branch-readiness` prompt per branch
- If `also_audit_branches` is empty, mention drift candidates briefly in state-summary but do not emit prompts for them — the operator's discipline is to merge first, then recon

### 2. Vision (universal)

- Read `docs/products/<product-id>/vision.md` in full
- Extract Decided constraints into a section of the report (read-only ratchet — recon will not edit, but consumers of the emitted prompts must respect them)
- Extract Open Questions with current status (resolved / partial / open / new-since-last-recon)
- Cross-reference: which Open Questions have been touched by a polish session? Which haven't?

### 3. Prior polish coverage (recon-specific — this IS recon's observer)

- `ls docs/products/<product-id>/polish-*.md` and `docs/products/<product-id>/ux-audit-*.md`
- Also list any sibling backlog files (`premium-feel-backlog-*.md`, `pro-value-backlog-*.md`) — the cooling-off rule applies cross-skill
- For each: capture date, slug, surfaces touched, asks-left-open
- **14-day cooling-off rule** (per `shared/recon-scaffolding.md`): do not emit a prompt whose slug overlaps a session log dated within the last 14 days UNLESS that log explicitly marked it "Outstanding (next session)" / "deferred" / "V3 follow-up" or similar.
- Read at least the most recent 3 logs in full. The rest can be skim-by-headings.

### 4. Surface inventory (universal)

- List `products/<product-id>-ios/Sources/Features/**/*.swift`
- Cross-reference each top-level feature directory against polish-*.md slugs. A surface with zero matching session logs = audit-gap → emit a `new-surface` or `drift` prompt.

### 5. Test inventory (universal)

- List `products/<product-id>-ios/Tests/` and `products/<product-id>-ios/UITests/`
- Tests for a surface with no polish-*.md log = the surface exists and is even locked by tests, but has never been driven live. That's a strong signal for a `drift` prompt.

### 6. Fixture knobs (universal)

- `grep -rn "<PRODUCT>_" products/<product-id>-ios/Sources/` (whatever env-var prefix the product uses — e.g. `LIFECLOCK_`)
- Catalog every env var with its accepted values and default behavior
- Include the full catalog at the top of the emitted report so prompt-writers (and the operator) can compose them precisely

### 7. Audit doc deltas (recon-specific)

- Open `docs/products/<product-id>/ux-audit-*.md`
- For each finding, check whether there is a "Status as of <date>" addendum that matches recent commits. Findings without one are candidates for a `fix-list` recheck prompt.

### 8. Operator memory pass (universal; mandatory — per `shared/recon-scaffolding.md`)

- List `.claude/projects/-Users-simons-ai-company-os/memory/feedback_*.md` and `MEMORY.md`
- Read every file whose name suggests it could apply to the product
- For each relevant memory: log it in the report's "Memory ledger" section
- **Hard refusal**: an emitted prompt must not contradict a memory entry. If a memory entry is ambiguous, note it as a vision-question candidate instead.

### 9. Branch backlog (opt-in only; recon-specific)

- Only if `also_audit_branches` is non-empty
- For each branch: list its phase number (if any), surfaces touched, what user-visible behavior changes, merge-readiness story, blockers
- Emit one `branch-readiness` prompt per branch

## Coverage matrix (recon-specific columns)

Every surface in the inventory gets a row. Columns:

| Column | Possible values |
|---|---|
| Last polish session | YYYY-MM-DD or "never" |
| Tone-mode coverage | full (all 3) / partial / coach-only / N/A |
| Light + dark | covered / partial / never |
| Accessibility text size | covered / never |
| Fixture knob composition tested | yes / partial / never |
| Pro + Free walked | both / Pro-only / Free-only / N/A |
| Open Questions touching this surface | list of #N references or none |
| Verdict | clean / drift / regression-risk / new-surface / audit-gap |

A cell that is "never" or "partial" on a non-trivial dimension contributes to the surface's verdict.

## Tier vocabulary (binding — recon-specific)

> Note: `submission-blocker` is a cross-sibling escalation tier defined in shared/recon-scaffolding.md § Cross-sibling escalation tier. Recon-specific tiers below.

| Tier | Meaning | Variety floor (at standard depth) |
|---|---|---|
| `submission-blocker` | Without this, App Store submission cannot proceed (icon, screenshots, age-gate, subscription lifecycle, privacy disclosure UI, notification permission honesty) | ≥1 if focus=submission-readiness |
| `vision-question` | Resolves an unresolved vision Open Question | ≥1 if any Open Question is unresolved |
| `regression-risk` | Recent commits introduced or revealed a bug or polish gap | ≥1 if focus=regression-sweep |
| `new-surface` | A surface that shipped since the last recon and has no focused polish pass yet | — |
| `drift` | An old surface, no recent log, may have rotted | — |
| `branch-readiness` | Audits a branch ahead of merging back to baseline | =N where N is `len(also_audit_branches)` |
| `nice-to-have` | Quality-bar improvement, no specific deadline pressure | — |

## Variety mandate (recon-specific floors at standard depth)

Per the shape defined in `shared/recon-scaffolding.md`, recon declares these floors at standard depth:

- **≥2 `fix-list`** prompts (typically regression-risk or fix-list-ready submission-blockers)
- **≥3 `freeform-polish`** prompts (new-surface or drift)
- **≥2 `vision-driven`** prompts (always tied to a specific Open Question or Decided-constraint reading)
- **≥1 `reference-match`** prompt (App Store screenshots, icon, competitive-reference comparison) — if the product has reference assets or is targeting submission

If `focus` would force the variety mandate to slip, stop and ask per the shared rule.

## Per-prompt template (inherited)

Use the binding 9-field template defined in [`shared/recon-scaffolding.md`](../shared/recon-scaffolding.md) verbatim. Field names match `packages/schemas/polish_prompt.py` `POLISH_PROMPT_FIELDS`.

## Anti-patterns (inherited)

All anti-patterns in `shared/recon-scaffolding.md` apply to this skill verbatim.

## Output structure (inherited; 9 sections)

Use the 9-section structure from `shared/recon-scaffolding.md` verbatim. The readiness flag for this skill is **submission-readiness** — see next section for criteria.

## Submission-readiness flag — strict mode (recon-specific)

The flag is **green** only if ALL of the following hold:

- Zero unresolved `submission-blocker` prompts in the emitted backlog
- Zero unresolved `regression-risk` prompts
- All vision Decided constraints have at least one polish session log demonstrating compliance
- App icon, launch screen, and submission-resolution screenshots exist as artifacts
- Age-gate path audited within the last 30 days
- Subscription lifecycle (restore, cancel, expire, refund) audited within the last 30 days
- Privacy disclosure UI / data-export / delete-my-data path exists
- HealthKit denied + notDetermined paths audited within the last 30 days (if the product uses HealthKit)

Anything short of green is **yellow** (some blockers) or **red** (many blockers or no recent submission-tier work at all). The flag is stable across sessions — if last week's flag was green and nothing regressed, this week's is green.

## Operator interactions

This skill is mostly silent — its output is the report, not a dialogue. The two times it should ask:

1. **Variety mandate conflict.** If `focus` would force the mandate to slip, ask before relaxing.
2. **Empty `also_audit_branches` with visible drift.** If the branch survey finds branches ≥5 commits ahead and `also_audit_branches` is empty, mention the drift in state-summary and offer to re-run with the branches included. The operator's stated discipline is to merge first, so default behavior is to skip.

All other findings flow into the report. The skill does not chat them mid-run.

## Failure modes (recon-specific)

- **Missing vision.md** — refuse with a one-line message telling the operator to run `simulator-driven-polish` in `vision-driven` mode first (which bootstraps the vision doc).
- **Missing shared/recon-scaffolding.md** — refuse; the shared spine is a hard dependency.
- **No prior polish coverage** — emit a 1-prompt backlog: "run `freeform-polish` against the whole app to establish a baseline; re-run recon afterward."
- **Memory pass produces a contradiction** — escalate to operator immediately. Do not silently drop the conflicting prompt.
- **Branch audit fails** (e.g. `gh` unavailable) — note the failure in state-summary; emit prompts for main only.
- **Operator's intent is elevation, not remediation** — route to `premium-feel-audit`. (Recon's prior-coverage-diff observer skews remedial on already-polished products; this was captured in operator memory `feedback_simulator_polish_recon_calibration.md`.)
- **Operator's intent is monetization audit** — route to `pro-value-audit`.

## Same-day collision rule

Inherited from `shared/recon-scaffolding.md`: append `-2`, `-3`, etc. to the filename slug, not to the date.

## Cadence

Recommended invocation cadence:

- Weekly on main when main is up to date
- After any merge of a feature branch (with `focus: regression-sweep`)
- Before an App Store submission push (with `focus: submission-readiness`)
- After completing a vision Open Question (with `focus: vision-questions-only`) to see what's newly unblocked

Do not invoke daily — the 14-day cooling-off rule will produce thin, repetitive backlogs.
