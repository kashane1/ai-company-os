# Recon Scaffolding — Shared Spine for Audit/Backlog Skills

> **Status:** Shared canonical content. Referenced by `simulator-polish-recon`, `premium-feel-audit`, `pro-value-audit`, and future audit-family skills. This file is **documentation** for the contract; the **mechanical** contract is `packages/schemas/polish_prompt.py`. If the two ever disagree, the Python module wins.
>
> **Why this exists:** before 2026-05-12 the audit/backlog skills were standalone files with significant duplication of evidence-stack order, output schema, per-prompt template, and operator-memory pass language. Forking `simulator-polish-recon` into two sibling elevation-audits (`premium-feel-audit`, `pro-value-audit`) made the duplication a maintenance hazard. This spine lifts the truly universal bits into one referenced doc so each sibling skill can stay focused on its **observer** and **tier vocabulary**.
>
> **Editing rule:** changes to the **per-prompt template** in this file MUST be mirrored in `packages/schemas/polish_prompt.py` (specifically `POLISH_PROMPT_FIELDS`). The producer fixtures lock the field list against the canonical body; the schema module locks the field list against runtime Python. Drift requires updating both.

---

## What a recon-family skill is

A recon-family skill is a **read-only audit** that emits a ranked, variety-balanced backlog of prompts that `simulator-driven-polish` consumes unchanged. The skill walks a defined evidence stack, builds a coverage matrix, classifies gaps into tiers, and writes a dated backlog file. It does not edit application sources. It does not run the polish loop. Its output is a markdown file the operator picks prompts from.

Each recon-family skill differs from its siblings in exactly two ways:

- **Observer**: what the coverage matrix is scored against (prior polish coverage / a premium-bar rubric / a pro-value rule).
- **Tier vocabulary**: the named taxonomy of gap categories the skill emits (remedial vs elevation vs monetization).

Everything else — the per-prompt template, the 14-day cooling-off rule, the operator-memory pass, the variety mandate shape, the output skeleton — lives here.

## Per-prompt template (binding)

Every prompt emitted into a backlog file by a recon-family skill MUST use this exact 9-field block. The fields appear in this order. The mechanical source of truth for the field set is `packages/schemas/polish_prompt.py` (`POLISH_PROMPT_FIELDS`).

```
### N. <Short title> (<mode>)

> **Tier:** [sibling-specific tier vocabulary — see the per-skill tier table]
>
> **Evidence:** <commit SHA | file_path:line | vision Open Q #M | prior session log slug | rubric category>
>
> **Idea:** <one-paragraph framing>
>
> **Surfaces:** [SurfaceName.swift](path/to/file.swift) — optional :line
>
> **Fixture knobs:** PRODUCT_KNOB=value (...)
>
> **Prior context:** <session-log link if relevant; "none" otherwise>
>
> **Success criteria:** <what "done" looks like — specific, not "looks better">
>
> **Iteration cap:** <integer matching simulator-driven-polish mode default unless justified>
>
> **Final computer-use checkpoint:** <yes | no — with one-line reason>
```

Every field is mandatory. A prompt missing any field invalidates the report.

`<mode>` is one of the four values in `POLISH_PROMPT_MODES`: `fix-list`, `freeform-polish`, `reference-match`, `vision-driven`. The consuming `simulator-driven-polish` skill uses this to pick its mode of operation.

## Variety mandate (shape; each skill specifies the numbers)

Every recon-family skill declares **variety floors** — the minimum number of prompts at each `<mode>` per emitted backlog. Floors are sibling-specific (a premium audit needs more `reference-match` prompts; a pro-value audit needs more `fix-list` prompts). The shape of the rule is shared.

Rules:

1. The variety floor is a hard minimum at the **default depth**. Quick-depth backlogs may relax floors proportionally; deep backlogs must hit at least the standard-depth floors.
2. If a `focus` parameter forces the floor to slip (e.g., `focus: vision-questions-only` precludes `fix-list` prompts), the skill stops, surfaces the conflict in the report's executive summary, and asks the operator before relaxing. **Never silently drop the variety floor.**
3. Floors do NOT include `nice-to-have`-tier padding. Padding is allowed only after the floor is met.

## Operator memory pass (mandatory; hard-refusal on contradiction)

Every recon-family skill MUST execute an operator-memory pass before emitting prompts:

1. List `~/.claude/projects/-Users-simons-ai-company-os/memory/feedback_*.md` and `MEMORY.md`.
2. Read every file whose name suggests it could apply to the product (e.g. `feedback_life_clock_*.md` for life-clock, plus product-agnostic conventions like `feedback_xcode_build_loop.md`).
3. For each relevant memory: log it in the report's **Memory ledger** section.
4. **Hard refusal:** an emitted prompt MUST NOT contradict a memory entry. Example: a "wake should only fire once per day" prompt is rejected because `feedback_life_clock_wake_animation.md` decided otherwise. If a memory entry is ambiguous, note it as a Vision-question candidate instead — never silently override.

The memory ledger must be present in every emitted report, even if it states "no relevant entries" — absence of the ledger invalidates the report.

## 14-day cooling-off rule (binding)

Do not emit a prompt whose slug overlaps a session log (under `docs/products/<product-id>/polish-*.md` or any sibling backlog file) dated within the last 14 days UNLESS that prior log explicitly marked the item "Outstanding (next session)" / "deferred" / "V3 follow-up" or equivalent. This prevents redundant work and false-positive backlogs.

For backlog overlap across recon-family siblings (e.g., a `polish-backlog-*.md` and a `premium-feel-backlog-*.md` both targeting the same surface), the 14-day rule applies cross-skill. The slugs need not match exactly — semantic overlap (same surface + same observed gap) counts.

## Anti-patterns (binding refusals)

Every recon-family skill MUST NOT:

- Edit any file outside its declared write boundary
- Edit `vision.md` `## Decided constraints` (the ratchet — operator-only) — Open Questions append-only via `simulator-driven-polish`, not via recon-family skills
- Propose Feature-tier work as a `fix-list` or `freeform-polish` prompt — Feature-tier always lives in a `vision-driven` prompt with concrete options
- Re-emit a prompt whose slug ran in the last 14 days unless the prior log explicitly deferred it
- Emit a prompt without specific file-path evidence (e.g., "audit Profile" alone is invalid — must be `[ProfileView.swift](path)`)
- Skip the operator memory pass — this is the most common silent-failure mode and a hard refusal applies
- Contradict an entry in `Decided constraints` or operator memory (escalate to a Vision-question prompt instead)
- Skip the variety mandate to fit a focus hint without operator approval logged in the report

## Output structure (9 binding sections, in order)

Every recon-family backlog report file MUST contain these 9 sections in order. Section names are case-sensitive headings.

1. **State summary** (4–6 sentences) — branch/commit audited; since-when delta; what's clean; what's risky; readiness color
2. **Coverage matrix** — table per the per-skill schema; one row per surface
3. **Open Questions ledger** — every vision Open Q with current status + which emitted prompt (if any) targets it
4. **Memory ledger** — every operator-memory entry consulted + which emitted prompt cites it (or "no relevant entries")
5. **Fixture knob catalog** — every env var with values and default behavior
6. **The prompts** — N numbered prompts using the binding per-prompt template above
7. **Variety check** — declared distribution across modes + tiers; mandate compliance
8. **Recommended sequencing** — which prompts to run first; dependency arrows (prompt #M before prompt #N because...)
9. **Readiness flag** — green / yellow / red against the per-skill readiness criteria; the 1–3 prompts that would flip it if not green

Each sibling skill defines:

- The exact coverage-matrix column set (some columns universal — e.g., "Last polish session," "Open Questions touching this surface" — some sibling-specific — e.g., "Premium-bar category covered" / "Pro-value criterion covered").
- The readiness-flag criteria (submission-readiness for recon, premium-readiness for premium-feel-audit, pro-value-readiness for pro-value-audit).

## Same-day collision rule

If a recon-family skill is invoked twice on the same day with the same `focus`, the second invocation's output file path collides with the first. Resolution: the skill appends `-2`, `-3`, etc. to the filename slug, NOT to the date. Example: `polish-backlog-2026-05-12-submission-readiness-2.md`. This rule is binding for every recon-family skill — siblings must not invent their own collision discipline.

## Quality checks before writing the report

Before writing the report file, the skill must verify:

- [ ] Prompt count `>= minimum_prompts` and `<= depth_ceiling`
- [ ] Variety floors met (per the sibling's declared floors) OR explicit operator approval logged
- [ ] Every prompt has all 9 binding fields (matching `POLISH_PROMPT_FIELDS`)
- [ ] Every prompt cites at least one piece of evidence
- [ ] No 14-day overlap unless prior log explicitly deferred
- [ ] Memory ledger present (even if empty, must state "no relevant entries")
- [ ] Coverage matrix has no empty cells
- [ ] Readiness flag computed against the sibling's strict criteria
- [ ] No contradictions with vision Decided constraints or operator memory

If any check fails, fix before writing. Do not write a half-valid report and apologize in the body.

## Cadence guidance (shape; each skill specifies the numbers)

Recon-family skills are **single-pass** read-only audits. They are not loops. They are not scheduled. The operator invokes them when:

- Main is up-to-date and they want to know what to work on next
- After a merge of a feature branch (often with `focus: regression-sweep` for the recon variant, or `focus: newly-exposed-gaps` for the elevation variants)
- Before a release push (with the sibling-specific submission/premium/pro-value `focus`)
- After completing a vision Open Question to see what's newly unblocked

Do not invoke daily — the 14-day cooling-off rule will produce thin, repetitive backlogs. Weekly is the upper-bound healthy cadence for any single sibling; monthly is more typical.

## Consumer contract

The consuming skill is `skills/canonical/simulator-driven-polish/skill.md`. It reads prompts in the per-prompt template defined above and consumes the `<mode>` value to pick its operating mode. The producer-consumer contract is enforced by:

1. `packages/schemas/polish_prompt.py` — the mechanical field-set source of truth
2. Per-producer fixture files — each sibling's `fixtures/happy_path.yaml` lists the 9 fields under `required_input_fields` (or an equivalent recognized group label), exercised by `tests/python/unit/test_<skill_id>_fixtures.py`
3. `simulator-driven-polish/skill.md` — declares its consumption of the schema by name

If you edit the per-prompt template, you MUST update all three. Item 1 fails Python imports; item 2 fails reconciliation; item 3 fails review. There is no silent-drift path.
