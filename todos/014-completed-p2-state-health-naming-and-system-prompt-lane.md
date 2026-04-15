---
status: completed
priority: p2
issue_id: "014"
tags: [code-review, architecture, state-dirs, context-budget, ecc-gap-plan]
dependencies: []
---

# Problem Statement

Two architectural naming/scope decisions need correction before Phase 2 implementation:

1. `state/benchmarks/skill-estate/` is the wrong home — `benchmarks/` by convention implies performance timings comparable over time, but stocktake/context-budget outputs are health snapshots. The plan never justifies the `benchmarks/` choice.
2. `context-budget` measures a single `claude_md` lane, but the real system-prompt cost includes CLAUDE.md + active project-skill pointers + MCP server instruction blocks + tool descriptions. A single lane gives misleadingly small numbers.

## Findings

### Architecture strategist second-pass findings

**Finding #3 — State directory naming:**
> "`state/benchmarks/skill-estate/` is the wrong home. `state/benchmarks/` by convention implies performance timings comparable over time; stocktake + context-budget outputs are health snapshots. Use `state/health/skill-estate/` and reserve `state/benchmarks/` for wallclock/throughput measurements. Phase 0's `state/README.md` glossary should encode the semantic boundary — `health/` = recurring drift/budget snapshots, `benchmarks/` = performance measurements, `artifacts/` = per-run output."

**Finding #6 — Context-budget lane scope:**
> "Measuring only `CLAUDE.md` gives a misleadingly small number that will pass baselines while real session context bloats unchecked. Rename the lane to `system_prompt` and have `context-budget` sum: (a) `CLAUDE.md`, (b) resolved `.claude/skills/*.md` pointers, (c) any `<mcp-instructions>` blocks from `.mcp.json` / settings — with each sub-contribution broken out in the report."

## Proposed Solutions

### Option 1: Adopt both corrections in Phase 0 ADR + Phase 2b contract

- Phase 0 `state/README.md` glossary encodes three state-dir semantics: `health/` (recurring snapshots), `benchmarks/` (performance measurements), `artifacts/` (per-run output).
- Rename `state/benchmarks/skill-estate/` → `state/health/skill-estate/` in the plan doc.
- Phase 2b `context-budget` contract.yaml renames `claude_md` lane → `system_prompt` and specifies it sums CLAUDE.md + project-skill pointers + MCP instruction blocks. MCP block discovery deferred if too expensive for v1, with an explicit TODO.

Pros:
- Gets both naming decisions right before on-disk artifacts ship
- Sets semantic precedent for future state subdirectories
- Context-budget measurement actually reflects session cost

Cons:
- Rename touches multiple plan sections

Effort: small (plan doc + contract.yaml)
Risk: low

### Option 2: Accept current names and add documentation

Keep `state/benchmarks/skill-estate/` and `claude_md` lane, add notes explaining why.

Pros:
- Zero rename

Cons:
- Wrong names persist
- Context-budget numbers are misleadingly small

Effort: trivial
Risk: medium

## Recommended Action

Option 1.

## Acceptance Criteria

- [ ] Phase 0 ADR encodes `state/health/`, `state/benchmarks/`, `state/artifacts/` semantic boundaries
- [ ] Plan doc + Phase 2b/3/4 references updated: `state/benchmarks/skill-estate/` → `state/health/skill-estate/`
- [ ] `context-budget` contract renames `claude_md` lane → `system_prompt`
- [ ] `system_prompt` lane sums CLAUDE.md + active `.claude/skills/*.md` pointers + MCP instruction blocks (or TODO if deferred)
- [ ] Baseline JSON breaks out per-contribution sub-counts under `system_prompt`

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
