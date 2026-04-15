---
status: completed
priority: p3
issue_id: "018"
tags: [code-review, data-integrity, state-dirs, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan adds JSON artifacts to `state/` subdirectories but does not specify: (a) retention policy, (b) state-directory ownership, or (c) CODEOWNERS entries for the new paths. After 30+ days of CI runs, `state/benchmarks/skill-estate/` (or `state/health/skill-estate/` per todo 014) will accumulate baselines with no GC story.

## Findings

Data-integrity-guardian second-pass findings:

- **Finding #8 — No GC / retention ADR:** "30+ daily baselines accumulate. Is that expected? Is there a retention ADR?"
- **Finding #10 — State ownership unstated:** "Who OWNS `state/benchmarks/skill-estate/` or `state/artifacts/verification-loop/`? The plan should name an owner because stale files otherwise accumulate. CODEOWNERS entry for these paths. Stale-file warning after 30 days in verification-loop output."
- **Finding #9 (supplementary) — `invalidate_registry_cache()` guidance is test-only:** Long-running workers invoking verification-loop across registry mutations could serve stale data. Confirm `(path, mtime_ns)` key handles in-process mutations; document it in the primitive docstring.

## Proposed Solutions

### Option 1: Governance ADR in Phase 0

Add §C + §D to the merged Phase 0 ADR (`docs/adr/2026-04-15-ecc-skill-decisions.md`):

**§C State ownership:**
| Subdir | Owner | Writer | Lifecycle |
| ------ | ----- | ------ | --------- |
| `state/health/skill-estate/` | CI + operator | stocktake, context-budget validators | append-only, retained 30 runs |
| `state/artifacts/verification-loop/` | operator | verification-loop smoke runs | append-only, retained 30 runs |
| `state/followups/` | agent + operator | followup_issue_writer | append-only, pruned on close |

**§D Retention:**
- Keep last N=30 files per subdir
- Oldest GC'd by a weekly `skill-estate-gc` skill (deferred to follow-up, issue filed when first breach observed)
- `verification-loop` output warns on stale files > 30 days old

**CODEOWNERS entry:** `state/health/** @simons` (or appropriate owner).

Pros:
- Governance in one place
- Retention policy documented before it matters
- Ownership is explicit

Cons:
- ADR grows by ~30 lines

Effort: trivial (plan doc + ADR edit)
Risk: low

## Recommended Action

Option 1. Fold into Phase 0 ADR as §C + §D.

## Acceptance Criteria

- [ ] Phase 0 ADR includes state-dir ownership table
- [ ] Phase 0 ADR includes retention policy (N=30, deferred GC implementation)
- [ ] `verification-loop` output has a "stale files detected" warning for files > 30 days old
- [ ] CODEOWNERS file entry for `state/health/**` (or chosen path)
- [ ] `invalidate_registry_cache()` docstring clarifies: `(path, mtime_ns)` key handles in-process mutations; long-running callers do not need manual invalidation after registry writes

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
