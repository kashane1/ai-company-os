---
title: ECC Gap — §5 Install-Surface Deferral + Kind/Layout Decisions for Six New Skills
date: 2026-04-15
status: accepted
supersedes: (none)
related:
  - docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md
  - docs/2026-04-14-everything-claude-code-gap-analysis.md
  - docs/adr/2026-04-14-canonical-skill-layout.md
  - docs/adr/2026-04-14-primitives-subpackage.md
---

# ECC Gap — §5 Install-Surface Deferral + Kind/Layout Decisions

## Status

**Accepted** (2026-04-15, ECC Gap Recommendations Phase 0).

## Context

The [2026-04-14 everything-claude-code gap analysis](/docs/2026-04-14-everything-claude-code-gap-analysis.md)
identified five places where `ai-company-os` could benefit from ideas in
[`affaan-m/everything-claude-code`](https://github.com/affaan-m/everything-claude-code).
§3 was already closed by the Hermes Phase 3 `worker-skill-evolution`
(PR #8, commit `1ce62bb`). The remaining four recommendations — §§1, 2,
4, 5 — are addressed by
[docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md](/docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md).

That plan ships six new canonical skills across three implementation
phases. This ADR records two binding decisions the plan depends on and
that future contributors need surfaced outside the plan body:

1. **§A — §5 install-surface machinery is a deliberate non-goal.** The
   plan never ships an install profile, marketplace, or manifest format.
   This ADR enumerates the trip-wire conditions under which the deferral
   should be revisited.
2. **§B — Kind, layout, and registry defaults for the six new skills
   are fixed up front.** Phase 1/2/3 PRs cannot relitigate whether
   `search-first` is agentic or validator, whether `skill-stocktake`
   uses the directory layout, or whether any of the six default to
   `self_evolvable: true`.

A third operational section documents state directory semantics and
retention governance because the plan introduces two new subdirectories
(`state/artifacts/verification-loop/`, `state/health/skill-estate/`) and
both need owner/writer/lifecycle rules recorded somewhere durable.

## Decision

### §A — §5 install-surface deferral

`ai-company-os` does **not** ship install-profile machinery, skill
marketplaces, manifest bundles, or any mechanism for selectively
installing a subset of canonical skills into another repository. The
plan's Phase 0 — this document — is the closest the plan gets to the §5
recommendation and is deliberate: a decision record, not code.

Until at least one of the following four trip-wires fires, install
surface work stays closed. A PR introducing install-profile, manifest,
or marketplace machinery must first supersede this ADR with evidence
that a trip-wire has fired.

1. **External distribution becomes a product need.** Another team or
   an external user wants to install a subset of `ai-company-os` skills
   in their own repo.
2. **Multi-harness shipping becomes a product need.** The repo ships
   canonical skills to a non-Claude, non-Codex harness (Cursor, Zed,
   etc.) beyond the Phase 4 ACP adapter envisaged in the Hermes plan.
3. **Selective skill packs become a product need.** The repo has > 50
   canonical skills and operators want to install only a subset
   (e.g., "gtm pack" or "engineering pack").
4. **Canonical skill count doubles.** The registry crosses 44 entries
   (2× the 2026-04-15 baseline of 22); skill-estate hygiene alone may
   not be enough and install profiles become a scaling lever.

**What "install surface is deferred" does NOT mean:**

- It does not mean skills cannot be shared with other runtimes. The
  existing canonical/adapters split handles multi-runtime shipping for
  Claude and Codex already.
- It does not mean the repo cannot document its skill-authoring
  conventions externally. `skills/README.md`, `skills/spec.md`, and
  `skills/WIRING.md` remain authoritative references.
- It does not mean third parties cannot copy individual skills by hand.
  They can, as source material, same as we read the upstream ECC repo
  on 2026-04-15.

### §B — Kind, layout, and registry defaults for six new skills

All six new canonical skills introduced by the ECC Gap Recommendations
plan use the **per-skill-directory layout** from
[2026-04-14-canonical-skill-layout.md](/docs/adr/2026-04-14-canonical-skill-layout.md):

```
skills/canonical/<skill-id>/
├── skill.md           (required — prompt + frontmatter)
├── contract.yaml      (required — I/O contract)
├── validator.py       (required for kind: validator)
└── fixtures/          (happy_path_*, boundary_*, adversarial_*)
```

Kind assignment (binding, cannot drift across phases):

| Skill id              | Kind       | Rationale                                                                                                |
| --------------------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| `search-first`        | agentic    | LLM judgment about whether an existing solution matches. Fixtures freeze the procedure, not the verdict. |
| `documentation-lookup`| agentic    | LLM dispatches the right doc source (Context7, web fallback, local).                                     |
| `repo-onboarding`     | agentic    | Summarizes a repo area in natural language bounded by a structural contract.                             |
| `skill-stocktake`     | validator  | Deterministic registry + filesystem + CLAUDE.md walk. Pure Python, no LLM round-trip.                    |
| `context-budget`      | validator  | Deterministic token count per lane. Pure Python. `tiktoken` if available, char-count fallback.           |
| `verification-loop`   | agentic    | Composes validator outputs into a pass/soft_fail/hard_fail judgment.                                     |

Registry defaults (binding, enforced by the existing loader path in
[packages/tools/skills/loader.py](/packages/tools/skills/loader.py)):

- `stage: draft` on first creation; flipped to `active` in the same PR
  that lands fixtures and the dedicated pytest.
- `fixture_status: missing` on first creation; flipped to `passing`
  only when fixtures + dedicated test pass and reconciliation is clean.
- `self_evolvable: false`, **never flipped true by this plan.** Any
  future self-evolution of these skills requires a human-authored PR
  via the Hermes Phase 3 allowlist model in
  [packages/tools/skills/loader.py](/packages/tools/skills/loader.py).
- `source: internal` — these are rewrites from scratch, not copies.

Registry field ordering (binding): `id → name → path → owner_agent →
target_runtimes → stage → kind → fixture_status → source → adapters →
project_skill`, with `self_evolvable: false` as an optional line after
`kind` when explicit declaration is warranted.

**Placeholder-entry ceremony is explicitly rejected.** Each of Phases
1/2/3 adds its own registry entry when it has real content to register.
No Phase-0 placeholder rows, no guard test that gets deleted later.

**Trigger-phrase edits are human-only.** Agents requesting a new
trigger phrase route through `worker-skill-evolution` (Hermes Phase 3)
which produces a human-authored PR. No primitive exists for programmatic
CLAUDE.md edits; this is a deliberate non-primitive so the boundary
stays visible. The `skill-stocktake` primitive only reads CLAUDE.md —
it never writes.

**Disambiguation rule in CLAUDE.md (binding for all trigger phrases,
not just the six new ones).** If multiple trigger phrases could match a
single user message, Claude MUST ask which skill to invoke rather than
guess. Every Phase 1 skill ships an `adversarial_ambiguous_phrase.yaml`
fixture asserting the canonical body instructs disambiguation.

### §C — State directory ownership and semantics

The plan introduces two new subdirectories under `state/`. Both need
ownership/writer/lifecycle records per the Hermes state-directory
hygiene convention.

| Subdir                            | Writer                | Purpose                                                | Lifecycle          |
| --------------------------------- | --------------------- | ------------------------------------------------------ | ------------------ |
| `state/artifacts/verification-loop/` | operator (via skill)  | Per-run `VerificationLoopReport` snapshots (one dir per run-id) | retain last 30     |
| `state/health/skill-estate/`      | CI + operator         | Recurring `StocktakeReport` and `ContextBudgetReport` baselines | retain last 30     |
| `state/followups/`                | agents + operator     | Typed `FollowupEntry` YAML files for drift items captured via `followup_issue_writer` | retain until resolved, then archive to `state/archive/followups/<yyyy>/` |

Three state-directory semantic categories are recognized across the
repo, each with distinct retention rules:

- **`state/health/`** — recurring snapshots. Point-in-time measurements
  of platform state. Retained for trend comparison.
- **`state/benchmarks/`** — performance measurements. Point-in-time
  wallclock / throughput records. Same lifecycle as `health/`.
- **`state/artifacts/`** — per-run output. Each run gets its own
  subdirectory. Retention per writer convention.

CODEOWNERS for `state/health/**` is required before Phase 4 baseline
runs land. This is process mitigation, not code enforcement, and keeps
bad actors from silently editing historical baseline files.

### §D — Retention policy

Keep the last **N = 30** files per `state/health/skill-estate/` and
`state/artifacts/verification-loop/` subdirectory. Garbage collection
is **deferred** until the first breach is observed — at that point,
file a follow-up to create a `skill-estate-gc` skill that walks the
subdirs and archives anything older than the retention cap. Until then,
`verification-loop` output warns on files older than 30 days so a
breach surfaces before it becomes a problem.

## Rationale

**Why a single ADR instead of two?** The two decisions — install-surface
deferral and kind/layout decisions — are both pre-implementation
commitments that Phase 1/2/3 PRs must not re-relitigate. Splitting them
into two short ADRs was inflation; one document, two sections matches
the existing ADR length convention
([2026-04-14-canonical-skill-layout.md](/docs/adr/2026-04-14-canonical-skill-layout.md)
is ~130 lines) and makes the two decisions visible together.

**Why record §A as an ADR and not a README line?** README lines decay.
An ADR with explicit trip-wire conditions survives contributor turnover
and makes the deferral provable. A future contributor who proposes
install-profile machinery can be pointed at this ADR's trip-wire list
and asked which one fired.

**Why record §C / §D here instead of in `state/README.md`?**
`state/README.md` is the directory glossary. This ADR is the decision
record. The glossary lists what exists; the ADR records why it exists
and what its governance rules are. Both ship in the Phase 0 PR; they
cross-reference each other.

## Consequences

### Immediate (Phase 0)

- `state/README.md` is converted from a 15-line category list into a
  directory table that lists every `state/*` subdirectory with columns
  `subdir | writer | purpose | lifecycle`, including the two new entries.
- `skills/WIRING.md` gains a reference to this ADR so the install-surface
  deferral is discoverable from the wiring convention document.

### Forward (Phase 1–4)

- Phase 1 PR adds the `search-first`, `documentation-lookup`, and
  `repo-onboarding` canonical directories with their own registry
  entries (no Phase 0 placeholders).
- Phase 2 PR adds `skill-stocktake` and `context-budget` canonical
  directories with their own registry entries.
- Phase 3 PR adds `verification-loop` canonical directory.
- Phase 4 PR captures baselines into `state/health/skill-estate/` and
  `state/artifacts/verification-loop/` under the retention rules this
  ADR establishes.

### Forward (post-plan)

- Any PR proposing install-profile machinery must supersede §A with
  explicit trip-wire evidence.
- Any PR flipping `self_evolvable: true` on one of the six skills must
  supersede §B with explicit allowlist-update justification.
- Retention garbage collection ships only after a breach is observed,
  not preemptively.

## References

- [docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md](/docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md) — the plan this ADR enables.
- [docs/2026-04-14-everything-claude-code-gap-analysis.md](/docs/2026-04-14-everything-claude-code-gap-analysis.md) — the gap analysis naming §§1, 2, 4, 5.
- [docs/adr/2026-04-14-canonical-skill-layout.md](/docs/adr/2026-04-14-canonical-skill-layout.md) — binding directory layout.
- [docs/adr/2026-04-14-primitives-subpackage.md](/docs/adr/2026-04-14-primitives-subpackage.md) — binding subpackage for `registry_drift.py` and `context_budget.py`.
- [packages/tools/skills/loader.py](/packages/tools/skills/loader.py) — stage/fixture gating enforcement.
- Hermes Phase 3 (PR #8, commit `1ce62bb`) — `worker-skill-evolution` allowlist model that §B defers to.
